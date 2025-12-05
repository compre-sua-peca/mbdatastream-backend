from flask import Blueprint, jsonify, request, send_file, current_app
import pandas as pd
from sqlalchemy import text, or_
from app.models import Product, Images, Category, Compatibility, Vehicle, SellerBrands, SellerVehicles, SellerCategories
from app.middleware.api_token import require_api_key
from app.extensions import db
from app.services.product_service import get_all_product_data, process_excel, transform_rows
from app.dal.S3_client import S3ClientSingleton
from app.utils.functions import is_image_file, extract_existing_product_codes, serialize_products, serialize_meta_pagination
from botocore.exceptions import BotoCoreError, ClientError
from werkzeug.utils import secure_filename


sitemap_bp = Blueprint("sitemap", __name__)


@sitemap_bp.route("/get-all-by-seller/<string:id_seller>", methods=["GET"])
@require_api_key
def get_all_products_by_seller(id_seller):
    is_manufactured_str = request.args.get("is_manufactured")

    is_manufactured = None
    if is_manufactured_str is not None:
        is_manufactured = is_manufactured_str.lower() == "true"

    pagination = None

    if is_manufactured is None:
        pagination = Product.query.filter(
            Product.id_seller == id_seller
        )

    else:
        pagination = Product.query.filter(
            Product.is_manufactured == is_manufactured,
            Product.id_seller == id_seller
        )

    products = serialize_products(pagination)
    
    return jsonify({
        "products": products
    }), 200
    

