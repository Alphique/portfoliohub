# app/__init__.py
from flask import Flask, render_template
from datetime import datetime
from flask_migrate import Migrate
from .config import Config
from .models import db

def create_app(config_class=Config):
    """Application factory for Portfolio PMC Hub."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)

    # Register blueprints
    from .routes.auth_routes import auth_bp
    from .routes.pages_routes import pages_bp
    from .routes.admin_routes import admin_bp
    from .routes.user_routes import user_bp
    from .routes.api_routes import api_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(api_bp, url_prefix='/api')

    # Context processors (available in all templates)
    @app.context_processor
    def inject_globals():
        """Inject global variables into all templates."""
        try:
            from .models import Portfolio, Year
            # Use simple queries that don't trigger relationship loading
            active_portfolios = Portfolio.query.filter_by(is_active=True).order_by(Portfolio.display_order).all()
            active_year = Year.query.filter_by(is_active=True).first()
        except Exception as e:
            # If tables don't exist yet or other error, return defaults
            active_portfolios = []
            active_year = None
        
        # Get current user from session if available
        from flask import session
        current_user = session.get('admin_user') if 'admin_user' in session else None
        
        return {
            "current_year": datetime.now().year,
            "active_portfolios": active_portfolios,
            "active_year": active_year,
            "current_user": current_user
        }

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        # Use simple template rendering without navigation data
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template("errors/403.html"), 403

    return app