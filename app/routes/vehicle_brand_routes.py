from flask import Blueprint, jsonify, request
from app.models import VehicleBrand
from app.extensions import db
from app.utils.functions import serialize_brand, serialize_meta_pagination


vehicle_brand_bp = Blueprint("vehicle_brands", __name__)

@vehicle_brand_bp.route("/get-all", methods=["GET"])
def get_all_vehicle_brands():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 16, type=int)
    
    pagination = VehicleBrand.query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    vehicle_brands = serialize_brand(pagination.items)
    
    meta = serialize_meta_pagination(
        pagination.total, 
        pagination.pages, 
        pagination.page, 
        pagination.per_page
    )
    
    return jsonify({
        "vehicle_brands": vehicle_brands,
        "meta": meta
    }), 200