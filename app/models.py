from .extensions import db

class Category(db.Model):
    hash_category = db.Column(db.String(255), primary_key=True)
    name_category = db.Column(db.String(255), nullable=False)
    
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
    hash_category = db.Column(db.String(255), db.ForeignKey('category.hash_category'), nullable=False)
    
    images = db.relationship('Images', backref='product', lazy=True)
    compatibilities = db.relationship('Compatibility', backref='product', lazy=True)
    
    def __repr__(self):
        return f"Product('{self.cod_product}', '{self.name_product}', '{self.bar_code}', '{self.gear_quantity}', '{self.gear_dimensions}', '{self.cross_reference}', '{self.hash_category}')"
    
class Images(db.Model):
    cod_product = db.Column(db.String(255), db.ForeignKey('product.cod_product'), nullable=False)
    id_image = db.Column(db.String(255), primary_key=True)
    url = db.Column(db.String(255), nullable=False)
    
    def __repr__(self):
        return f"Images('{self.cod_product}', '{self.url}')"
    
class Vehicle(db.Model):
    vehicle_name = db.Column(db.String(255), primary_key=True)
    start_year = db.Column(db.String(4), nullable=False)
    end_year = db.Column(db.String(4), nullable=True)
    vehicle_type = db.Column(db.String(255), nullable=False)
    hash_brand = db.Column(db.String(255), db.ForeignKey('vehicle_brand.hash_brand'), nullable=False)
    
    compatibilities = db.relationship('Compatibility', backref='vehicle', lazy=True)
    vehicle_brand = db.relationship('VehicleBrand', backref='vehicles', lazy=True)
    
class Compatibility(db.Model):
    cod_product = db.Column(db.String(255), db.ForeignKey('product.cod_product'), primary_key=True)
    vehicle_name = db.Column(db.String(255), db.ForeignKey('vehicle.vehicle_name'), primary_key=True)
    
    def __repr__(self):
        return f"Compatibility('{self.cod_product}', '{self.vehicle_name}')"
    
class VehicleBrand(db.Model):
    __tablename__ = "vehicle_brand"
    hash_brand = db.Column(db.String(255), primary_key=True)
    brand_name = db.Column(db.String(255), nullable=False)
    brand_image = db.Column(db.String(255), nullable=True)
    