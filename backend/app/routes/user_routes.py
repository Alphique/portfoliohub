# app/routes/user_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from functools import wraps
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
import logging
import traceback
from ..models import db, Portfolio, Department, Subsidiary, Score, Year, Category, KPI
from ..utils.auth import login_required, get_navigation_data, get_active_year, get_score_years
from ..utils.dashboard_utils import get_dashboard_data, get_filter_data, get_chart_data
from ..utils.logo_mappings import LOGO_MAPPINGS

user_bp = Blueprint('user', __name__)
logger = logging.getLogger(__name__)

# ==============================================
# Main Application Routes (for logged-in users)
# ==============================================

@user_bp.route('/select_task')
@login_required()
def select_task():
    return render_template('select_task.html', **get_navigation_data())

@user_bp.route('/dashboard')
@login_required()
def dashboard():
    try:
        # Get active year as default
        active_year = get_active_year()
        if not active_year:
            flash('No active year configured. Please set up a year first.', 'warning')
            return redirect(url_for('user.select_task'))

        # Collect filters from query parameters
        requested_year_id = request.args.get('year_id', type=int)
        if requested_year_id:
            requested_year = Year.query.get(requested_year_id)
            if requested_year:
                selected_year_id = requested_year_id
                selected_year = requested_year
            else:
                selected_year_id = active_year.id
                selected_year = active_year
        else:
            selected_year_id = active_year.id
            selected_year = active_year

        filters = {
            'year_id': selected_year_id,
            'portfolio_id': request.args.get('portfolio_id', type=int),
            'subsidiary_id': request.args.get('subsidiary_id', type=int),
            'category_id': request.args.get('category_id', type=int),
            'kpi_id': request.args.get('kpi_id', type=int)
        }

        # Get dashboard data
        results = get_dashboard_data(filters)
        dashboard_data = process_dashboard_results(results)
        
        # Get chart data
        chart_data = get_chart_data(results, filters['year_id'])

        # Get navigation and filter data
        nav_data = get_navigation_data()
        nav_data.pop('portfolios', None)
        filter_data = get_filter_data(filters['year_id'])

        return render_template(
            'dashboard.html',
            data=dashboard_data['scores'],
            overall_average=dashboard_data['overall_avg'],
            top_performer=dashboard_data['top_performer'],
            score_distribution=dashboard_data['score_distribution'],
            counts=dashboard_data['counts'],
            chart_data=chart_data,
            years=filter_data['years'],
            portfolios=filter_data['portfolios'],
            subsidiaries=filter_data['subsidiaries'],
            categories=filter_data['categories'],
            kpis=filter_data['kpis'],
            selected_year=filters['year_id'],
            selected_portfolio=filters['portfolio_id'],
            selected_subsidiary=filters['subsidiary_id'],
            selected_category=filters['category_id'],
            selected_kpi=filters['kpi_id'],
            display_year=selected_year,
            **nav_data
        )

    except Exception as e:
        logger.exception(f"Dashboard error: {str(e)}")
        flash('Error loading dashboard. Please try again.', 'danger')
        return redirect(url_for('user.select_task'))

