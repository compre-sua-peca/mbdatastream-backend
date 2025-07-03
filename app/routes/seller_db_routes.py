from flask import Blueprint, request, jsonify
from sqlalchemy import text
from app.extensions import db
from app.models import Seller, Label, CustomShowcase
from sqlalchemy.exc import SQLAlchemyError
from app.services.seller_db_service import get_all_labels, get_all_showcase_items, get_one_label, get_one_similar_label
from app.utils.functions import serialize_label, serialize_custom_showcase, serialize_seller_showcase_items


seller_db_bp = Blueprint("seller-db", __name__)


@seller_db_bp.route("/create", methods=["POST"])
def create_seller():
    data = request.get_json()

    try:
        new_seller = Seller(
            name=data["name"],
            cnpj=data["cnpj"]
        )

        db.session.add(new_seller)

        db.session.commit()

    except SQLAlchemyError as e:
        db.session.rollback()

        raise e

    return jsonify({"message": "Seller created successfully"}), 201


@seller_db_bp.route("/create-label/<string:id_seller>", methods=["POST"])
def create_showcase_label(id_seller):
    data = request.get_json()

    try:
        new_label = Label(
            id_seller=id_seller,
            name=data.get("name", "")
        )

        db.session.add(new_label)

        db.session.commit()

        return jsonify({"message": "Label created successfully"}), 201

    except SQLAlchemyError as e:
        db.session.rollback()

        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@seller_db_bp.route("/get-all-labels/<string:id_seller>", methods=["GET"])
def get_all_showcase_labels(id_seller):
    try:
        labels = get_all_labels(id_seller=id_seller)

        if not labels:
            return jsonify({"message": "No labels found!"}), 404

        serialized_labels = serialize_label(labels)

        return jsonify(serialized_labels)

    except SQLAlchemyError as e:

        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@seller_db_bp.route("/get-one-label/<string:name>", methods=["GET"])
def get_one_showcase_label(name):
    try:
        label = get_one_similar_label(name)

        if not label:
            return jsonify({"message": f"No label with name equal '{name}'"})

        serialized_label = serialize_label([label])

        return jsonify(serialized_label)

    except SQLAlchemyError as e:

        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@seller_db_bp.route("/update-label/<string:name>", methods=["PUT"])
def update_one_showcase_label(name):
    try:
        data = request.get_json()

        existing_label = get_one_label(name=name)

        if not existing_label:
            return jsonify({"message": f"Label '{name}' does not exist"})

        existing_label.name = data.get("name", "")

        db.session.commit()

        serialized_label = serialize_label([existing_label])

        return ({
            "message": f"Label '{name}' updated with sucess to {existing_label.name}",
            "updated": serialized_label
        })

    except SQLAlchemyError as e:

        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@seller_db_bp.route("/delete-label/<string:name>", methods=["DELETE"])
def delete_showcase_label(name):
    try:
        existing_label = get_one_label(name=name)

        if not existing_label:
            return jsonify({"message": f"Label '{name}' cannot be deleted as it dont exist"})

        db.session.delete(existing_label)

        db.session.commit()

        return jsonify({
            "message": f"Label '{name}' deleted with success"
        })

    except SQLAlchemyError as e:
        db.session.rollback()

        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@seller_db_bp.route("/create-custom-showcase", methods=["POST"])
def create_custom_showcase():
    try:
        data = request.get_json()
        showcase_items = data.get("items", [])

        if not isinstance(showcase_items, list) or not showcase_items:
            return jsonify({"error": "`items` must be a non-empty list"}), 400

        created_models = []
        skipped_items = []

        for item in showcase_items:
            exists = get_one_showcase_label(item)

            if exists:
                skipped_items.append(item)
                continue

            new_cs = CustomShowcase(**item)
            db.session.add(new_cs)
            created_models.append(new_cs)

        db.session.commit()

        serialized_created = serialize_custom_showcase(created_models)

        created_len = len(created_models)

        if created_len == 0:
            return jsonify({
                "message": "Items sended already exists into the showcase",
            }), 400
        else:
            return jsonify({
                "message": "Processed custom-showcase items.",
                "created": serialized_created
            }), 201

    except SQLAlchemyError as e:
        # rollback on any SQL error
        db.session.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@seller_db_bp.route("/get-all-showcase-items", methods=["GET"])
