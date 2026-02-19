# app/routes/admin_routes.py
from flask import Blueprint, render_template, request, flash, jsonify, session, current_app
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import func
import logging
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from ..models import db, AdminUser, Portfolio, Department, Subsidiary, Score, Year, Category, KPI
from ..utils.auth import login_required, get_navigation_data, get_active_year, get_score_years
from ..utils.file_upload import allowed_file, ALLOWED_EXTENSIONS
from ..utils.logo_mappings import LOGO_MAPPINGS

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
logger = logging.getLogger(__name__)

# ==============================================
# Admin Management Routes
# ==============================================

@admin_bp.route('/dashboard')
@login_required(roles=['admin'])
def admin_dashboard():
    """Admin-only dashboard with system statistics"""
    try:
        # Get system statistics
        stats = {
            'total_users': AdminUser.query.count(),
            'active_users': AdminUser.query.filter_by(is_active=True).count(),
            'total_portfolios': Portfolio.query.count(),
            'total_subsidiaries': Subsidiary.query.count(),
            'total_scores': Score.query.count(),
            'recent_logins': AdminUser.query.order_by(AdminUser.last_login.desc()).limit(5).all()
        }
        
        return render_template(
            'admin_dashboard.html',
            stats=stats,
            **get_navigation_data()
        )
    except Exception as e:
        logger.error(f"Admin dashboard error: {str(e)}")
        flash('Error loading admin dashboard.', 'danger')
        return redirect(url_for('user.select_task'))

@admin_bp.route('/users')
@login_required(roles=['admin'])
def manage_users():
    """Manage system users"""
    try:
        users = AdminUser.query.order_by(AdminUser.created_at.desc()).all()
        return render_template(
            'admin/users.html',
            users=users,
            **get_navigation_data()
        )
    except Exception as e:
        logger.error(f"Manage users error: {str(e)}")
        flash('Error loading users.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/user/create', methods=['POST'])
