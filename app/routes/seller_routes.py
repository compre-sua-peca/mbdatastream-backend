from flask import Blueprint, jsonify, request
from app.dal.dynamo_client import DynamoSingleton
from app.models import Product
from app.utils.functions import serialize_products


seller_bp = Blueprint("sellers", __name__)


@seller_bp.route("/<string:seller_domain>", methods=["GET"])
def get_seller_info(seller_domain):    
    dynamo_client = DynamoSingleton()
    
    table = "CatalogSellers"
    key_name = "seller_domain"
    key_value = seller_domain
    
    seller = dynamo_client.get_item_by_hash_key(table, key_name, key_value)
    
    return jsonify(seller), 200


@seller_bp.route("/showcase", methods=["GET"])
def get_showcase():
    dynamo_client = DynamoSingleton()
    
    table = "CatalogSellers"
    key_name = "seller_domain"
    # key_value = "mobensani"
    
    id_seller = request.args.get("id_seller", type=int)
    seller_domain = request.args.get("seller_domain", type=str)
    
    seller = dynamo_client.get_item_by_hash_key(table, key_name, seller_domain)
    
    tags = seller.get("tags", [])
    
    showcase = {}
    
    for tag in tags:
        # Debug: Print tag values
        tag_id = tag.get("id")
        tag_name = tag.get("name")
        
        per_page = 15
        
        # Ensure that the tag id is the correct type (assuming Product.hash_category is stored as a string)
        # category_id = str(tag_id)
        
        pagination = Product.query.filter_by(
            hash_category=tag_id,
            id_seller=id_seller
        ).limit(per_page).all()
        
        product = serialize_products(pagination)
        
        showcase[tag_name] = product
    
    return jsonify(showcase)

    
    
    