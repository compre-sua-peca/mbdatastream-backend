from flask import Blueprint, jsonify, request
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from app.models import Compatibility, SellerVehicles, Vehicle, VehicleBrand
from app.extensions import db
from app.utils.functions import serialize_vehicle, serialize_meta_pagination, serialize_product, serialize_vehicle_product_count


vehicle_bp = Blueprint("vehicles", __name__)


@vehicle_bp.route("/all", methods=["GET"])
def get_vehicles_count_prods():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 16, type=int)
    id_seller = request.args.get("id_seller", type=int)
    
    print(id_seller)

    # Build base query
    query = db.session.query(
        Vehicle,
        func.count(Compatibility.cod_product).label("product_count")
    )\
    .join(SellerVehicles, SellerVehicles.vehicle_name == Vehicle.vehicle_name)\
    .outerjoin(Compatibility, Compatibility.vehicle_name == Vehicle.vehicle_name)\
    .filter(SellerVehicles.id_seller == id_seller)\
    .group_by(Vehicle.vehicle_name)

    # Paginate the query
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    vehicles_product_count = serialize_vehicle_product_count(pagination.items)

    meta = serialize_meta_pagination(
        pagination.total,
        pagination.pages,
        pagination.page,
        pagination.per_page
    )

    return jsonify({
        "vehicles": vehicles_product_count,
        "meta": meta
    })


# List all vehicles
"""
@vehicle_bp.route("/all", methods=["GET"])
def get_vehicles():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 16, type=int)
    
    pagination = Vehicle.query.paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
   
    vehicles = serialize_vehicle(pagination.items)
    
    meta = serialize_meta_pagination(
        pagination.total, 
        pagination.pages, 
        pagination.page, 
        pagination.per_page
    )
        
    return jsonify({
        "vehicles": vehicles,
        "meta": meta   
    }), 200
"""
   
    
@vehicle_bp.route("/brand/<string:hash_brand>", methods=["GET"])
def get_by_vehicle_brand(hash_brand):
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 16, type=int)
    id_seller = request.args.get("id_seller", type=str)
    
    if not hash_brand:
        return jsonify({"message": "Nenhuma marca de veículo informada"}), 400
    
    brand = VehicleBrand.query.filter(VehicleBrand.hash_brand == hash_brand).first()
    
    if not brand:
        return jsonify({"message": f"Marca '{hash_brand}' não encontrada"}), 404
    
    query = db.session.query(
        Vehicle,
        func.count(Compatibility.cod_product).label("product_count")
    )\
    .join(SellerVehicles, SellerVehicles.vehicle_name == Vehicle.vehicle_name)\
    .outerjoin(Compatibility, Compatibility.vehicle_name == Vehicle.vehicle_name)\
    .filter(Vehicle.hash_brand == brand.hash_brand, SellerVehicles.id_seller == id_seller)\
    .group_by(Vehicle.vehicle_name)
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    vehicles = serialize_vehicle_product_count(pagination.items)
    
    meta = serialize_meta_pagination(
        pagination.total,
        pagination.pages,
        pagination.page,
        pagination.per_page
    )
    
    return jsonify({
        "vehicles": vehicles,
        "meta": meta
    })
    

# Create a new vehicle
@vehicle_bp.route("/", methods=["POST"])
def create_vehicle():
    data = request.get_json()
    new_vehicle = Vehicle(
        vehicle_name=data["vehicle_name"],
        start_year=data["start_year"],
        end_year=data["end_year"],
        vehicle_type=data["vehicle_type"]
    )
    db.session.add(new_vehicle)
    db.session.commit()
    return jsonify({"message": "Vehicle created successfully!"}), 201


# Retrieve a single vehicle by its vehicle_name
@vehicle_bp.route("/<string:vehicle_name>", methods=["GET"])
def get_vehicle(vehicle_name):
    vehicle = Vehicle.query.filter_by(vehicle_name=vehicle_name).first()
    if not vehicle:
        return jsonify({"message": "Vehicle not found"}), 404

    data = {
        "vehicle_name": vehicle.vehicle_name,
        "start_year": vehicle.start_year,
        "end_year": vehicle.end_year,
        "vehicle_type": vehicle.vehicle_type
    }
    return jsonify(data), 200


