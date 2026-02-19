# backend/app/seed_data.py
from .models import db, Portfolio, Department, Subsidiary, Attribute, Score, AdminUser
from datetime import datetime
import random

def seed_all_data():
    """Comprehensive data seeding with error handling"""
    print("\n=== Starting database seeding ===")
    
    try:
        # Clear existing data in proper order
        models = [Score, Attribute, Subsidiary, Department, Portfolio, AdminUser]
        for model in models:
            db.session.query(model).delete()
        db.session.commit()
        
        # Seed admin user
        admin = AdminUser(
            username="admin",
            is_active=True,
            role="admin"
        )
        admin.set_password("securepassword123")
        db.session.add(admin)
        
        # Seed portfolios and departments
        portfolios_data = [
            {
                "name": "Mining & Energy",
                "color_theme": "blue",
                "departments": ["Mining", "Energy", "M&E Services"]
            },
            {
                "name": "Manufacturing & Agriculture",
                "color_theme": "green",
                "departments": ["Manufacturing", "Agriculture", "M&A Services"]
            },
            {
                "name": "Tourism Infrastructure & Services", 
                "color_theme": "yellow",
                "departments": ["Infrastructure", "Transportation", "TIS Services"]
            }
        ]
        
        portfolios = []
        for p_data in portfolios_data:
            p = Portfolio(
                name=p_data["name"],
                color_theme=p_data["color_theme"]
            )
            db.session.add(p)
            db.session.flush()
            
            for dept_name in p_data["departments"]:
                d = Department(
                    name=dept_name,
                    portfolio_id=p.id
                )
                db.session.add(d)
            
            portfolios.append(p)
        
        db.session.flush()
        
        # Seed subsidiaries (sample - extend with your full list)
        subsidiaries_data = [
            {"name": "ZCCM-IH", "department": 1, "cluster": "Mining", "location": "Kitwe"},
            {"name": "ZESCO", "department": 2, "cluster": "Energy", "location": "Lusaka"},
            # Add all other subsidiaries...
        ]
        
        subsidiaries = []
        for sub_data in subsidiaries_data:
            sub = Subsidiary(
                name=sub_data["name"],
                department_id=sub_data["department"],
                cluster=sub_data["cluster"],
                location=sub_data["location"],
                portfolio_id=next(p.id for p in portfolios if p.id == sub_data["department"]),
                logo_url=f"/static/logos/{sub_data['name'].lower().replace(' ', '_')}.png"
            )
            db.session.add(sub)
            subsidiaries.append(sub)
        
        db.session.flush()
        
        # Seed attributes
        attributes_data = [
            {"name": "Revenue Growth", "category": "Financial"},
            {"name": "Profit Margin", "category": "Financial"},
            # Add all other attributes...
        ]
        
        attributes = []
        for attr_data in attributes_data:
            attr = Attribute(
                name=attr_data["name"],
                category=attr_data["category"],
                weight=1.0
            )
            db.session.add(attr)
            attributes.append(attr)
        
        db.session.flush()
        
        # Seed scores
        current_year = datetime.now().year
        for sub in subsidiaries:
            for attr in random.sample(attributes, min(5, len(attributes))):
                score = Score(
                    subsidiary_id=sub.id,
                    attribute_id=attr.id,
                    year=current_year,
                    company_score=round(random.uniform(50, 95), 2),
                    top_score=round(random.uniform(80, 100), 2),
                    is_approved=random.choice([True, False])
                )
                db.session.add(score)
        
        db.session.commit()
        print("✅ Database seeded successfully!")
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Seeding failed: {str(e)}")
        return False