from flask import Blueprint, jsonify, request
from app.models import Category
from app.extensions import db

category_bp = Blueprint("categories", __name__)

@category_bp.route("/get-all", methods=["GET"])
def get_all_categories():
    category = Category.query.all()
    
    results = []
    
    if category:
        for category in category:
            results.append({
                "hash_category": category.hash_category,
                "name_category": category.name_category
            })
            
    return jsonify(results), 200

# Create a new category
@category_bp.route("/", methods=["POST"])
def create_category():
    data = request.get_json()
    new_category = Category(
        hash_category=data["hash_category"],
        name_category=data["name_category"]
    )
    db.session.add(new_category)
    db.session.commit()
    return jsonify({"message": "Category created successfully!"}), 201


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