@login_required(roles=['admin'])
def create_user():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        required_fields = ['username', 'email', 'role', 'password']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Check if username already exists
        if AdminUser.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already exists'}), 400
            
        # Check if email already exists
        if AdminUser.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 400
            
        user = AdminUser(
            username=data['username'],
            email=data['email'],
            role=data['role'],
            is_active=data.get('is_active', True)
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'message': 'User created successfully',
            'user': user.to_dict()
        }), 201
        
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"User creation integrity error: {str(e)}")
        return jsonify({'error': 'Database integrity error'}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"User creation error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/user/<int:user_id>', methods=['PUT'])
@login_required(roles=['admin'])
def update_user(user_id):
    try:
        user = AdminUser.query.get_or_404(user_id)
        data = request.get_json()
        
        # Prevent self-deactivation
        if user.username == session.get('admin_user') and 'is_active' in data and not data['is_active']:
            return jsonify({'error': 'Cannot deactivate your own account'}), 400
            
        if 'username' in data and data['username'] != user.username:
            # Check if new username already exists
            if AdminUser.query.filter(
                AdminUser.id != user_id,
                AdminUser.username == data['username']
            ).first():
                return jsonify({'error': 'Username already exists'}), 400
            user.username = data['username']
            
        if 'email' in data and data['email'] != user.email:
            # Check if new email already exists
            if AdminUser.query.filter(
                AdminUser.id != user_id,
                AdminUser.email == data['email']
            ).first():
                return jsonify({'error': 'Email already exists'}), 400
            user.email = data['email']
            
        if 'role' in data:
            user.role = data['role']
            
        if 'is_active' in data:
            user.is_active = data['is_active']
            
        if 'password' in data and data['password']:
            user.set_password(data['password'])
            
        db.session.commit()
        
        return jsonify({
            'message': 'User updated successfully',
            'user': user.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"User update error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/user/<int:user_id>', methods=['DELETE'])
@login_required(roles=['admin'])
def delete_user(user_id):
    try:
        user = AdminUser.query.get_or_404(user_id)
        
        # Prevent self-deletion
        if user.username == session.get('admin_user'):
            return jsonify({'error': 'Cannot delete your own account'}), 400
            
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'message': 'User deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"User deletion error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ==============================================
# Seed Management (Admin only)
# ==============================================

@admin_bp.route("/seed_management", methods=["GET", "POST"])
@login_required(roles=['admin'])
def seed_management():
    try:
        if request.method == "POST":
            data_type = request.form.get("entity_type")

            if data_type == "portfolio":
                name = request.form.get("name")
                description = request.form.get("description")

                if not name:
                    flash("Portfolio name is required.", "danger")
                elif Portfolio.query.filter_by(name=name).first():
                    flash(f"Portfolio '{name}' already exists.", "warning")
                else:
                    new_portfolio = Portfolio(name=name, description=description)
                    db.session.add(new_portfolio)
                    db.session.commit()
                    flash(f"Portfolio '{name}' added successfully!", "success")

            elif data_type == "department":
                name = request.form.get("name")
                portfolio_id = request.form.get("portfolio_id")

                if not name or not portfolio_id:
                    flash("Department name and Portfolio are required.", "danger")
                else:
                    new_department = Department(name=name, portfolio_id=portfolio_id)
                    db.session.add(new_department)
                    db.session.commit()
                    flash(f"Department '{name}' added successfully!", "success")

            elif data_type == "subsidiary":
                name = request.form.get("name")
                short_name = request.form.get("short_name")
                portfolio_id = request.form.get("portfolio_id")
                department_id = request.form.get("department_id")

                if not name or not portfolio_id or not department_id:
                    flash("Subsidiary name, portfolio, and department are required.", "danger")
                else:
                    new_subsidiary = Subsidiary(
                        name=name,
                        short_name=short_name,
                        portfolio_id=portfolio_id,
                        department_id=department_id
                    )
                    db.session.add(new_subsidiary)
                    db.session.commit()
                    flash(f"Subsidiary '{name}' added successfully!", "success")

            elif data_type == "category":
                name = request.form.get("name")
                weight = request.form.get("weight")
                year_id = request.form.get("year_id")
                subsidiary_id = request.form.get("subsidiary_id")

                if not name or not weight or not year_id or not subsidiary_id:
                    flash("Category name, weight, year, and subsidiary are required.", "danger")
                else:
                    new_category = Category(
                        name=name,
                        weight=weight,
                        year_id=year_id,
                        subsidiary_id=subsidiary_id
                    )
                    db.session.add(new_category)
                    db.session.commit()
                    flash(f"Category '{name}' added successfully!", "success")

            elif data_type == "kpi":
                name = request.form.get("name")
                category_id = request.form.get("category_id")
                weight = request.form.get("weight")
                target = request.form.get("target")
                calculation_method = request.form.get("calculation_method")
                description = request.form.get("description")

                if not name or not category_id:
                    flash("KPI name and Category are required.", "danger")
                else:
                    new_kpi = KPI(
                        name=name,
                        category_id=category_id,
                        weight=weight,
                        target=target,
                        calculation_method=calculation_method,
                        description=description
                    )
                    db.session.add(new_kpi)
                    db.session.commit()
                    flash(f"KPI '{name}' added successfully!", "success")

            elif data_type == "year":
                year_value = request.form.get("year")
                is_active = bool(request.form.get("is_active"))

                if not year_value:
                    flash("Year value is required.", "danger")
                elif Year.query.filter_by(year=year_value).first():
                    flash(f"Year {year_value} already exists.", "warning")
                else:
                    new_year = Year(
                        year=int(year_value),
                        is_active=is_active
                    )
                    db.session.add(new_year)
                    db.session.commit()
                    flash(f"Year {year_value} added successfully!", "success")

            return redirect(url_for("admin.seed_management"))
        
        # GET request - fetch existing data
        years = Year.query.all()
        portfolios = Portfolio.query.all()
        departments = Department.query.all()
        subsidiaries = Subsidiary.query.all()
        categories = Category.query.all()
        kpis = KPI.query.all()

        # Get navigation data and remove portfolios to avoid conflict
        nav_data = get_navigation_data()
        nav_data.pop('portfolios', None)

        return render_template(
            "admin/seed_management.html",
            years=years,
            portfolios=portfolios,
            departments=departments,
            subsidiaries=subsidiaries,
            categories=categories,
            kpis=kpis,
            **nav_data
        )
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Seed management error: {str(e)}")
        flash('Error in seed management operation.', 'danger')
        return redirect(url_for('user.select_task'))

# ==============================================
# Logo Upload Route (Admin only)
# ==============================================

@admin_bp.route('/upload_logo/<int:subsidiary_id>', methods=['POST'])
@login_required(roles=['admin', 'editor'])
def upload_logo(subsidiary_id):
    try:
        subsidiary = Subsidiary.query.get_or_404(subsidiary_id)
        
        if 'logo' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        file = request.files['logo']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        if file and allowed_file(file.filename):
            # Generate unique filename
            filename = secure_filename(file.filename)
            unique_filename = f"logo_{subsidiary_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{filename}"
            
            # Create uploads directory if it doesn't exist
            upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'logos')
            os.makedirs(upload_dir, exist_ok=True)
            
            filepath = os.path.join(upload_dir, unique_filename)
            file.save(filepath)
            
            # Update subsidiary with relative path for web access
            relative_path = f"uploads/logos/{unique_filename}"
            subsidiary.logo_url = relative_path
            db.session.commit()
            
            return jsonify({
                'message': 'Logo uploaded successfully',
                'logo_url': url_for('static', filename=relative_path)
            }), 200
            
        return jsonify({'error': 'Invalid file type. Allowed types: PNG, JPG, JPEG, GIF, SVG, WebP'}), 400
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Logo upload error: {str(e)}")
        return jsonify({'error': 'Error uploading logo'}), 500

# ==============================================
# Setup Route for Default Data (Admin only)
# ==============================================

@admin_bp.route('/setup_default_year')
@login_required(roles=['admin'])
def setup_default_year():
    """Create a default active year if none exists"""
    try:
        # Check if any year exists
        existing_year = Year.query.first()
        if not existing_year:
            # Create current year as active
            current_year = datetime.now().year
            new_year = Year(
                year=current_year,
                is_active=True
            )
            db.session.add(new_year)
            db.session.commit()
            flash(f'Default year {current_year} created and set as active.', 'success')
        else:
            # Check if any year is active
            active_year = Year.query.filter_by(is_active=True).first()
            if not active_year:
                # Set the most recent year as active
                latest_year = Year.query.order_by(Year.year.desc()).first()
                latest_year.is_active = True
                db.session.commit()
                flash(f'Year {latest_year.year} set as active.', 'success')
            else:
                flash(f'Year {active_year.year} is already active.', 'info')
                
        return redirect(url_for('user.select_task'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Year setup error: {str(e)}")
        flash('Error setting up default year.', 'danger')
        return redirect(url_for('user.select_task'))