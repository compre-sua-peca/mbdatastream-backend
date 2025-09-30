import math
from flask import Blueprint, jsonify, request
from sqlalchemy import or_
from app.models import Manufacturer, SellerManufacturer
from app.middleware.api_token import require_api_key
from app.extensions import db
from app.utils.functions import serialize_meta_pagination, serialize_manufacturer

manufacturer_bp = Blueprint("manufacturer", __name__)

@manufacturer_bp.route("/all", methods=["GET"])
@require_api_key
def get_manufacturers():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 16, type=int)

    pagination = Manufacturer.query.order_by(Manufacturer.order.asc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    manufacturers = [serialize_manufacturer(m) for m in pagination.items]

    meta = serialize_meta_pagination(
        pagination.total,
        pagination.pages,
        pagination.page,
        pagination.per_page
    )
    
    return jsonify({
        "manufacturers": manufacturers,
        "meta": meta
    }), 200


@manufacturer_bp.route("/get-all-by-seller/<int:id_seller>", methods=["GET"])
@require_api_key
def get_manufacturers_by_seller(id_seller):
    query = db.session.query(Manufacturer).join(
        SellerManufacturer,
        SellerManufacturer.id_manufacturer == Manufacturer.id
    ).filter(SellerManufacturer.id_seller == id_seller)
    
    #lukao mosapo

    manufacturers = [serialize_manufacturer(m) for m in query.all()]

    return jsonify({
        "manufacturers": manufacturers
    }), 200


@manufacturer_bp.route("/get-one-by-id/<int:id_manufacturer>", methods=["GET"])
@require_api_key
def get_one_manufacturer_by_id(id_manufacturer):
    manufacturer = Manufacturer.query.filter_by(id=id_manufacturer).first()

    if not manufacturer:
        return jsonify({"message": "Fabricante não encontrado"}), 404

    return jsonify(serialize_manufacturer(manufacturer)), 200


@manufacturer_bp.route("/create", methods=["POST"])
@require_api_key
def create_manufacturer():
    data = request.json

    if not data or not data.get("name"):
        return jsonify({"message": "Nome do fabricante é obrigatório"}), 400

    last_order = db.session.query(db.func.max(Manufacturer.order)).scalar() or 0
    
    new_manufacturer = Manufacturer(
        name=data["name"],
        description=data.get("description"),
        order=last_order + 1
    )
    
    print(data)

    db.session.add(new_manufacturer)
    db.session.commit()

    return jsonify({
        "message": "Fabricante criado com sucesso",
        "manufacturer": serialize_manufacturer(new_manufacturer)
    }), 201

@manufacturer_bp.route("/update/<int:id_manufacturer>", methods=["PUT"])
@require_api_key
def update_manufacturer(id_manufacturer):
    manufacturer = Manufacturer.query.filter_by(id=id_manufacturer).first()

    if not manufacturer:
        return jsonify({"message": "Fabricante não encontrado"}), 404

    data = request.json or {}

    manufacturer.name = data.get("name", manufacturer.name)
    manufacturer.description = data.get("description", manufacturer.description)
    manufacturer.order = data.get("order", manufacturer.order)

    db.session.commit()

    return jsonify({"message": "Fabricante atualizado com sucesso"}), 200

@manufacturer_bp.route("/delete/<int:id_manufacturer>", methods=["DELETE"])
@require_api_key
def delete_manufacturer(id_manufacturer):
    manufacturer = Manufacturer.query.filter_by(id=id_manufacturer).first()

    if not manufacturer:
        return jsonify({"message": "Fabricante não encontrado"}), 404

    try:
        SellerManufacturer.query.filter_by(id_manufacturer=id_manufacturer).delete()

        db.session.delete(manufacturer)
        db.session.commit()

        return jsonify({"message": "Fabricante deletado com sucesso"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Ocorreu um erro: {str(e)}"}), 500
    finally:
        db.session.close()
