# app/routes/api_routes.py
from flask import Blueprint, request, jsonify, session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import func
import logging
from ..models import db, Portfolio, Department, Subsidiary, Score, Year, Category, KPI
from ..utils.auth import login_required

api_bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

# ==============================================
# Category Management API
# ==============================================

@api_bp.route('/categories', methods=['POST'])
@login_required(roles=['admin', 'editor'])
def create_category():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        required_fields = ['name', 'year_id', 'subsidiary_id']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Validate year and subsidiary exist
        Year.query.get_or_404(data['year_id'])
        Subsidiary.query.get_or_404(data['subsidiary_id'])
            
        # Check if category already exists
        exists = Category.query.filter_by(
            name=data['name'],
            year_id=data['year_id'],
            subsidiary_id=data['subsidiary_id']
        ).first()
        
        if exists:
            return jsonify({'error': 'Category already exists for this subsidiary and year'}), 400
            
        category = Category(
            name=data['name'],
            year_id=data['year_id'],
            subsidiary_id=data['subsidiary_id'],
            weight=data.get('weight', 100.0),
            display_order=data.get('display_order', 0)
        )
        
        db.session.add(category)
        db.session.commit()
        
        return jsonify({
            'message': 'Category created successfully',
            'category': category.to_dict()
        }), 201
        
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"Category creation integrity error: {str(e)}")
        return jsonify({'error': 'Database integrity error'}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Category creation error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/categories/<int:category_id>', methods=['PUT'])
@login_required(roles=['admin', 'editor'])
def update_category(category_id):
    try:
        category = Category.query.get_or_404(category_id)
        data = request.get_json()
        
        if 'name' in data:
            if Category.query.filter(
                Category.id != category_id,
                Category.name == data['name'],
                Category.year_id == category.year_id,
                Category.subsidiary_id == category.subsidiary_id
            ).first():
                return jsonify({'error': 'Category name already exists for this subsidiary and year'}), 400
            category.name = data['name']
            
        if 'weight' in data:
            new_weight = float(data['weight'])
            current_kpi_weight = getattr(category, 'total_kpi_weight', 0)
            if new_weight < current_kpi_weight:
                return jsonify({
                    'error': f'New weight ({new_weight}) cannot be less than used weight ({current_kpi_weight})'
                }), 400
            category.weight = new_weight
            
        if 'display_order' in data:
            category.display_order = data['display_order']
            
        db.session.commit()
        
        return jsonify({
            'message': 'Category updated successfully',
            'category': category.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Category update error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/categories/copy', methods=['POST'])
@login_required(roles=['admin', 'editor'])
def copy_categories():
    try:
        data = request.get_json()
        source_year_id = data.get('source_year_id')
        target_year_id = data.get('target_year_id')
        subsidiary_id = data.get('subsidiary_id')
        
        if not all([source_year_id, target_year_id, subsidiary_id]):
            return jsonify({'error': 'Missing required parameters'}), 400
            
        Year.query.get_or_404(source_year_id)
        target_year = Year.query.get_or_404(target_year_id)
        subsidiary = Subsidiary.query.get_or_404(subsidiary_id)
        
        source_categories = Category.query.filter_by(
            year_id=source_year_id,
            subsidiary_id=subsidiary_id
        ).all()
        
        if not source_categories:
            return jsonify({'error': 'No categories found for source year'}), 404
            
        copied_categories = 0
        copied_kpis = 0
        
        for source_cat in source_categories:
            exists = Category.query.filter_by(
                name=source_cat.name,
                year_id=target_year_id,
                subsidiary_id=subsidiary_id
            ).first()
            
            if not exists:
                new_cat = Category(
                    name=source_cat.name,
                    weight=source_cat.weight,
                    display_order=source_cat.display_order,
                    year_id=target_year_id,
                    subsidiary_id=subsidiary_id
                )
                db.session.add(new_cat)
                db.session.flush()
                copied_categories += 1
                
                for kpi in source_cat.kpis:
                    new_kpi = KPI(
                        name=kpi.name,
                        description=kpi.description,
                        weight=kpi.weight,
                        target=kpi.target,
                        calculation_method=kpi.calculation_method,
                        display_order=kpi.display_order,
                        category_id=new_cat.id
                    )
                    db.session.add(new_kpi)
                    copied_kpis += 1
        
        db.session.commit()
        return jsonify({
            'message': f'Successfully copied {copied_categories} categories and {copied_kpis} KPIs',
            'copied_categories': copied_categories,
            'copied_kpis': copied_kpis
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Category copy error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ==============================================
# KPI Management API
# ==============================================

@api_bp.route('/kpis', methods=['GET'])
@login_required()
def get_kpis():
    category_id = request.args.get('category_id', type=int)
    if not category_id:
        return jsonify({'error': 'Missing category_id'}), 400
        
    kpis = KPI.query.filter_by(category_id=category_id).order_by(KPI.display_order).all()
    return jsonify([kpi.to_dict() for kpi in kpis])

@api_bp.route('/kpis', methods=['POST'])
@login_required(roles=['admin', 'editor'])
def create_kpi():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        category = Category.query.get(data.get('category_id'))
        if not category:
            return jsonify({"error": "Category not found"}), 404
            
        existing_weight = db.session.query(func.sum(KPI.weight)).filter(
            KPI.category_id == category.id
        ).scalar() or 0
        
        new_weight = sum(kpi.get('weight', 0) for kpi in data.get('kpis', []))
        
        if (existing_weight + new_weight) > category.weight:
            return jsonify({
                "error": f"Category weight exceeded (Max: {category.weight})",
                "current_total": existing_weight + new_weight,
                "available_weight": category.weight - existing_weight
            }), 400
        
        created_kpis = []
        for kpi_data in data.get('kpis', []):
            kpi = KPI(
                name=kpi_data.get('name'),
                description=kpi_data.get('description', ''),
                weight=kpi_data.get('weight', 1.0),
                target=kpi_data.get('target', 80.0),
                calculation_method=kpi_data.get('calculation_method', 'direct'),
                display_order=kpi_data.get('display_order', 0),
                category_id=category.id
            )
            db.session.add(kpi)
            db.session.flush()
            created_kpis.append(kpi.to_dict())
        
        db.session.commit()
        return jsonify({
            "message": "KPIs created successfully",
            "kpis": created_kpis,
            "remaining_weight": category.weight - (existing_weight + new_weight)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"KPI creation error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/kpis/<int:kpi_id>', methods=['PUT'])
@login_required(roles=['admin', 'editor'])
def update_kpi(kpi_id):
    try:
        kpi = KPI.query.get_or_404(kpi_id)
        data = request.get_json()
        
        if 'weight' in data:
            new_weight = float(data['weight'])
            current_total = db.session.query(func.sum(KPI.weight)).filter(
                KPI.category_id == kpi.category_id,
                KPI.id != kpi_id
            ).scalar() or 0
            
            if (current_total + new_weight) > kpi.category.weight:
                return jsonify({
                    "error": f"Category weight would be exceeded (Max: {kpi.category.weight})",
                    "current_total": current_total + new_weight,
                    "available_weight": kpi.category.weight - current_total
                }), 400
            kpi.weight = new_weight
            
        if 'name' in data:
            kpi.name = data['name']
        if 'target' in data:
            kpi.target = data['target']
        if 'calculation_method' in data:
            kpi.calculation_method = data['calculation_method']
        if 'display_order' in data:
            kpi.display_order = data['display_order']
            
        db.session.commit()
        
        return jsonify({
            "message": "KPI updated successfully",
            "kpi": kpi.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"KPI update error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ==============================================
# Deletion API Endpoints
# ==============================================

@api_bp.route('/portfolio/<int:portfolio_id>', methods=['DELETE'])
@login_required(roles=['admin'])
def delete_portfolio(portfolio_id):
    try:
        portfolio = Portfolio.query.get_or_404(portfolio_id)
        
        department_count = Department.query.filter_by(portfolio_id=portfolio_id).count()
        
        if department_count > 0:
            return jsonify({
                'error': f'Cannot delete portfolio with {department_count} associated departments. Delete departments first.'
            }), 400
            
        db.session.delete(portfolio)
        db.session.commit()
        return jsonify({'message': 'Portfolio deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Portfolio deletion error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/portfolio/<int:portfolio_id>/force', methods=['DELETE'])
@login_required(roles=['admin'])
def force_delete_portfolio(portfolio_id):
    try:
        portfolio = Portfolio.query.get_or_404(portfolio_id)
        
        subsidiaries = Subsidiary.query.filter_by(portfolio_id=portfolio_id).all()
        deleted_subsidiaries = 0
        deleted_departments = 0
        
        for subsidiary in subsidiaries:
            Category.query.filter_by(subsidiary_id=subsidiary.id).delete()
            Score.query.filter_by(subsidiary_id=subsidiary.id).delete()
            db.session.delete(subsidiary)
            deleted_subsidiaries += 1
        
        departments = Department.query.filter_by(portfolio_id=portfolio_id).all()
        for department in departments:
            db.session.delete(department)
            deleted_departments += 1
        
        db.session.delete(portfolio)
        db.session.commit()
        
        return jsonify({
            'message': f'Portfolio and all associated data deleted successfully. Removed {deleted_departments} departments and {deleted_subsidiaries} subsidiaries.'
        }), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Force delete portfolio error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/department/<int:department_id>', methods=['DELETE'])
@login_required(roles=['admin'])
def delete_department(department_id):
    try:
        department = Department.query.get_or_404(department_id)
        
        subsidiary_count = Subsidiary.query.filter_by(department_id=department_id).count()
        if subsidiary_count > 0:
            return jsonify({
                'error': f'Cannot delete department with {subsidiary_count} associated subsidiaries. Delete subsidiaries first.'
            }), 400
            
        db.session.delete(department)
        db.session.commit()
        return jsonify({'message': 'Department deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Department deletion error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/department/<int:department_id>/force', methods=['DELETE'])
@login_required(roles=['admin'])
def force_delete_department(department_id):
    try:
        department = Department.query.get_or_404(department_id)
        
        subsidiaries = Subsidiary.query.filter_by(department_id=department_id).all()
        deleted_subsidiaries = 0
        
        for subsidiary in subsidiaries:
            Category.query.filter_by(subsidiary_id=subsidiary.id).delete()
            Score.query.filter_by(subsidiary_id=subsidiary.id).delete()
            db.session.delete(subsidiary)
            deleted_subsidiaries += 1
        
        db.session.delete(department)
        db.session.commit()
        
        return jsonify({
            'message': f'Department and all associated subsidiaries deleted successfully. Removed {deleted_subsidiaries} subsidiaries.'
        }), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Force delete department error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/subsidiary/<int:subsidiary_id>', methods=['DELETE'])
@login_required(roles=['admin'])
def delete_subsidiary(subsidiary_id):
    try:
        subsidiary = Subsidiary.query.get_or_404(subsidiary_id)
        
        category_count = Category.query.filter_by(subsidiary_id=subsidiary_id).count()
        score_count = Score.query.filter_by(subsidiary_id=subsidiary_id).count()
        
        if category_count > 0:
            return jsonify({
                'error': f'Cannot delete subsidiary with {category_count} associated categories. Delete categories first.'
            }), 400
            
        if score_count > 0:
            return jsonify({
                'error': f'Cannot delete subsidiary with {score_count} associated scores. Delete scores first.'
            }), 400
            
        db.session.delete(subsidiary)
        db.session.commit()
        return jsonify({'message': 'Subsidiary deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Subsidiary deletion error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/subsidiary/<int:subsidiary_id>/force', methods=['DELETE'])
@login_required(roles=['admin'])
def force_delete_subsidiary(subsidiary_id):
    try:
        subsidiary = Subsidiary.query.get_or_404(subsidiary_id)
        
        categories_deleted = Category.query.filter_by(subsidiary_id=subsidiary_id).delete()
        scores_deleted = Score.query.filter_by(subsidiary_id=subsidiary_id).delete()
        
        db.session.delete(subsidiary)
        db.session.commit()
        
        return jsonify({
            'message': f'Subsidiary and all associated data deleted successfully. Removed {categories_deleted} categories and {scores_deleted} scores.'
        }), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Force delete subsidiary error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/category/<int:category_id>', methods=['DELETE'])
@login_required(roles=['admin'])
def delete_category(category_id):
    try:
        category = Category.query.get_or_404(category_id)
        
        kpi_count = KPI.query.filter_by(category_id=category_id).count()
        if kpi_count > 0:
            return jsonify({
                'error': f'Cannot delete category with {kpi_count} associated KPIs. Delete KPIs first.'
            }), 400
            
        db.session.delete(category)
        db.session.commit()
        return jsonify({'message': 'Category deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Category deletion error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/category/<int:category_id>/force', methods=['DELETE'])
@login_required(roles=['admin'])
def force_delete_category(category_id):
    try:
        category = Category.query.get_or_404(category_id)
        
        kpis_deleted = KPI.query.filter_by(category_id=category_id).delete()
        
        db.session.delete(category)
        db.session.commit()
        
        return jsonify({
            'message': f'Category and all associated KPIs deleted successfully. Removed {kpis_deleted} KPIs.'
        }), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Force delete category error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/kpi/<int:kpi_id>', methods=['DELETE'])
@login_required(roles=['admin'])
def delete_kpi(kpi_id):
    try:
        kpi = KPI.query.get_or_404(kpi_id)
        
        score_count = Score.query.filter_by(kpi_id=kpi_id).count()
        if score_count > 0:
            return jsonify({
                'error': f'Cannot delete KPI with {score_count} associated scores.'
            }), 400
            
        db.session.delete(kpi)
        db.session.commit()
        return jsonify({'message': 'KPI deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"KPI deletion error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/year/<int:year_id>', methods=['DELETE'])
@login_required(roles=['admin'])
def delete_year(year_id):
    try:
        year = Year.query.get_or_404(year_id)
        
        score_count = Score.query.filter_by(year_id=year_id).count()
        category_count = Category.query.filter_by(year_id=year_id).count()
        
        if score_count > 0 or category_count > 0:
            return jsonify({
                'error': f'Cannot delete year with {score_count} scores and {category_count} categories. Delete associated data first.'
            }), 400
            
        db.session.delete(year)
        db.session.commit()
        return jsonify({'message': 'Year deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Year deletion error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ==============================================
# Utility API Endpoints
# ==============================================

@api_bp.route('/score_years')
@login_required()
def api_get_score_years():
    try:
        years = [y.to_dict() for y in Year.query.order_by(Year.year.desc()).all()]
        return jsonify(years)
    except Exception as e:
        logger.error(f"Score years error: {str(e)}")
        return jsonify([])