def process_dashboard_results(results):
    """Process dashboard results to calculate statistics"""
    if not results:
        return get_empty_dashboard_data()
    
    valid_scores = [score for score in results if score.Score.actual is not None]
    
    if not valid_scores:
        return get_empty_dashboard_data()
    
    # Calculate overall average
    overall_avg = sum(score.Score.actual for score in valid_scores) / len(valid_scores)
    
    # Score distribution
    excellent = len([s for s in valid_scores if s.Score.actual >= 90])
    high = len([s for s in valid_scores if 80 <= s.Score.actual < 90])
    medium = len([s for s in valid_scores if 50 <= s.Score.actual < 80])
    low = len([s for s in valid_scores if s.Score.actual < 50])
    
    # Top performer calculation
    subsidiary_scores = {}
    for result in valid_scores:
        sub_id = result.subsidiary_id
        if sub_id not in subsidiary_scores:
            subsidiary_scores[sub_id] = {
                'scores': [],
                'name': result.subsidiary_name,
                'portfolio': result.portfolio_name
            }
        subsidiary_scores[sub_id]['scores'].append(result.Score.actual)
    
    subsidiary_avgs = {}
    for sub_id, data in subsidiary_scores.items():
        if data['scores']:
            avg_score = sum(data['scores']) / len(data['scores'])
            subsidiary_avgs[sub_id] = {
                'average': avg_score,
                'name': data['name'],
                'portfolio': data['portfolio'],
                'count': len(data['scores'])
            }
    
    top_performer = None
    if subsidiary_avgs:
        top_id = max(subsidiary_avgs.items(), key=lambda x: x[1]['average'])[0]
        top_data = subsidiary_avgs[top_id]
        top_performer = {
            'name': top_data['name'],
            'portfolio': top_data['portfolio'],
            'score': round(top_data['average'], 2),
            'count': top_data['count']
        }
    
    # Counts
    unique_subsidiaries = len(set(result.subsidiary_id for result in valid_scores))
    unique_portfolios = len(set(result.portfolio_id for result in valid_scores))
    unique_categories = len(set(result.category_id for result in valid_scores if result.category_id))
    unique_kpis = len(set(result.kpi_id for result in valid_scores))
    
    return {
        'scores': results,
        'overall_avg': round(overall_avg, 2),
        'top_performer': top_performer,
        'score_distribution': {
            'excellent': excellent,
            'high': high,
            'medium': medium,
            'low': low,
            'total': len(valid_scores)
        },
        'counts': {
            'portfolios': unique_portfolios,
            'subsidiaries': unique_subsidiaries,
            'categories': unique_categories,
            'kpis': unique_kpis,
            'records': len(valid_scores)
        }
    }

def get_empty_dashboard_data():
    """Return empty dashboard data structure"""
    return {
        'scores': [],
        'overall_avg': 0,
        'top_performer': None,
        'score_distribution': {
            'excellent': 0, 'high': 0, 'medium': 0, 'low': 0, 'total': 0
        },
        'counts': {
            'portfolios': 0, 'subsidiaries': 0, 'categories': 0, 'kpis': 0, 'records': 0
        }
    }

# ==============================================
# Portfolio & Subsidiary Selection Routes
# ==============================================

@user_bp.route("/portfolio", methods=["GET", "POST"])
@login_required()
def portfolio():
    try:
        if request.method == "POST":
            portfolio_id = request.form.get("portfolio_id")
            if portfolio_id:
                return redirect(url_for('user.select_subsidiary', portfolio_id=portfolio_id))
            else:
                flash('Please select a portfolio.', 'warning')
                return redirect(url_for('user.portfolio'))
        
        portfolios = Portfolio.query.filter_by(is_active=True).order_by(Portfolio.name).all()
        nav_data = get_navigation_data()
        nav_data.pop('portfolios', None)
            
        return render_template(
            "portfolio.html", 
            portfolios=portfolios,
            **nav_data
        )
    except Exception as e:
        logger.error(f"Portfolio error: {str(e)}")
        flash('Error loading portfolios.', 'danger')
        return redirect(url_for('user.select_task'))

@user_bp.route('/portfolio/<int:portfolio_id>/select_subsidiary', methods=['GET'])
@login_required()
def select_subsidiary(portfolio_id):
    try:
        portfolio = Portfolio.query.get_or_404(portfolio_id)
        departments = Department.query.filter_by(
            portfolio_id=portfolio_id).order_by(Department.name).all()
        
        department_clusters = {
            dept.name: dept.subsidiaries 
            for dept in departments
        }

        nav_data = get_navigation_data()
        nav_data.pop('portfolios', None)
        
        return render_template(
            "select_subsidiary.html",
            portfolio=portfolio,
            departments=departments,
            department_clusters=department_clusters,
            years=get_score_years(),
            logo_mappings=LOGO_MAPPINGS,
            **nav_data
        )
    except Exception as e:
        logger.error(f"Select subsidiary error: {str(e)}")
        flash('Error loading subsidiary data.', 'danger')
        return redirect(url_for('user.portfolio'))

