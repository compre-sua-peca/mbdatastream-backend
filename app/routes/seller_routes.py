from flask import Blueprint, Response, json, jsonify, request
from app.dal.dynamo_client import DynamoSingleton
from app.middleware.api_token import require_api_key
from app.models import Product
from app.services.seller_db_service import get_one_db_seller
from app.services.seller_db_service import get_all_labeled_custom_showcases, get_all_labels
from app.utils.functions import serialize_label, serialize_products


seller_bp = Blueprint("sellers", __name__)


@seller_bp.route("/by-id/<string:id_seller>", methods=["GET"])
@require_api_key
def get_seller_info_by_id(id_seller):
    db_seller = get_one_db_seller(id_seller)
    
    dynamo_client = DynamoSingleton()
    
    table = "CatalogSellers"
    key_name = "seller_domain"
    key_value = db_seller.seller_domain
    
    seller = dynamo_client.get_item_by_hash_key(table, key_name, key_value)
    
    return jsonify(seller), 200


@seller_bp.route("/<string:seller_domain>", methods=["GET"])
@require_api_key
def get_seller_info_by_domain(seller_domain):
    dynamo_client = DynamoSingleton()
    
    table = "CatalogSellers"
    key_name = "seller_domain"
    key_value = seller_domain
    
    seller = dynamo_client.get_item_by_hash_key(table, key_name, key_value)
    
    return jsonify(seller), 200


@seller_bp.route("/showcase", methods=["GET"])
@require_api_key
def get_showcase():
    dynamo_client = DynamoSingleton()
    
    table = "CatalogSellers"
    key_name = "seller_domain"
    # key_value = "mobensani"
    
    id_seller = request.args.get("id_seller", type=int)
    seller_domain = request.args.get("seller_domain", type=str)
    
    seller = dynamo_client.get_item_by_hash_key(table, key_name, seller_domain)
    
    labels = get_all_labels(id_seller)
    
    serialized_labels = serialize_label(labels)
    
    tags = seller.get("tags", [])
    
    showcase = {}
    
    custom_showcase = {}
    
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
        
    custom_showcase = get_all_labeled_custom_showcases(serialized_labels, id_seller)
    
    all_showcases = {**custom_showcase, **showcase}
    
    payload = json.dumps(all_showcases, ensure_ascii=False, sort_keys=False)
    
    return Response(payload, mimetype='application/json')

    
    
    