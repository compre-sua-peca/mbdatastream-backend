from flask import Blueprint, jsonify, request
from sqlalchemy import func
from app.dal.S3_client import S3ClientSingleton
from app.dal.encryptor import HashGenerator
from app.models import VehicleBrand
from app.extensions import db
from app.utils.functions import serialize_brand, serialize_meta_pagination
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from flask import request, jsonify


vehicle_brand_bp = Blueprint("vehicle_brands", __name__)


@vehicle_brand_bp.route("/all", methods=["GET"])
def get_all_vehicle_brands():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 16, type=int)
    
    pagination = VehicleBrand.query.order_by(VehicleBrand.display_order).paginate(
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
    
    
@vehicle_brand_bp.route("/<string:hash_brand>")
def get_vehicle_brand(hash_brand):
    vehicle_brand = VehicleBrand.query.filter_by(hash_brand=hash_brand).first()
    
    if not vehicle_brand:
        return jsonify({"message": "Não existe a marca informada"}), 404
    
    data = {
        "brand_image": vehicle_brand.brand_image,
        "brand_name": vehicle_brand.brand_name,
        "hash_brand": vehicle_brand.hash_brand
    }
    
    return jsonify(data), 200


@vehicle_brand_bp.route("/", methods=["POST"])
def create_vehicle_brand():
    # The request is expected to be multipart/form-data.
    # Text fields are in request.form and files are in request.files.
    data = request.form.to_dict()
    BUCKET_NAME = "catalog-vehicle-brand-logos"
    
    hash_generator = HashGenerator()
    s3_client = S3ClientSingleton()
    
    try:
        with db.session.begin_nested():
            # Retrieve text fields from the form data.
            brand_name = data.get("brand_name")
            
            if not brand_name:
                return jsonify({"error": "brand_name is required"}), 400
            
            # Determine the display_order: if provided, use it; otherwise, compute the next value.
            display_order_str = data.get("display_order")
            
            if display_order_str is None or display_order_str == "":
                max_order = db.session.query(func.max(VehicleBrand.display_order)).scalar() or 0
                
                display_order = max_order + 1
            else:
                display_order = int(display_order_str)
            
            # Generate a unique hash for the brand based on the brand name (spaces removed).
            treated_brand_name = brand_name.replace(" ", "")
            hash_brand = hash_generator.generate_hash(treated_brand_name)
            
            # Create a new VehicleBrand instance.
            new_vehicle_brand = VehicleBrand(
                hash_brand=hash_brand,
                brand_name=brand_name,
                display_order=display_order
            )
            
            # If an image is included in the request files, handle the upload.
            if "brand_image" in request.files:
                image_file = request.files["brand_image"]
                # Create a unique S3 object name. You can modify the folder path as needed.
                object_name = f"mobensani/{hash_brand}_{image_file.filename}"
                
                # Upload the image file to S3.
                response = s3_client.upload_image(image_file, BUCKET_NAME, object_name)
                
                if response:
                    # Construct the public URL for the uploaded image.
                    image_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{object_name}"
                    
                    new_vehicle_brand.image_url = image_url
                else:
                    db.session.rollback()
                    
                    return jsonify({"error": "Image upload failed"}), 500
            else:
                # If no image is provided, set image_url to None or a default URL.
                new_vehicle_brand.image_url = None
            
            # Add the new vehicle brand to the session.
            db.session.add(new_vehicle_brand)
        
        # Commit the transaction.
        db.session.commit()
        
        # Return a response with the newly created vehicle brand data.
        return jsonify({
            "hash_brand": new_vehicle_brand.hash_brand,
            "brand_name": new_vehicle_brand.brand_name,
            "display_order": new_vehicle_brand.display_order,
            "image_url": new_vehicle_brand.image_url
        }), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@vehicle_brand_bp.route("/<string:hash_brand>", methods=["DELETE"])
def delete_vehicle_brand(hash_brand):
    vehicle_brand = VehicleBrand.query.filter_by(hash_brand).first()
    
    if not vehicle_brand:
        return jsonify({"message": "Vehicle brand not found"}), 404
    
    db.session.delete(vehicle_brand)
    db.session.commit()
    
    return jsonify({"message": "Vehicle brand deleted successfully"}), 200