# Retrieve a single vehicle by its vehicle_name
@vehicle_bp.route("/search/<string:vehicle_name>", methods=["GET"])
def search_vehicle(vehicle_name):
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 16, type=int)
    id_seller = request.args.get("id_seller", type=int)
    
    transformed_vehicle_name = vehicle_name.upper()
    
    try:
        query = Vehicle.query\
        .join(SellerVehicles, SellerVehicles.vehicle_name == Vehicle.vehicle_name)\
        .filter(Vehicle.vehicle_name.ilike(f"%{transformed_vehicle_name}%"), SellerVehicles.id_seller == id_seller)
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
        if not pagination.items:
            return jsonify({"message": "Vehicle not found"}), 404

        filtered_vehicles = serialize_vehicle(pagination.items)
        
        meta = serialize_meta_pagination(
            pagination.total, 
            pagination.pages, 
            pagination.page, 
            pagination.per_page
        )
        
        return jsonify({
            "vehicles": filtered_vehicles,
            "meta": meta
        }), 200
        
    except SQLAlchemyError as e:
        db.session.rollback()
        
        raise e
    

# Create seller vehicles relationships
@vehicle_bp.route("/create-seller-vehicles", methods=["POST"])
def add_seller_vehicles_by_brand():
    brand_name = request.args.get("brand_name")
    id_seller = request.args.get("id_seller", type=int)
    
    print(brand_name)
    
    if not brand_name or not id_seller:
        return jsonify({"error": "brand_name and id_seller are required"}), 400
    
    try:
        # Fetch all vehicles matching the brand name
        vehicles = Vehicle.query\
            .join(VehicleBrand)\
            .filter(VehicleBrand.brand_name == brand_name).all()
            
        if not vehicles:
            return jsonify({"message": f"No vehicles found for brand '{brand_name}"}), 404
        
        created = 0
        
        for vehicle in vehicles:
            # Check if relationship already exists
            existing = SellerVehicles.query.filter_by(
                id_seller = id_seller,
                vehicle_name = vehicle.vehicle_name
            ).first()
            
            if not existing:
                seller_vehicle = SellerVehicles(
                    id_seller = id_seller,
                    vehicle_name = vehicle.vehicle_name
                )
                db.session.add(seller_vehicle)
                created += 1
                
        db.session.commit()

        return jsonify({
            "message": f"Successfully linked {created} vehicles of brand '{brand_name}' to seller ID {id_seller}"
        }), 201
        
    except SQLAlchemyError as e:
        
        raise e
    
    
@vehicle_bp.route("/create-multiple-seller-vehicles", methods=["POST"])
def add_seller_vehicles_by_brands():
    id_seller = request.args.get("id_seller", type=int)
    brand_names = request.json.get("brand_names") if request.is_json else request.args.getlist("brand_name")
    
    if not brand_names or not id_seller:
        return jsonify({"error": "brand_names (array) and id_seller are required"}), 400
    
    total_created = 0
    response_details = []
    
    try:
    
        for brand_name in brand_names:
            vehicles = Vehicle.query\
                .join(VehicleBrand)\
                .filter(VehicleBrand.brand_name == brand_name).all()
            
            if not vehicles:
                response_details.append({"brand": brand_name, "message": "No vehicles found"})
                continue

            created = 0
            for vehicle in vehicles:
                existing = SellerVehicles.query.filter_by(
                    id_seller=id_seller,
                    vehicle_name=vehicle.vehicle_name
                ).first()

                if not existing:
                    seller_vehicle = SellerVehicles(
                        id_seller=id_seller,
                        vehicle_name=vehicle.vehicle_name
                    )
                    db.session.add(seller_vehicle)
                    created += 1

            total_created += created
            response_details.append({
                "brand": brand_name,
                "linked": created
            })

        db.session.commit()

        return jsonify({
            "message": f"Processed {len(brand_names)} brands",
            "total_created": total_created,
            "details": response_details
        }), 201
    
    except SQLAlchemyError as e:
        db.session.rollback()
        
        raise e


# Update an existing vehicle
@vehicle_bp.route("/<string:vehicle_name>", methods=["PUT"])
def update_vehicle(vehicle_name):
    vehicle = Vehicle.query.filter_by(vehicle_name=vehicle_name).first()
    if not vehicle:
        return jsonify({"message": "Vehicle not found"}), 404

    data = request.get_json()
    vehicle.start_year = data.get("start_year", vehicle.start_year)
    vehicle.end_year = data.get("end_year", vehicle.end_year)
    vehicle.vehicle_type = data.get("vehicle_type", vehicle.vehicle_type)

    db.session.commit()
    return jsonify({"message": "Vehicle updated successfully!"}), 200


# DELETE: Remove a vehicle
@vehicle_bp.route("/<string:vehicle_name>", methods=["DELETE"])
def delete_vehicle(vehicle_name):
    vehicle = Vehicle.query.filter_by(vehicle_name=vehicle_name).first()
    if not vehicle:
        return jsonify({"message": "Vehicle not found"}), 404

    db.session.delete(vehicle)
    db.session.commit()
    return jsonify({"message": "Vehicle deleted successfully!"}), 200
