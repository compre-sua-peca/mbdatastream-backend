from .product_routes import product_bp
from .vehicle_routes import vehicle_bp
from .category_routes import category_bp
from .seller_routes import seller_bp
from .vehicle_brand_routes import vehicle_brand_bp

def register_routes(app):
    app.register_blueprint(product_bp, url_prefix="/product")
    app.register_blueprint(vehicle_bp, url_prefix="/vehicle")
    app.register_blueprint(category_bp, url_prefix="/category")
    app.register_blueprint(seller_bp, url_prefix="/seller")
    app.register_blueprint(vehicle_brand_bp, url_prefix="/vehicle-brand")