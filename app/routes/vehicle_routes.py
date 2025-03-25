from flask import Blueprint, jsonify, request
from app.models import Vehicle
from app.extensions import db
from app.utils.functions import serialize_vehicle, serialize_meta_pagination
import json

vehicle_bp = Blueprint("vehicles", __name__)

# List all vehicles
@vehicle_bp.route("/", methods=["GET"])
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
