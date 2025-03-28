from flask import Flask

from config.settings import Config
from app.extensions import db, migrate, setup_async_sqlalchemy
from app.routes import register_routes

def create_app(config_class=Config):
    """Application factory pattern"""
    app = Flask(__name__)
    
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    with app.app_context():
        setup_async_sqlalchemy(app)
    
    # Register blueprints
    register_routes(app)
    
    return app