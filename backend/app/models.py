from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, func, event, UniqueConstraint, ForeignKey
from typing import Optional, List, Dict, Any
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class BaseModel(db.Model):
    """Base model with common columns and methods."""
    __abstract__ = True
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, 
                           onupdate=datetime.utcnow, nullable=False)

    @classmethod
    def get_by_id(cls, id: int) -> Optional['BaseModel']:
        return cls.query.get(id)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

# --------------------- Admin ---------------------
class AdminUser(BaseModel):
    __tablename__ = 'admin_users'
    
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True, index=True)
    role = db.Column(db.String(20), default='user')
    email = db.Column(db.String(120), unique=True, nullable=True)
    last_password_change = db.Column(db.DateTime)
    login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    
    def set_password(self, password: str):
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        self.password_hash = generate_password_hash(password)
        self.last_password_change = datetime.utcnow()
        
    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
    
    def increment_login_attempts(self):
        self.login_attempts += 1
        if self.login_attempts >= 5:
            self.locked_until = datetime.utcnow() + timedelta(minutes=30)
    
    def reset_login_attempts(self):
        self.login_attempts = 0
        self.locked_until = None
    
    @property
    def is_locked(self) -> bool:
        return self.locked_until and self.locked_until > datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert AdminUser to dictionary, excluding sensitive data."""
        data = super().to_dict()
        # Remove sensitive fields
        data.pop('password_hash', None)
        data.pop('last_password_change', None)
        data.pop('login_attempts', None)
        data.pop('locked_until', None)
        return data
    
    def __repr__(self) -> str:
        return f'<AdminUser {self.username}>'

# --------------------- Portfolio Structure ---------------------
class Portfolio(BaseModel):
    __tablename__ = 'portfolios'

    name = db.Column(db.String(100), nullable=False, unique=True, index=True)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, index=True)
    color_theme = db.Column(db.String(20))
    display_order = db.Column(db.Integer, default=0)

    departments = db.relationship(
        'Department',
        back_populates='portfolio',
        cascade='all, delete-orphan',
        lazy='selectin',
        order_by='Department.display_order'
    )

    def to_dict(self, include_relationships: bool = False) -> Dict[str, Any]:
        """Convert Portfolio to dictionary."""
        data = super().to_dict()
        if include_relationships and self.departments:
            data['departments'] = [dept.to_dict() for dept in self.departments]
        return data

    def __repr__(self) -> str:
        return f'<Portfolio {self.name}>'

class Department(BaseModel):
    __tablename__ = 'departments'

    name = db.Column(db.String(100), nullable=False, index=True)
    portfolio_id = db.Column(
        db.Integer,
        ForeignKey('portfolios.id', name='fk_department_portfolio', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    display_order = db.Column(db.Integer, default=0)

    portfolio = db.relationship('Portfolio', back_populates='departments')
    subsidiaries = db.relationship(
        'Subsidiary',
        back_populates='department',
        cascade='all, delete-orphan',
        lazy='selectin',
        order_by='Subsidiary.display_order'
    )

    __table_args__ = (
        UniqueConstraint('name', 'portfolio_id', name='uq_department_name_portfolio'),
    )

    def to_dict(self, include_relationships: bool = False) -> Dict[str, Any]:
        """Convert Department to dictionary."""
        data = super().to_dict()
        if include_relationships:
            if self.portfolio:
                data['portfolio'] = self.portfolio.to_dict()
            if self.subsidiaries:
                data['subsidiaries'] = [sub.to_dict() for sub in self.subsidiaries]
        return data

    def __repr__(self) -> str:
        return f'<Department {self.name}>'

class Subsidiary(BaseModel):
    __tablename__ = 'subsidiaries'

    name = db.Column(db.String(100), nullable=False, index=True)
    short_name = db.Column(db.String(20))
    cluster = db.Column(db.String(50), index=True)
    location = db.Column(db.String(100))
    industry = db.Column(db.String(100), index=True)
    website = db.Column(db.String(255))
    logo_url = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, index=True)
    display_order = db.Column(db.Integer, default=0)

    portfolio_id = db.Column(
        db.Integer,
        ForeignKey('portfolios.id', name='fk_subsidiary_portfolio', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    department_id = db.Column(
        db.Integer,
        ForeignKey('departments.id', name='fk_subsidiary_department', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    portfolio = db.relationship('Portfolio')
    department = db.relationship('Department', back_populates='subsidiaries')
    categories = db.relationship(
        'Category',
        back_populates='subsidiary',
        cascade='all, delete-orphan',
        lazy='selectin',
        order_by='Category.display_order'
    )
    scores = db.relationship(
        'Score',
        back_populates='subsidiary',
        cascade='all, delete-orphan',
        lazy='dynamic',
        order_by='Score.year_id.desc()'
    )

    def to_dict(self, include_relationships: bool = False) -> Dict[str, Any]:
        """Convert Subsidiary to dictionary."""
        data = super().to_dict()
        if include_relationships:
            if self.portfolio:
                data['portfolio'] = self.portfolio.to_dict()
            if self.department:
                data['department'] = self.department.to_dict()
            if self.categories:
                data['categories'] = [cat.to_dict(include_relationships=True) for cat in self.categories]
        return data

    def __repr__(self) -> str:
        return f'<Subsidiary {self.name}>'

# --------------------- Year ---------------------
class Year(BaseModel):
    __tablename__ = 'years'

    year = db.Column(db.Integer, unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    scores = db.relationship("Score", back_populates="year")

    def to_dict(self, include_relationships: bool = False) -> Dict[str, Any]:
        """Convert Year to dictionary."""
        data = super().to_dict()
        if include_relationships and self.scores:
            data['scores'] = [score.to_dict() for score in self.scores]
        return data

    def __repr__(self) -> str:
        return f'<Year {self.year}>'

# --------------------- Category ---------------------
class Category(BaseModel):
    __tablename__ = 'categories'

    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    weight = db.Column(db.Float, default=100.0)
    year_id = db.Column(
        db.Integer,
        ForeignKey('years.id', name='fk_category_year', ondelete='CASCADE'),
        nullable=False
    )
    subsidiary_id = db.Column(
        db.Integer,
        ForeignKey('subsidiaries.id', name='fk_category_subsidiary', ondelete='CASCADE'),
        nullable=False
    )
    display_order = db.Column(db.Integer, default=0)

    # Relationships
    year = db.relationship('Year')
    subsidiary = db.relationship('Subsidiary', back_populates='categories')
    kpis = db.relationship('KPI', back_populates='category', cascade='all, delete-orphan')

    __table_args__ = (
        UniqueConstraint('name', 'subsidiary_id', 'year_id', name='uq_category_name_subsidiary_year'),
    )

    def to_dict(self, include_relationships: bool = False) -> Dict[str, Any]:
        """Convert Category to dictionary."""
        data = super().to_dict()
        if include_relationships:
            if self.year:
                data['year'] = self.year.to_dict()
            if self.subsidiary:
                data['subsidiary'] = self.subsidiary.to_dict()
            if self.kpis:
                data['kpis'] = [kpi.to_dict(include_relationships=True) for kpi in self.kpis]
        return data

    def __repr__(self):
        return f'<Category {self.name} (Subsidiary: {self.subsidiary.name if self.subsidiary else "None"})>'

# --------------------- KPI ---------------------
class KPI(BaseModel):
    __tablename__ = 'kpis'

    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    weight = db.Column(db.Float, default=1.0)
    target = db.Column(db.Float)
    calculation_method = db.Column(db.String(50))
    display_order = db.Column(db.Integer, default=0)

    category_id = db.Column(
        db.Integer,
        ForeignKey('categories.id', name='fk_kpi_category', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    category = db.relationship('Category', back_populates='kpis')
    scores = db.relationship('Score', back_populates='kpi', cascade='all, delete-orphan')

    __table_args__ = (
        CheckConstraint('weight > 0', name='chk_kpi_positive_weight'),
        CheckConstraint('target IS NULL OR target BETWEEN 0 AND 100', name='chk_kpi_target_range'),
        UniqueConstraint('name', 'category_id', name='uq_kpi_name_category'),
    )

    def to_dict(self, include_relationships: bool = False) -> Dict[str, Any]:
        """Convert KPI to dictionary."""
        data = super().to_dict()
        if include_relationships and self.category:
            data['category'] = self.category.to_dict()
        return data

    def __repr__(self) -> str:
        return f'<KPI {self.name} (Category: {self.category.name if self.category else "None"})>'

# --------------------- Score ---------------------
class Score(BaseModel):
    __tablename__ = "scores"
    
    subsidiary_id = db.Column(
        db.Integer,
        ForeignKey("subsidiaries.id", name="fk_score_subsidiary", ondelete="CASCADE"),
        nullable=False
    )
    year_id = db.Column(
        db.Integer,
        ForeignKey("years.id", name="fk_score_year", ondelete="CASCADE"),
        nullable=False
    )
    kpi_id = db.Column(
        db.Integer,
        ForeignKey("kpis.id", name="fk_score_kpi", ondelete="CASCADE"),
        nullable=False
    )

    weight = db.Column(db.Float, nullable=True)
    target = db.Column(db.Float, nullable=True)
    actual = db.Column(db.Float, nullable=True)
    weighted_score = db.Column(db.Float, nullable=True)
    # ADDED: is_approved field for score approval workflow
    is_approved = db.Column(db.Boolean, default=False, nullable=False)
    created_by = db.Column(db.String(100), nullable=True)

    kpi = db.relationship("KPI", back_populates="scores")
    subsidiary = db.relationship("Subsidiary", back_populates="scores")
    year = db.relationship("Year", back_populates="scores")

    __table_args__ = (
        UniqueConstraint("subsidiary_id", "year_id", "kpi_id", name="uq_score_unique"),
        CheckConstraint("weight IS NULL OR weight >= 0", name="chk_score_weight_positive"),
        CheckConstraint("target IS NULL OR target >= 0", name="chk_score_target_positive"),
        CheckConstraint("actual IS NULL OR actual >= 0", name="chk_score_actual_positive"),
    )

    def to_dict(self, include_relationships: bool = False) -> Dict[str, Any]:
        """Convert Score to dictionary."""
        data = super().to_dict()
        if include_relationships:
            if self.kpi:
                data['kpi'] = self.kpi.to_dict()
            if self.subsidiary:
                data['subsidiary'] = self.subsidiary.to_dict()
            if self.year:
                data['year'] = self.year.to_dict()
        return data

    def __repr__(self):
        return f'<Score {self.kpi.name if self.kpi else "Unknown"} - {self.actual} (Approved: {self.is_approved})>'