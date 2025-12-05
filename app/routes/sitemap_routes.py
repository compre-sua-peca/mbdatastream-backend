from flask import Blueprint, jsonify, request, send_file, current_app
import pandas as pd
from sqlalchemy import text, or_
from app.models import Manufacturer, Product, Images, Category, Compatibility, SellerManufacturer, Vehicle, SellerBrands, SellerVehicles, SellerCategories, VehicleBrand
from app.middleware.api_token import require_api_key
from app.extensions import db
from app.services.product_service import get_all_product_data, process_excel, transform_rows
from app.dal.S3_client import S3ClientSingleton
from app.utils.functions import is_image_file, extract_existing_product_codes, serialize_brand, serialize_category, serialize_manufacturer, serialize_products, serialize_meta_pagination, serialize_vehicle_product, serialize_vehicle_product_count
from botocore.exceptions import BotoCoreError, ClientError
from werkzeug.utils import secure_filename


sitemap_bp = Blueprint("sitemap", __name__)


@sitemap_bp.route("/get-all-products/<string:id_seller>", methods=["GET"])
@require_api_key
def get_all_products_by_seller(id_seller):
    is_manufactured_str = request.args.get("is_manufactured")

    is_manufactured = None
    if is_manufactured_str is not None:
        is_manufactured = is_manufactured_str.lower() == "true"

    # select only the two fields we need
    query = Product.query.with_entities(Product.cod_product, Product.name_product)
    query = query.filter(Product.id_seller == id_seller)

    if is_manufactured is not None:
        query = query.filter(Product.is_manufactured == is_manufactured)

    rows = query.all()  # list of tuples (code_product, name_product)

    products = [
        {"code_product": code, "name_product": name}
        for code, name in rows
    ]

    return jsonify({"products": products}), 200


@sitemap_bp.route("/get-all-categories/<string:id_seller>", methods=["GET"])
@require_api_key
def get_all_categories(id_seller):    
    # Join Category ← SellerCategories for this seller, ordered by display_order
    category_rows = (
        db.session.query(Category)
            .join(SellerCategories, SellerCategories.hash_category == Category.hash_category)
            .filter(SellerCategories.id_seller == id_seller)
            .order_by(Category.display_order)
            .all()
    )

    # Run your serializer to turn the Category models into plain dicts
    categories = serialize_category(category_rows)

    # If the list is empty, tell the client “no categories found”
    if not categories:
        return jsonify({"error": "Nenhuma categoria encontrado para esse seller!"}), 400

    # Return a JSON object with a "categories" field
    return jsonify({
        "categories": categories
    }), 200
    
    
@sitemap_bp.route("/get-all-manufacturers/<int:id_seller>", methods=["GET"])
@require_api_key
def get_manufacturers_by_seller(id_seller):
    query = db.session.query(Manufacturer).join(
        SellerManufacturer,
        SellerManufacturer.id_manufacturer == Manufacturer.id
    ).filter(SellerManufacturer.id_seller == id_seller)

    manufacturers = [serialize_manufacturer(m) for m in query.all()]

    return jsonify({
        "manufacturers": manufacturers
    }), 200
    
    
@sitemap_bp.route("/get-all-brands/<string:id_seller>", methods=["GET"])
@require_api_key
def get_all_vehicle_brands_no_pagination(id_seller):
    query = db.session.query(VehicleBrand)\
        .join(SellerBrands, SellerBrands.hash_brand == VehicleBrand.hash_brand)\
        .filter(SellerBrands.id_seller == id_seller)

    # Get ALL results (no pagination)
    results = query.all()

    vehicle_brands = serialize_brand(results)

    return jsonify({
        "vehicle_brands": vehicle_brands
    }), 200
    
    
@sitemap_bp.route("/get-all-vehicles-brands/<string:id_seller>", methods=["GET"])
@require_api_key
def get_all_vehicle_brands(id_seller):
    query = db.session.query(VehicleBrand)\
        .join(SellerBrands, SellerBrands.hash_brand == VehicleBrand.hash_brand)\
        .filter(SellerBrands.id_seller == id_seller)

    # Get ALL results (no pagination)
    results = query.all()

    vehicle_brands = serialize_brand(results)

    return jsonify({
        "vehicle_brands": vehicle_brands
    }), 200


@sitemap_bp.route("/get-all-vehicles/<string:id_seller>", methods=["GET"])
@require_api_key
def get_vehicles(id_seller):
    # Build base query (Vehicle + count of Compatibility.cod_product)
    query = db.session.query(Vehicle)\
    .join(SellerVehicles, SellerVehicles.vehicle_name == Vehicle.vehicle_name)\
    .outerjoin(Compatibility, Compatibility.vehicle_name == Vehicle.vehicle_name)\
    .filter(SellerVehicles.id_seller == id_seller)\
    .group_by(Vehicle.vehicle_name)

    # Get all results (no pagination)
    results = query.all()  # list of (Vehicle, product_count) tuples

    vehicles_product_count = serialize_vehicle_product(results)

    return jsonify({
        "vehicles": vehicles_product_count
    }), 200