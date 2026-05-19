# app/routes/auth_routes.py
from flask import Blueprint, render_template, redirect, url_for, request, flash, session, current_app
from functools import wraps
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
import logging
from ..models import db, AdminUser, Year

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

@auth_bp.route('/', methods=['GET', 'POST'])
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    try:
        # Create default admin and year in development
        if current_app.config.get('ENV') == 'development':
            # Create default admin if none exists
            if not AdminUser.query.first():
                admin_user = AdminUser(
                    username='admin',
                    role='admin',
                    is_active=True,
                    email='admin@example.com'
                )
                admin_user.set_password('admin123')
                db.session.add(admin_user)
                db.session.commit()
                flash('Default admin user created.', 'info')
            
            # Create default year if none exists
            if not Year.query.first():
                current_year = datetime.now().year
                default_year = Year(
                    year=current_year,
                    is_active=True
                )
                db.session.add(default_year)
                db.session.commit()
                flash(f'Default year {current_year} created.', 'info')

        if 'admin_user' in session:
            return redirect(url_for('user.select_task'))
            
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            next_page = request.args.get('next')
            
            if not username or not password:
                flash('Username and password are required.', 'danger')
                return render_template('login.html')
                
            user = AdminUser.query.filter_by(username=username).first()
            
            if not user or not user.check_password(password):
                flash('Invalid credentials.', 'danger')
                return render_template('login.html')
                
            if not user.is_active:
                flash('Account is inactive.', 'danger')
                return render_template('login.html')
                
            session['admin_user'] = user.username
            session['role'] = user.role
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            flash(f'Welcome, {user.username}!', 'success')
            return redirect(next_page or url_for('user.select_task'))
            
        return render_template('login.html')
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        flash('System error during login.', 'danger')
        return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    try:
        session.pop('admin_user', None)
        session.pop('role', None)
        flash('Logged out successfully.', 'info')
        return redirect(url_for('auth.login'))
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        flash('Error during logout.', 'danger')
        return redirect(url_for('auth.login'))

#sample admin
@auth_bp.route('/create-admin')
def create_admin():
    from ..models import AdminUser, db

    # prevent duplicate creation
    if AdminUser.query.filter_by(username="admin").first():
        return "Admin already exists."

    admin = AdminUser(
        username="admin",
        email="admin@local.com",
        role="admin",
        is_active=True
    )
    admin.set_password("admin123")

    db.session.add(admin)
    db.session.commit()

    return "Admin created: username=admin password=admin123"
    return "HIT"
