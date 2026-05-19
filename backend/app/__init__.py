# app/__init__.py
from flask import Flask, render_template, session
from datetime import datetime
from flask_migrate import Migrate
from .config import Config

def create_app(config_class=Config):
    """Application factory for Portfolio PMC Hub."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # =========================
    # INIT DB SAFELY (FIX HERE)
    # =========================
    from .models import db   # <-- moved INSIDE function
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

    # Context processors
    @app.context_processor
    def inject_globals():
        try:
            from .models import Portfolio, Year

            active_portfolios = Portfolio.query.filter_by(
                is_active=True
            ).order_by(Portfolio.display_order).all()

            active_year = Year.query.filter_by(is_active=True).first()

        except Exception:
            active_portfolios = []
            active_year = None

        return {
            "current_year": datetime.now().year,
            "active_portfolios": active_portfolios,
            "active_year": active_year,
            "current_user": session.get('admin_user')
        }

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template("errors/403.html"), 403

    # =========================
    # AUTO ADMIN SEED (FIXED) 
    # =========================
    with app.app_context():
        try:
            from .models import AdminUser, db

            if not AdminUser.query.first():
                admin = AdminUser(
                    username="admin",
                    email="admin@local.com",
                    role="admin",
                    is_active=True
                )
                admin.set_password("admin123")

                db.session.add(admin)
                db.session.commit()

                print("✅ AUTO ADMIN CREATED")

        except Exception as e:
            print("❌ SEED ERROR:", str(e))

    return app
