import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from a .env file
load_dotenv()

# Build the base directory path (project root)
basedir = Path(__file__).resolve().parent.parent.parent


class Config:
    """Base configuration settings."""

    # Core
    SECRET_KEY = os.getenv('SECRET_KEY') or 'dev-key-please-change'

    # ==============================
    # FIX: Render + Local compatible DB path
    # ==============================
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL") or f"sqlite:///{basedir / 'instance' / 'app.db'}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Security
    SESSION_COOKIE_SECURE = os.getenv('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Performance
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 20,
        'max_overflow': 10
    }


class ProductionConfig(Config):
    """Production specific configuration."""
    FLASK_ENV = 'production'
    DEBUG = False


class DevelopmentConfig(Config):
    """Development specific configuration."""
    FLASK_ENV = 'development'
    DEBUG = True
    SQLALCHEMY_ECHO = True
