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
    bar_code = db.Column(db.BigInteger, nullable=True)
    gear_quantity = db.Column(db.Integer, nullable=True)
    gear_dimensions = db.Column(db.String(255), nullable=True)
    cross_reference = db.Column(db.String(2500), nullable=True)
    hash_category = db.Column(db.String(255), db.ForeignKey(
        'category.hash_category', onupdate="CASCADE", ondelete="CASCADE"
    ), nullable=False)
    id_seller = db.Column(db.Integer, db.ForeignKey(
        'seller.id', onupdate="CASCADE", ondelete="CASCADE"
    ), nullable=True)

    images = db.relationship('Images', backref='product', lazy=True, cascade="all" )
    compatibilities = db.relationship(
        'Compatibility', backref='product', lazy=True)

    def __repr__(self):
        return f"Product('{self.cod_product}', '{self.name_product}', '{self.bar_code}', '{self.gear_quantity}', '{self.gear_dimensions}', '{self.cross_reference}', '{self.hash_category}')"


class Images(db.Model):
    __tablename__ = "images"

    cod_product = db.Column(
        db.String(255),
        db.ForeignKey(
            'product.cod_product', onupdate="CASCADE", ondelete="CASCADE"
        ),
        primary_key=True,  # passa a fazer parte da PK composta
        nullable=False
    )

    id_image = db.Column(
        db.String(255),
        primary_key=True,  # continua como parte da PK composta
        nullable=False
    )

    url = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f"Images('{self.cod_product}', '{self.id_image}', '{self.url}')"


class Vehicle(db.Model):
    vehicle_name = db.Column(db.String(255), primary_key=True)
    start_year = db.Column(db.String(4), nullable=True)
    end_year = db.Column(db.String(4), nullable=True)
    vehicle_type = db.Column(db.String(255), nullable=False)
    hash_brand = db.Column(db.String(255), db.ForeignKey(
        'vehicle_brand.hash_brand', onupdate="CASCADE", ondelete="CASCADE"
    ), nullable=False)

    compatibilities = db.relationship(
        'Compatibility', backref='vehicle', lazy=True)
    vehicle_brand = db.relationship(
        'VehicleBrand', backref='vehicles', lazy=True)


class Compatibility(db.Model):
    cod_product = db.Column(db.String(255), db.ForeignKey(
        'product.cod_product', onupdate="CASCADE", ondelete="CASCADE"
    ), primary_key=True)
    vehicle_name = db.Column(db.String(255), db.ForeignKey(
        'vehicle.vehicle_name', onupdate="CASCADE", ondelete="CASCADE"
    ), primary_key=True)

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

class SellerUsers(db.Model):
    __tablename__ = 'seller_users'
    id_seller = db.Column(db.Integer, db.ForeignKey('seller.id', onupdate="CASCADE", ondelete="CASCADE"), primary_key=True)
    id_user = db.Column(db.Integer, db.ForeignKey('user.id', onupdate="CASCADE", ondelete="CASCADE"), primary_key=True)

    seller = db.relationship("Seller", backref="user_seller")
    user = db.relationship("User", backref="user_seller")

class Seller(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(75), unique=True, nullable=False)
    cnpj = db.Column(db.String(20), unique=True, nullable=False)


class SellerVehicles(db.Model):
    id_seller = db.Column(db.Integer, db.ForeignKey(
        'seller.id', onupdate="CASCADE", ondelete="CASCADE"
    ), primary_key=True)
    vehicle_name = db.Column(db.String(255), db.ForeignKey(
        'vehicle.vehicle_name', onupdate="CASCADE", ondelete="CASCADE"
    ), primary_key=True)

    sellers = db.relationship(
        'Seller', backref='seller_v', lazy=True
    )
    vehicles = db.relationship(
        'Vehicle', backref='vehicle_s', lazy=True
    )


class SellerBrands(db.Model):
    id_seller = db.Column(db.Integer, db.ForeignKey(
        'seller.id', onupdate="CASCADE", ondelete="CASCADE"
    ), primary_key=True)
    hash_brand = db.Column(db.String(255), db.ForeignKey(
        'vehicle_brand.hash_brand', onupdate="CASCADE", ondelete="CASCADE"
    ), primary_key=True)

    sellers = db.relationship(
        'Seller', backref='seller_b', lazy=True
    )
    vehicle_brand = db.relationship(
        'VehicleBrand', backref='brands_s', lazy=True
    )


class SellerCategories(db.Model):
    id_seller = db.Column(db.Integer, db.ForeignKey(
        'seller.id', onupdate="CASCADE", ondelete="CASCADE"
    ), primary_key=True)
    hash_category = db.Column(db.String(255), db.ForeignKey(
        'category.hash_category', onupdate="CASCADE", ondelete="CASCADE"
    ), primary_key=True)

    sellers = db.relationship(
        'Seller', backref='seller_c', lazy=True
    )
    categories = db.relationship(
        'Category', backref='category_s', lazy=True
    )


class Label(db.Model):
    name = db.Column(db.String(255), primary_key=True)
    id_seller = db.Column(db.Integer, db.ForeignKey(
        'seller.id', onupdate="CASCADE", ondelete="CASCADE"
    ), primary_key=True)

 
class CustomShowcase(db.Model):
    cod_product = db.Column(db.String(255), db.ForeignKey(
        'product.cod_product', onupdate="CASCADE", ondelete="CASCADE"
    ), primary_key=True)
    order = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(255), db.ForeignKey(
        'label.name', onupdate="CASCADE", ondelete="CASCADE"
    ), primary_key=True)