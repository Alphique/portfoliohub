# app/routes/pages_routes.py
from flask import Blueprint, render_template, session
import logging
from app.utils.navigation import get_navigation_data

pages_bp = Blueprint('pages', __name__)
logger = logging.getLogger(__name__)

@pages_bp.route('/about_us')
def about_us():
    return render_template('about_us.html', **get_navigation_data())

@pages_bp.route('/contact')
def contact():
    return render_template('contact.html', **get_navigation_data())

@pages_bp.route('/')
def home():
    """Landing page - redirects to login if not authenticated, otherwise to select_task"""
    if 'admin_user' in session:
        return redirect(url_for('user.select_task'))
    return redirect(url_for('auth.login'))

# Error handlers
@pages_bp.app_errorhandler(404)
def page_not_found(e):
    return render_template('404.html', **get_navigation_data()), 404

@pages_bp.app_errorhandler(500)
def internal_server_error(e):
    return render_template('500.html', **get_navigation_data()), 500

@pages_bp.app_errorhandler(403)
def forbidden(e):
    return render_template('403.html', **get_navigation_data()), 403
