import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env
load_dotenv()

# Base directory (project root)
basedir = Path(__file__).resolve().parent.parent.parent


class Config:
    """Base configuration settings."""

    # =========================
    # CORE
    # =========================
    SECRET_KEY = os.getenv('SECRET_KEY') or 'dev-key-please-change'

    # =========================
    # DATABASE FIX (RENDER + LOCAL SAFE)
    # =========================

    # Ensure instance folder exists (VERY IMPORTANT for SQLite)
    INSTANCE_PATH = basedir / "instance"
    INSTANCE_PATH.mkdir(parents=True, exist_ok=True)

    DB_PATH = INSTANCE_PATH / "app.db"

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{DB_PATH}"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # =========================
    # SECURITY
    # =========================
    SESSION_COOKIE_SECURE = os.getenv('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # =========================
    # PERFORMANCE
    # =========================
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 20,
        'max_overflow': 10
    }


class ProductionConfig(Config):
    """Production configuration."""
    FLASK_ENV = 'production'
    DEBUG = False


class DevelopmentConfig(Config):
    """Development configuration."""
    FLASK_ENV = 'development'
    DEBUG = True
    SQLALCHEMY_ECHO = True
