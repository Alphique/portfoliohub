# backend/init_db.py
import os
import sys

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import (
    AdminUser, Portfolio, Department, Subsidiary, 
    Score, Year, Category, KPI
)

def init_database():
    app = create_app()
    
    with app.app_context():
        try:
            print("Dropping all tables...")
            db.drop_all()
            
            print("Creating all tables...")
            db.create_all()
            
            print("Creating default data...")
            
            # Create default admin user
            admin_user = AdminUser(
                username='admin',
                role='admin',
                is_active=True,
                email='admin@example.com'
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            
            # Create default year
            from datetime import datetime
            current_year = datetime.now().year
            default_year = Year(
                year=current_year,
                is_active=True
            )
            db.session.add(default_year)
            db.session.flush()
            
            # Create sample portfolio structure
            portfolio = Portfolio(
                name='Corporate Portfolio',
                description='Main corporate performance portfolio',
                is_active=True,
                display_order=1
            )
            db.session.add(portfolio)
            db.session.flush()
            
            department = Department(
                name='Finance Division',
                portfolio_id=portfolio.id,
                display_order=1
            )
            db.session.add(department)
            db.session.flush()
            
            # Create subsidiary - Indo Bank example
            subsidiary = Subsidiary(
                name='Indo Bank',
                short_name='IBK',
                portfolio_id=portfolio.id,
                department_id=department.id,
                is_active=True,
                display_order=1
            )
            db.session.add(subsidiary)
            db.session.flush()
            
            # Create categories for Indo Bank
            categories_data = [
                {
                    'name': 'Financial Perspective',
                    'description': 'Financial performance metrics',
                    'weight': 40.0,
                    'kpis': [
                        {'name': 'Revenue Growth', 'weight': 25.0, 'target': 85.0, 'description': 'Year-over-year revenue growth percentage'},
                        {'name': 'GP Margin', 'weight': 20.0, 'target': 80.0, 'description': 'Gross profit margin percentage'},
                        {'name': 'EBIT Margin', 'weight': 15.0, 'target': 75.0, 'description': 'EBIT margin percentage'},
                        {'name': 'Current Ratio', 'weight': 20.0, 'target': 90.0, 'description': 'Current assets to current liabilities ratio'},
                        {'name': 'Payable Days', 'weight': 20.0, 'target': 85.0, 'description': 'Average days to pay suppliers'}
                    ]
                },
                {
                    'name': 'Internal Processes',
                    'description': 'Internal operational efficiency metrics',
                    'weight': 30.0,
                    'kpis': [
                        {'name': 'Clean Audit Opinion', 'weight': 40.0, 'target': 95.0, 'description': 'Receive clean audit opinion'},
                        {'name': 'Monthly Financial Submission', 'weight': 30.0, 'target': 90.0, 'description': 'Timely submission of monthly financials'},
                        {'name': 'Audited Financials Submission', 'weight': 30.0, 'target': 85.0, 'description': 'Timely submission of audited financials'}
                    ]
                },
                {
                    'name': 'Stakeholder Perspective', 
                    'description': 'Stakeholder satisfaction metrics',
                    'weight': 20.0,
                    'kpis': [
                        {'name': 'Customer Satisfaction', 'weight': 50.0, 'target': 88.0, 'description': 'Customer satisfaction score'},
                        {'name': 'Employee Engagement', 'weight': 50.0, 'target': 82.0, 'description': 'Employee engagement score'}
                    ]
                },
                {
                    'name': 'Intragroup Collaboration',
                    'description': 'Cross-group collaboration metrics',
                    'weight': 10.0,
                    'kpis': [
                        {'name': 'Cross-Selling Ratio', 'weight': 60.0, 'target': 78.0, 'description': 'Cross-selling to other group entities'},
                        {'name': 'Knowledge Sharing', 'weight': 40.0, 'target': 75.0, 'description': 'Participation in group knowledge sharing'}
                    ]
                }
            ]
            
            display_order = 1
            for cat_data in categories_data:
                category = Category(
                    name=cat_data['name'],
                    description=cat_data['description'],
                    weight=cat_data['weight'],
                    year_id=default_year.id,
                    subsidiary_id=subsidiary.id,
                    display_order=display_order
                )
                db.session.add(category)
                db.session.flush()
                
                # Create KPIs for this category
                kpi_display_order = 1
                for kpi_data in cat_data['kpis']:
                    kpi = KPI(
                        name=kpi_data['name'],
                        description=kpi_data['description'],
                        weight=kpi_data['weight'],
                        target=kpi_data['target'],
                        calculation_method='direct',
                        category_id=category.id,
                        display_order=kpi_display_order
                    )
                    db.session.add(kpi)
                    kpi_display_order += 1
                
                display_order += 1
            
            # Create sample scores
            from random import uniform
            for kpi in KPI.query.all():
                score = Score(
                    subsidiary_id=subsidiary.id,
                    year_id=default_year.id,
                    kpi_id=kpi.id,
                    weight=kpi.weight,
                    target=kpi.target,
                    actual=uniform(kpi.target - 10, kpi.target + 5),  # Random actual around target
                    weighted_score=uniform(15, 25)  # Random weighted score
                )
                db.session.add(score)
            
            db.session.commit()
            
            print("=" * 50)
            print("Database initialized successfully!")
            print("=" * 50)
            print("Default admin user created:")
            print("  Username: admin")
            print("  Password: admin123")
            print("\nSample data created:")
            print("  - Corporate Portfolio")
            print("  - Finance Division") 
            print("  - Indo Bank (Subsidiary)")
            print("  - 4 Categories with KPIs:")
            print("    * Financial Perspective (5 KPIs)")
            print("    * Internal Processes (3 KPIs)") 
            print("    * Stakeholder Perspective (2 KPIs)")
            print("    * Intragroup Collaboration (2 KPIs)")
            print("  - Sample scores for all KPIs")
            print("=" * 50)
            
        except Exception as e:
            print(f"ERROR during database initialization: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()

if __name__ == '__main__':
    init_database()