# ==============================================
# Score Entry Routes
# ==============================================

@user_bp.route('/entry/<int:subsidiary_id>/<int:year_id>', methods=['GET'])
@login_required(roles=['admin', 'editor'])
def score_entry(subsidiary_id, year_id):
    try:
        subsidiary = Subsidiary.query.get_or_404(subsidiary_id)
        year = Year.query.get_or_404(year_id)

        # Fetch categories with their KPIs
        categories = Category.query.filter_by(
            subsidiary_id=subsidiary_id,
            year_id=year_id
        ).options(
            db.joinedload(Category.kpis)
        ).order_by(Category.display_order).all()

        serializable_categories = [cat.to_dict(include_relationships=True) for cat in categories]

        # Get existing scores
        existing_scores = db.session.query(
            Score.kpi_id, 
            Score.actual,
            Score.weighted_score,
            Score.is_approved
        ).filter(
            Score.subsidiary_id == subsidiary_id,
            Score.year_id == year_id
        ).all()
        
        existing_scores_dict = {
            score.kpi_id: {
                'actual': score.actual,
                'weighted_score': score.weighted_score,
                'is_approved': score.is_approved
            } for score in existing_scores
        }

        total_kpis = sum(len(category.kpis) for category in categories)

        nav_data = get_navigation_data()
        if 'portfolios' in nav_data:
            nav_data.pop('portfolios')

        return render_template(
            'entry.html',
            year=year,
            subsidiary=subsidiary,
            categories=serializable_categories,
            scores=existing_scores_dict,
            total_kpis=total_kpis,
            available_years=get_score_years(),
            **nav_data
        )

    except Exception as e:
        logger.error(f"Score entry error for subsidiary {subsidiary_id}, year {year_id}: {str(e)}", exc_info=True)
        
        if current_app.config.get('ENV') == 'development':
            return f"""
            <h1>Error Loading Score Entry</h1>
            <p><strong>Error:</strong> {str(e)}</p>
            <p><strong>Subsidiary ID:</strong> {subsidiary_id}</p>
            <p><strong>Year ID:</strong> {year_id}</p>
            <pre>{traceback.format_exc()}</pre>
            <a href="{url_for('user.select_task')}">Back to Select Task</a>
            """, 500
        else:
            flash(f'Error loading score entry page: {str(e)}', 'danger')
            return redirect(url_for('user.select_task'))

