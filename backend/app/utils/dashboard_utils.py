from sqlalchemy import and_
import logging
from ..models import db, Score, Subsidiary, Portfolio, Category, KPI, Year

logger = logging.getLogger(__name__)

def get_dashboard_data(filters):
    """Get dashboard data based on filters"""
    try:
        query = (
            db.session.query(
                Score,
                Subsidiary.name.label('subsidiary_name'),
                Subsidiary.id.label('subsidiary_id'),
                Portfolio.name.label('portfolio_name'),
                Portfolio.id.label('portfolio_id'),
                Category.name.label('category_name'),
                Category.id.label('category_id'),
                KPI.name.label('kpi_name'),
                KPI.id.label('kpi_id'),
                Year.year.label('year')
            )
            .join(Subsidiary, Score.subsidiary_id == Subsidiary.id)
            .join(Portfolio, Subsidiary.portfolio_id == Portfolio.id)
            .join(KPI, Score.kpi_id == KPI.id)
            .join(Year, Score.year_id == Year.id)
            .outerjoin(Category, KPI.category_id == Category.id)
            .filter(Subsidiary.is_active.is_(True))
            .filter(Portfolio.is_active.is_(True))
            .filter(Score.year_id == filters['year_id'])
            .filter(Score.actual.isnot(None))
        )

        if filters['portfolio_id']:
            query = query.filter(Portfolio.id == filters['portfolio_id'])
        if filters['subsidiary_id']:
            query = query.filter(Subsidiary.id == filters['subsidiary_id'])
        if filters['category_id']:
            query = query.filter(Category.id == filters['category_id'])
        if filters['kpi_id']:
            query = query.filter(KPI.id == filters['kpi_id'])

        return query.all()
    except Exception as e:
        logger.error(f"Dashboard data error: {str(e)}")
        return []

def get_filter_data(year_id):
    """Get data for filter dropdowns"""
    try:
        return {
            'years': Year.query.order_by(Year.year.desc()).all(),
            'portfolios': Portfolio.query.filter_by(is_active=True).order_by(Portfolio.name).all(),
            'subsidiaries': Subsidiary.query.filter_by(is_active=True).order_by(Subsidiary.name).all(),
            'categories': Category.query.filter_by(year_id=year_id).order_by(Category.name).all(),
            'kpis': KPI.query.join(Category).filter(Category.year_id == year_id).order_by(KPI.name).all()
        }
    except Exception as e:
        logger.error(f"Filter data error: {str(e)}")
        return {
            'years': [],
            'portfolios': [],
            'subsidiaries': [],
            'categories': [],
            'kpis': []
        }

def get_chart_data(results, year_id):
    """Generate chart data from actual scores"""
    if not results:
        return get_empty_chart_data()
    
    valid_results = [r for r in results if r.Score.actual is not None]
    
    if not valid_results:
        return get_empty_chart_data()
    
    # Chart data generation logic here
    # ... (copy the get_chart_data function from your original code)
    
    return chart_data

def get_empty_chart_data():
    """Return empty chart data structure"""
    return {
        'main_chart': {'labels': [], 'data': [], 'title': 'Performance by Category'},
        'score_distribution': {
            'labels': ['Excellent (≥90)', 'High (80-89)', 'Medium (50-79)', 'Low (<50)'],
            'data': [0, 0, 0, 0],
            'title': 'Score Distribution'
        },
        'portfolio_comparison': {'labels': [], 'data': [], 'title': 'Portfolio Comparison'},
        'kpi_comparison': {'labels': [], 'data': [], 'title': 'Top Performing KPIs'},
        'yearly_trend': {'labels': [], 'data': []},
        'attribute_comparison': {'labels': [], 'data': []}
    }