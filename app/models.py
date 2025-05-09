from .extensions import db

class Category(db.Model):
    hash_category = db.Column(db.String(255), primary_key=True)
    name_category = db.Column(db.String(255), nullable=False)
    display_order = db.Column(db.Integer, default=0, nullable=False)
    
    products = db.relationship('Product', backref='category', lazy=True)
    
    def __repr__(self):
        return f"Category('{self.hash_category}', '{self.name_category}')"

class Product(db.Model):
    cod_product = db.Column(db.String(255), primary_key=True)
    name_product = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(2500), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_manufactured = db.Column(db.Boolean, default=True)
    bar_code = db.Column(db.BigInteger, nullable=False)
    gear_quantity = db.Column(db.Integer, nullable=False)
    gear_dimensions = db.Column(db.String(255), nullable=True)
    cross_reference = db.Column(db.String(2500), nullable=True)
    hash_category = db.Column(db.String(255), db.ForeignKey('category.hash_category', onupdate="CASCADE"), nullable=False)
    
    images = db.relationship('Images', backref='product', lazy=True)
    compatibilities = db.relationship('Compatibility', backref='product', lazy=True)
    
    def __repr__(self):
        return f"Product('{self.cod_product}', '{self.name_product}', '{self.bar_code}', '{self.gear_quantity}', '{self.gear_dimensions}', '{self.cross_reference}', '{self.hash_category}')"
    
class Images(db.Model):
    cod_product = db.Column(db.String(255), db.ForeignKey('product.cod_product', onupdate="CASCADE"), nullable=False)
    id_image = db.Column(db.String(255), primary_key=True)
    url = db.Column(db.String(255), nullable=False)
    
    def __repr__(self):
        return f"Images('{self.cod_product}', '{self.url}')"
    
class Vehicle(db.Model):
    vehicle_name = db.Column(db.String(255), primary_key=True)
    start_year = db.Column(db.String(4), nullable=False)
    end_year = db.Column(db.String(4), nullable=True)
    vehicle_type = db.Column(db.String(255), nullable=False)
    hash_brand = db.Column(db.String(255), db.ForeignKey('vehicle_brand.hash_brand', onupdate="CASCADE"), nullable=False)
    
    compatibilities = db.relationship('Compatibility', backref='vehicle', lazy=True)
    vehicle_brand = db.relationship('VehicleBrand', backref='vehicles', lazy=True)
    
class Compatibility(db.Model):
    cod_product = db.Column(db.String(255), db.ForeignKey('product.cod_product', onupdate="CASCADE"), primary_key=True)
    vehicle_name = db.Column(db.String(255), db.ForeignKey('vehicle.vehicle_name', onupdate="CASCADE"), primary_key=True)
    
    def __repr__(self):
        return f"Compatibility('{self.cod_product}', '{self.vehicle_name}')"
    
class VehicleBrand(db.Model):
    __tablename__ = "vehicle_brand"
    hash_brand = db.Column(db.String(255), primary_key=True)
    brand_name = db.Column(db.String(255), nullable=False)
    brand_image = db.Column(db.String(255), nullable=True)
    display_order = db.Column(db.Integer, default=0, nullable=False)
    
    
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    cnpj = db.Column(db.String(20), nullable=False)
    whatsapp = db.Column(db.String(150), nullable=False)
    
    def serialize(self):
        return {
            "username": self.username,
            "email": self.email
        }