def get_custom_showcase_items():
    try:
        custom_showcase_items = get_all_showcase_items()

        if not custom_showcase_items:
            return jsonify({"message": "No showcase items found!"}), 404

        serialized_showcase_items = serialize_custom_showcase(custom_showcase_items)

        return jsonify(serialized_showcase_items)

    except SQLAlchemyError as e:

        db.session.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@seller_db_bp.route("/get-seller-showcase-items/<string:id_seller>", methods=["GET"])
def get_seller_showcase_items(id_seller):
    try: 
        labels = get_all_labels(id_seller)
        
        serialized_labels = serialize_label(labels)
        
        items_by_label = {}
            
        for label in serialized_labels:
            seller_showcase_products_sql = text("""
                SELECT DISTINCT cs.`order`, cs.name as label, p.* FROM custom_showcase cs
                    JOIN product p ON cs.cod_product = p.cod_product
                    JOIN label l ON l.id_seller = :id_seller
                    WHERE cs.name = :label
                    ORDER BY cs.`order`                     
            """)
            
            label_name = label.get("name")

            result = db.session.execute(
                seller_showcase_products_sql,
                {
                    "label": f"{label_name}",
                    "id_seller": f"{id_seller}"
                }
            )
            
            if not result:
                return jsonify({"message": "No showcase items found!"}), 404
            
            serialized_showcase_items = serialize_seller_showcase_items(result)
            
            for item in serialized_showcase_items:
                items_by_label.setdefault(label_name, []).append(item)
            
        return jsonify(items_by_label)

    except SQLAlchemyError as e:

        db.session.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    
    
@seller_db_bp.route("/update-showcase-items/<string:id_seller>/<string:label>", methods=["PUT"])
def update_showcase_items(id_seller, label):
    try:
        data = request.get_json()
        
        if not data or 'items' not in data:
            return jsonify({"message": "No items data provided"}), 400
        
        existing_label = Label.query.filter_by(name=label, id_seller=id_seller).first()
        
        if not existing_label:
            return jsonify({"message": f"Label '{label}' does not exist for seller {id_seller}"}), 404
        
        items = data['items']
        
        current_items = CustomShowcase.query.filter_by(name=label).all()
        current_cod_products = {item.cod_product for item in current_items}
        
        new_items_data = {item['cod_product']: item for item in items}
        new_cod_products = set(new_items_data.keys())
        
        items_to_delete = current_cod_products - new_cod_products
        
        if items_to_delete:
            CustomShowcase.query.filter(
                CustomShowcase.name == label,
                CustomShowcase.cod_product.in_(items_to_delete)
            ).delete(synchronize_session=False)
            
        for item_data in items:
            cod_product = item_data['cod_product']
            new_order = item_data['order']
            
            existing_item = CustomShowcase.query.filter_by(
                cod_product=cod_product,
                name=label
            ).first()
            
            if existing_item:
                existing_item.order = new_order
            
            else:
                new_showcase_item = CustomShowcase(
                    cod_product=cod_product,
                    order=new_order,
                    name=label
                )
                db.session.add(new_showcase_item)

        db.session.commit()
        return jsonify({"message": f"Label '{label}' updated successfully"}), 200
        
    except SQLAlchemyError as e:
        
        db.session.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    
    
@seller_db_bp.route("/delete-showcase-item/<string:cod_product>", methods=["DELETE"])
def delete_showcase_item(cod_product):
    try:
        existing_showcase_item = CustomShowcase.query.filter_by(cod_product=cod_product).first()
        
        if not existing_showcase_item:
            return jsonify({"message": f"Showcase item with code '{cod_product}' no existent"})
        
        db.session.delete(existing_showcase_item)
        
        db.session.commit()
        
        return jsonify({
            "message": f"Showcase item with product code '{cod_product}' deleted successfully"
        })
    
    except SQLAlchemyError as e:
        db.session.rollback()
        
        return jsonify({"error": f"An error ocurred: {str(e)}"}), 500
        
        