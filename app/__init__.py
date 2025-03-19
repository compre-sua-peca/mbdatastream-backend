from flask import Flask
from config.settings import Config
from app.extensions import db, migrate
from app.routes import register_routes
from dotenv import load_dotenv

load_dotenv()

def create_app(config_class=Config):
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Register blueprints
    register_routes(app)
    
    return app