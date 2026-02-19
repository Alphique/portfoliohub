import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from a .env file
load_dotenv()

# Build the base directory path, assuming this config.py is in 'backend/app'
# This reliably finds the project root regardless of where the app is run from.
basedir = Path(__file__).resolve().parent.parent.parent

class Config:
    """Base configuration settings."""
    # Core
    SECRET_KEY = os.getenv('SECRET_KEY') or 'dev-key-please-change'
    
    # Use the absolute path for the SQLite database.
    # This ensures the database can be found whether the app is run via 'flask run'
    # or a direct Python script from any directory.
    SQLALCHEMY_DATABASE_URI = 'sqlite:///C:/ALPHACENTAURI/Portfolio Projects/portifolio-pmc-hub/backend/app/instance/app.db'

    
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