@user_bp.route('/save_scores', methods=['POST'])
@login_required(roles=['admin', 'editor'])
def save_scores():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        subsidiary_id = data.get('subsidiary_id')
        year_id = data.get('year_id')
        username = session.get('admin_user')
        
        if not all([subsidiary_id, year_id, username]):
            return jsonify({'error': 'Missing required fields'}), 400

        subsidiary = Subsidiary.query.get(subsidiary_id)
        year = Year.query.get(year_id)
        if not subsidiary or not year:
            return jsonify({'error': 'Invalid subsidiary or year'}), 400

        saved_count = 0
        updated_count = 0
        scores_data = data.get('scores', [])

        for score_data in scores_data:
            kpi_id = score_data.get('kpi_id')
            value = score_data.get('value')
            
            if not kpi_id:
                continue

            kpi = KPI.query.get(kpi_id)
            if not kpi:
                logger.warning(f"KPI {kpi_id} not found, skipping")
                continue

            # Calculate weighted score
            weighted = None
            if value is not None and value != '' and kpi.target:
                try:
                    numeric_value = float(value)
                    weighted = (numeric_value / kpi.target) * kpi.weight
                except (ValueError, TypeError, ZeroDivisionError) as e:
                    logger.warning(f"Invalid value for KPI {kpi_id}: {value}, error: {str(e)}")
                    weighted = None

            # Find existing score
            score = Score.query.filter_by(
                subsidiary_id=subsidiary_id,
                kpi_id=kpi_id,
                year_id=year_id
            ).first()

            if score:
                # Check if score is approved and user is not admin
                if getattr(score, "is_approved", False) and session.get('role') != 'admin':
                    continue

                # Only update if value changed
                new_actual = float(value) if value is not None and value != '' else None
                if score.actual != new_actual:
                    score.actual = new_actual
                    score.weighted_score = weighted
                    score.updated_at = datetime.utcnow()
                    updated_count += 1
                    
            elif value is not None and value != '':
                # Create new score
                try:
                    score = Score(
                        subsidiary_id=subsidiary_id,
                        kpi_id=kpi_id,
                        year_id=year_id,
                        actual=float(value),
                        weighted_score=weighted,
                        target=kpi.target,
                        created_by=username,
                        created_at=datetime.utcnow()
                    )
                    db.session.add(score)
                    saved_count += 1
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid value for new score KPI {kpi_id}: {value}")
                    continue

        db.session.commit()
        
        total_processed = saved_count + updated_count
        message = f'Successfully saved {saved_count} new scores and updated {updated_count} scores'
        
        logger.info(f"Scores saved: {saved_count} new, {updated_count} updated for subsidiary {subsidiary_id}, year {year_id} by {username}")
        
        return jsonify({
            'message': message,
            'saved': saved_count,
            'updated': updated_count,
            'total_processed': total_processed
        }), 200

    except ValueError as e:
        db.session.rollback()
        logger.error(f"Value error in save_scores: {str(e)}")
        return jsonify({'error': 'Invalid data format provided'}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error saving scores: {str(e)}")
        return jsonify({'error': 'Database error saving scores'}), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error in save_scores: {str(e)}", exc_info=True)
        return jsonify({'error': 'System error during save operation'}), 500

# ==============================================
# Debug Route
# ==============================================

@user_bp.route('/debug-dashboard')
@login_required()
def debug_dashboard():
    """Debug route to identify data issues"""
    debug_info = {}
    
    # Check active year
    active_year = get_active_year()
    debug_info['active_year'] = {
        'id': active_year.id if active_year else None,
        'year': active_year.year if active_year else None
    }
    
    # Check portfolios and their data
    portfolios = Portfolio.query.filter_by(is_active=True).all()
    debug_info['portfolios'] = {}
    
    for portfolio in portfolios:
        portfolio_data = {
            'id': portfolio.id,
            'name': portfolio.name,
            'subsidiaries': []
        }
        
        subsidiaries = Subsidiary.query.filter_by(
            portfolio_id=portfolio.id, 
            is_active=True
        ).all()
        
        for subsidiary in subsidiaries:
            subsidiary_data = {
                'id': subsidiary.id,
                'name': subsidiary.name,
                'categories_count': len(subsidiary.categories),
                'scores_count': 0
            }
            
            categories = Category.query.filter_by(
                subsidiary_id=subsidiary.id,
                year_id=active_year.id
            ).all()
            
            subsidiary_data['categories_for_active_year'] = len(categories)
            
            scores = Score.query.filter_by(
                subsidiary_id=subsidiary.id,
                year_id=active_year.id
            ).filter(Score.actual.isnot(None)).all()
            
            subsidiary_data['scores_count'] = len(scores)
            
            if categories:
                kpi_count = 0
                for category in categories:
                    kpi_count += len(category.kpis)
                subsidiary_data['kpis_count'] = kpi_count
            else:
                subsidiary_data['kpis_count'] = 0
                
            portfolio_data['subsidiaries'].append(subsidiary_data)
        
        debug_info['portfolios'][portfolio.name] = portfolio_data
    
    return jsonify(debug_info)