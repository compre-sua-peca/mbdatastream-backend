from flask import Blueprint, jsonify, request
from app.dal.encryptor import HashGenerator
from app.models import Category, SellerCategories
from app.extensions import db
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError


category_bp = Blueprint("categories", __name__)


@category_bp.route("/all", methods=["GET"])
def get_all_categories():
    categories = Category.query.order_by(Category.display_order).all()

    results = []

    if categories:
        for category in categories:
            results.append({
                "hash_category": category.hash_category,
                "name_category": category.name_category
            })

    return jsonify(results), 200

# Create a new category
@category_bp.route("/", methods=["POST"])
def create_category():
    data = request.get_json()
    
    hash_generator = HashGenerator()
    
    try:
        with db.session.begin_nested():
            # Lock the rows to avoid race conditions
            
            name_category = data["name_category"]

            max_order = db.session.query(
                func.max(Category.display_order)).with_for_update().scalar()
            
            new_order = (max_order or 0) + 1
            
            treated_category_name = name_category.replace(" ", "")
            
            hash_category = hash_generator.generate_hash(treated_category_name)         

            new_category = Category(
                hash_category=hash_category,
                name_category=data["name_category"],
                display_order=new_order
            )
            
            db.session.add(new_category)
        db.session.commit()
    
    except SQLAlchemyError as e:
        db.session.rollback()
        
        raise e
    
    return jsonify({"message": "Category created successfully!"}), 201


@category_bp.route("/create-multiple-seller-categories", methods=["POST"])
def create_seller_categories():
    id_seller = request.args.get("id_seller", type=int)
    categories = request.json.get("category_names")
    
    if not categories or not id_seller:
        return jsonify({"error": "categories (array) and id_seller are required"}), 400
    
    total_created = 0
    response_details = []
    
    try:
        for category in categories:
            existing_category = Category.query.filter_by(
                name_category=category
            ).first()
            
            existing_seller_category = SellerCategories.query.filter_by(
                id_seller=id_seller,
                hash_category=existing_category.hash_category
            ).first()
            
            if not existing_seller_category:
                seller_category = SellerCategories(
                    id_seller = id_seller,
                    hash_category = existing_category.hash_category
                )
                
                db.session.add(seller_category)
                
                response_details.append({
                    "category": category
                })
                
                total_created += 1
                
        db.session.commit()
            
        return jsonify({
            "message": f"Processed {total_created} categories",
            "details": response_details
        })
        
    except SQLAlchemyError as e:
        db.session.rollback()
        
        raise e


# Retrieve a single category by its hash_category
@category_bp.route("/<string:hash_category>", methods=["GET"])
def get_category(hash_category):
    category = Category.query.filter_by(hash_category=hash_category).first()
    if not category:
        return jsonify({"message": "Category not found"}), 404

    data = {
        "hash_category": category.hash_category,
        "name_category": category.name_category
    }
    return jsonify(data), 200


# Update an existing category
@category_bp.route("/<string:hash_category>", methods=["PUT"])
def update_category(hash_category):
    category = Category.query.filter_by(hash_category=hash_category).first()
    if not category:
        return jsonify({"message": "Category not found"}), 404

    data = request.get_json()
    category.name_category = data.get("name_category", category.name_category)

    db.session.commit()
    return jsonify({"message": "Category updated successfully!"}), 200


# Remove a category
@category_bp.route("/<string:hash_category>", methods=["DELETE"])
def delete_category(hash_category):
    category = Category.query.filter_by(hash_category=hash_category).first()
    if not category:
        return jsonify({"message": "Category not found"}), 404

    db.session.delete(category)
    db.session.commit()
    return jsonify({"message": "Category deleted successfully!"}), 200
