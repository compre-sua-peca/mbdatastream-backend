from .product_routes import product_bp
from .vehicle_routes import vehicle_bp
from .category_routes import category_bp

def register_routes(app):
    app.register_blueprint(product_bp, url_prefix="/product")
    app.register_blueprint(vehicle_bp, url_prefix="/vehicle")
    app.register_blueprint(category_bp, url_prefix="/category")