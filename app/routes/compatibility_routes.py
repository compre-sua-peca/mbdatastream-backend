from flask import Blueprint, jsonify, request
from app.middleware.api_token import require_api_key
from app.services.compatibility_service import get_compatibility_info, get_or_create_vehicle, get_or_create_vehicle_brand, handle_brand_compatibility, handle_compatibility

compatibility_bp = Blueprint("compatibility", __name__)


@compatibility_bp.route("/upsert/<string:cod_product>/<string:id_seller>", methods=["POST"])
@require_api_key
def upsert_compatibility(cod_product, id_seller):
    if not request.is_json:
        return jsonify({"error": "Request body must be JSON"}), 400

    data = request.get_json()

    compats = get_compatibility_info(data)

    if data is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    brands = []
    vehicles = []
    seen_hash_brands = set()
    seen_vehicles = set()

    for compat in compats:
        brand_name = compat.get("brand_name")

        brand = get_or_create_vehicle_brand(brand_name, id_seller)
        hash_brand = brand.hash_brand

        handle_brand_compatibility(
            brand_name, 
            hash_brand, 
            seen_hash_brands, 
            brands
        )

        years = compat.get("years")

        if years:
            year_values = [y.get("year")
                           for y in years if y.get("year") is not None]
            start_year = min(year_values) if year_values else None
            end_year = max(year_values) if year_values else None
        else:
            start_year = end_year = None

        vehicle = {
            "vehicle_name": compat.get("car_version"),
            "vehicle_type": "leve",
            "start_year": start_year,
            "end_year": end_year,
            "hash_brand": hash_brand
        }

        get_or_create_vehicle(
            hash_brand, 
            vehicle,
            vehicles, 
            id_seller, 
            seen_vehicles
        )

    compat_results = handle_compatibility(cod_product, vehicles)

    return jsonify({
        "message": "Compatibilidade de catálogo processada com sucesso!",
        "statistics": {
            "brands_processed": len(brands),
            "vehicles_processed": len(vehicles),
            "cod_product": cod_product,
            "compatibilities_created": len(compat_results.get("incoming")),
            "compatibilities_deleted": len(compat_results.get("to_delete"))
        }
    })
