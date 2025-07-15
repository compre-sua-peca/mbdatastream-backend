from flask import Blueprint, request, jsonify
from sqlalchemy import text
from app.extensions import db
from app.middleware.api_token import require_api_key
from app.models import Seller, Label, CustomShowcase
from sqlalchemy.exc import SQLAlchemyError
from app.services.seller_db_service import get_all_db_sellers, get_one_db_seller, get_all_labels, get_all_showcase_items, get_one_db_seller_by_cnpj, get_one_db_seller_by_name, get_one_label, get_one_similar_label
from app.utils.functions import serialize_label, serialize_custom_showcase, serialize_seller_showcase_items, serialize_seller, serialize_one_seller


seller_db_bp = Blueprint("seller-db", __name__)


@seller_db_bp.route("/create", methods=["POST"])
@require_api_key
def create_seller():
    data = request.get_json()

    name = data.get("name")
    cnpj = data.get("cnpj")

    try:
        existing_seller = get_one_db_seller_by_name(name)

        if existing_seller:
            return jsonify({"message": f"O seller {name} já existe!"}), 400

        new_seller = Seller(
            name=name,
            cnpj=cnpj
        )

        db.session.add(new_seller)

        db.session.commit()

    except SQLAlchemyError as e:
        db.session.rollback()

        raise e

    return jsonify({"message": "Seller criado com sucesso!"}), 201


@seller_db_bp.route("/get-all", methods=["GET"])
@require_api_key
def get_all_sellers():
    try:
        sellers = get_all_db_sellers()

        if not sellers:
            return jsonify({"message": "No sellers found!"}), 404

        serialized_sellers = serialize_seller(sellers)

        return jsonify(serialized_sellers)

    except SQLAlchemyError as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@seller_db_bp.route("/get-one/<string:id>", methods=["GET"])
@require_api_key
def get_one_seller(id):
    try:
        seller = get_one_db_seller(id)

        if not seller:
            return jsonify({"message": "No seller found!"}), 404

        serialized_seller = serialize_one_seller(seller)

        return jsonify(serialized_seller)

    except SQLAlchemyError as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@seller_db_bp.route("/get-one-by-name/<string:name>", methods=["GET"])
@require_api_key
def get_one_seller_by_name(name):
    try:
        seller = get_one_db_seller_by_name(name)

        if not seller:
            return jsonify({"message": "No seller found!"}), 404

        serialized_seller = serialize_seller([seller])

        return jsonify(serialized_seller)

    except SQLAlchemyError as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@seller_db_bp.route("/get-one-by-cnpj/<string:name>", methods=["GET"])
@require_api_key
def get_one_seller_by_cnpj(cnpj):
    try:
        seller = get_one_db_seller_by_cnpj(cnpj)

        if not seller:
            return jsonify({"message": "No seller found!"}), 404

        serialized_seller = serialize_seller([seller])

        return jsonify(serialized_seller)

    except SQLAlchemyError as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@seller_db_bp.route("/update/<string:id>", methods=["PUT"])
@require_api_key
def update_seller(id):
    data = request.get_json()

    try:
        seller = get_one_db_seller(id)

        if not seller:
            return jsonify({"message": f"Seller with id {id} not found!"}), 404

        if "name" in data:
            seller.name = data["name"]
        if "cnpj" in data:
            seller.cnpj = data["cnpj"]

        db.session.commit()

        serialized_seller = serialize_one_seller(seller)

        return jsonify({
            "message": f"Seller com id {id} atualizado com sucesso!",
            "updated": serialized_seller
        }), 200

    except SQLAlchemyError as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@seller_db_bp.route("/delete/<string:id>", methods=["DELETE"])
@require_api_key
def delete_seller(id):
    try:
        seller = get_one_db_seller(id)

        if not seller:
            return jsonify({"message": f"Seller with id {id} not found!"}), 404

        serialized_seller = serialize_seller([seller])

        return jsonify(serialized_seller)

    except SQLAlchemyError as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@seller_db_bp.route("/create-label/<string:id_seller>", methods=["POST"])
@require_api_key
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
@require_api_key
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
@require_api_key
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
@require_api_key
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
@require_api_key
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
@require_api_key
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


@seller_db_bp.route("/create-label-custom-showcase/<string:id_seller>", methods=["POST"])
@require_api_key
def create_label_and_showcase(id_seller):
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    showcase_items = data.get("items", [])

    if not name:
        return jsonify({"error": "Campo 'name' é obrigatório!"}), 400

    # You probably want to check existence by both seller and name:
    existing_label = Label.query.filter_by(
        id_seller=id_seller, name=name).first()
    if existing_label:
        return jsonify({"message": "A vitrine já existe!"}), 400

    try:
        db.session.rollback()

        # All operations inside here are part of one transaction.
        with db.session.begin():
            # 1) create the label
            new_label = Label(id_seller=id_seller, name=name)
            db.session.add(new_label)
            db.session.flush()

            # 2) create each showcase item linked to that label
            created_showcase = []
            for item in showcase_items:
                cs = CustomShowcase(
                    name=name,
                    order=item.get("order", ""),
                    cod_product=item.get("cod_product", "")
                )
                db.session.add(cs)
                created_showcase.append(cs)
        # Exiting the `with` block commits automatically if no errors.

        # Serialize and return
        serialized_label = serialize_label([new_label])[0]
        serialized_showcase = serialize_custom_showcase(created_showcase)

        return jsonify({
            "message": f"Vitrine '{name}' criada com sucesso!",
            "created_label": serialized_label,
            "created_showcase": serialized_showcase
        }), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({
            "message": "Erro ao criar a vitrine.",
            "error": str(e)
        }), 500


