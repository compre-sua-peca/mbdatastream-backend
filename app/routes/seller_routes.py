from flask import Blueprint, jsonify, request
import os
from app.dal.dynamo_client import DynamoSingleton
from app.models import Product
from app.utils.functions import serialize_product

seller_bp = Blueprint("sellers", __name__)


@seller_bp.route("/", methods=["GET"])
def get_seller_info():
    dynamo_client = DynamoSingleton()
    
    table = "CatalogSellers"
    key_name = "seller_domain"
    key_value = "mobensani"
    
    seller = dynamo_client.get_item_by_hash_key(table, key_name, key_value)
    
    return jsonify(seller), 200

@seller_bp.route("/showcase", methods=["GET"])
def get_showcase():
    dynamo_client = DynamoSingleton()
    
    table = "CatalogSellers"
    key_name = "seller_domain"
    key_value = "mobensani"
    
    seller = dynamo_client.get_item_by_hash_key(table, key_name, key_value)
    
    tags = seller.get("tags", [])
    
    showcase = {}
    
    for tag in tags:
        # Debug: Print tag values
        tag_id = tag.get("id")
        tag_name = tag.get("name")
        
        per_page = 15
        
        # Ensure that the tag id is the correct type (assuming Product.hash_category is stored as a string)
        category_id = str(tag_id)
        
        pagination = Product.query.filter_by(hash_category=category_id).limit(per_page).all()
        product = serialize_product(pagination)
        
        showcase[tag_name] = product
    
    return jsonify(showcase)

    
    
    