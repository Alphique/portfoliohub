from functools import wraps
from flask import session, redirect, url_for, flash, request
import logging
from ..models import AdminUser, Portfolio, Year
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

def login_required(roles=None):
    """Enhanced login decorator with session, role, and debug logging."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            logger.info(f"[AUTH] Accessing {f.__name__} | Roles Allowed: {roles}")

            if 'admin_user' not in session:
                logger.warning("[AUTH] No admin_user in session — redirecting to login.")
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login', next=request.url))

            user = AdminUser.query.filter_by(username=session['admin_user']).first()
            if not user:
                logger.error("[AUTH] Session user not found in DB — clearing session.")
                session.pop('admin_user', None)
                flash('User not found.', 'danger')
                return redirect(url_for('auth.login'))

            if not user.is_active:
                logger.warning(f"[AUTH] User {user.username} inactive — redirecting to login.")
                session.pop('admin_user', None)
                flash('Your account is inactive.', 'danger')
                return redirect(url_for('auth.login'))

            if roles and user.role not in roles:
                logger.warning(f"[AUTH] Unauthorized access — role '{user.role}' not allowed.")
                flash('Unauthorized access.', 'danger')
                return redirect(url_for('user.dashboard'))

            logger.info(f"[AUTH] Access granted for user: {user.username} ({user.role})")
            return f(*args, **kwargs)

        decorated_function.login_required = True
        return decorated_function
    return decorator

def get_navigation_data():
    """Fetches common data for navigation elements."""
    try:
        portfolios = Portfolio.query.filter_by(is_active=True).order_by(Portfolio.display_order).all()
        active_year = Year.query.filter_by(is_active=True).first()
        
        return {
            'portfolios': portfolios,
            'current_year': datetime.now().year,
            'active_year': active_year
        }
    except SQLAlchemyError as e:
        logger.error(f"Navigation data error: {str(e)}")
        return {
            'portfolios': [], 
            'current_year': datetime.now().year,
            'active_year': None
        }

def get_active_year():
    """Retrieves the currently active fiscal year with fallback."""
    try:
        active_year = Year.query.filter_by(is_active=True).first()
        if not active_year:
            latest_year = Year.query.order_by(Year.year.desc()).first()
            if latest_year:
                latest_year.is_active = True
                db.session.commit()
                logger.info(f"Auto-activated year: {latest_year.year}")
        return active_year
    except SQLAlchemyError as e:
        logger.error(f"Active year query error: {str(e)}")
        return None

def get_score_years():
    """Retrieves a list of all fiscal years."""
    try:
        return Year.query.order_by(Year.year.desc()).all()
    except SQLAlchemyError as e:
        logger.error(f"Score years query error: {str(e)}")
        return []