@seller_db_bp.route("/get-all-custom-showcase-items", methods=["GET"])
@require_api_key
def get_custom_showcase_items():
    try:
        custom_showcase_items = get_all_showcase_items()

        if not custom_showcase_items:
            return jsonify({"message": "No showcase items found!"}), 404

        serialized_showcase_items = serialize_custom_showcase(
            custom_showcase_items)

        return jsonify(serialized_showcase_items)

    except SQLAlchemyError as e:

        db.session.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@seller_db_bp.route("/get-seller-custom-showcase-items/<string:id_seller>", methods=["GET"])
@require_api_key
def get_seller_showcase_items(id_seller):
    try:
        labels = get_all_labels(id_seller)

        serialized_labels = serialize_label(labels)

        items_by_label = {}

        for label in serialized_labels:
            seller_showcase_products_sql = text("""
                SELECT DISTINCT
                    cs.`order`,
                    cs.name            AS label,
                    p.*,
                    COALESCE(
                        (
                        SELECT JSON_ARRAYAGG(
                                JSON_OBJECT(
                                    'url', img.url
                                ))
                        FROM images img
                        WHERE img.cod_product = p.cod_product
                        ),
                        JSON_ARRAY()  /* empty array if no images */
                    ) AS images
                FROM custom_showcase cs
                JOIN label       l  ON l.id_seller    = :id_seller
                JOIN product     p  ON p.cod_product  = cs.cod_product
                WHERE cs.name = :label
                ORDER BY cs.`order`;         
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
    

@seller_db_bp.route("/get-seller-custom-showcase/<string:id_seller>/<string:label>", methods=["GET"])
@require_api_key
def get_seller_showcase_item(id_seller, label):
    try:
        seller_showcase_product_sql = text("""
            SELECT DISTINCT
                    cs.`order`,
                    cs.name            AS label,
                    p.*,
                    COALESCE(
                        (
                        SELECT JSON_ARRAYAGG(
                                JSON_OBJECT(
                                    'url', img.url
                                ))
                        FROM images img
                        WHERE img.cod_product = p.cod_product
                        ),
                        JSON_ARRAY()  /* empty array if no images */
                    ) AS images
                FROM custom_showcase cs
                JOIN label       l  ON l.id_seller    = :id_seller
                JOIN product     p  ON p.cod_product  = cs.cod_product
                WHERE cs.name = :label
                ORDER BY cs.`order`;                                    
        """)
        
        item_by_label = {}
    
        
        result = db.session.execute(
            seller_showcase_product_sql,
            {
                "label": f"{label}",
                "id_seller": f"{id_seller}"
            }
        )
        
        if not result:
            return jsonify({"message": "No showcase item found!"}), 404
        
        serialized_showcase_item = serialize_seller_showcase_items(result)
        
        for item in serialized_showcase_item:
            item_by_label.setdefault(label, []).append(item)
        
        return jsonify(item_by_label)
    
    except SQLAlchemyError as e:
        
        db.session.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@seller_db_bp.route("/update-custom-showcase-items/<string:id_seller>/<string:label>", methods=["PUT"])
@require_api_key
def update_showcase_items(id_seller, label):
    try:
        data = request.get_json()

        if not data or 'items' not in data:
            return jsonify({"message": "No items data provided"}), 400

        existing_label = Label.query.filter_by(
            name=label, id_seller=id_seller).first()

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
            
            # if existing_item:
            #     existing_item.order = new_order

            if not existing_item:
                new_showcase_item = CustomShowcase(
                    cod_product=cod_product,
                    order=new_order,
                    name=label
                )
                db.session.add(new_showcase_item)

            # else:
            #     new_showcase_item = CustomShowcase(
            #         cod_product=cod_product,
            #         order=new_order,
            #         name=label
            #     )
            #     db.session.add(new_showcase_item)

        db.session.commit()
        return jsonify({"message": f"Rótulo '{label}' atualizado com sucesso!"}), 200

    except SQLAlchemyError as e:

        db.session.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@seller_db_bp.route("/delete-custom-showcase/<string:label>", methods=["DELETE"])
@require_api_key
def delete_custom_showcase(label):
    try:
        existing_custom_showcase = Label.query.filter_by(
            name=label
        ).first()
        
        if not existing_custom_showcase:
            return jsonify({"message": f"Vitrine {label} não existe para ser deletada!"})
        
        CustomShowcase.query.filter_by(
            name=label
        ).delete()
        
        Label.query.filter_by(
            name=label
        ).delete()
        
        db.session.commit()
        
        return jsonify({"message": f"Vitrine de {label} deletada com sucesso!"}), 200
        
    except SQLAlchemyError as e:
        db.session.rollback()
        
        return jsonify({"error": f"An error ocurred: {str(e)}"}), 500
        

@seller_db_bp.route("/delete-custom-showcase-item/<string:cod_product>", methods=["DELETE"])
@require_api_key
def delete_showcase_item(cod_product):
    try:
        existing_showcase_item = CustomShowcase.query.filter_by(
            cod_product=cod_product).first()

        if not existing_showcase_item:
            return jsonify({"message": f"Showcase item with code '{cod_product}' no existent"})

        db.session.delete(existing_showcase_item)

        db.session.commit()

        return jsonify({
            "message": f"Item de vitrine com código '{cod_product}' deletado com sucesso!"
        })

    except SQLAlchemyError as e:
        db.session.rollback()

        return jsonify({"error": f"An error ocurred: {str(e)}"}), 500