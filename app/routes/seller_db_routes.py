from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import Seller, Label
from sqlalchemy.exc import SQLAlchemyError
from app.utils.functions import serialize_label

seller_db_bp = Blueprint("seller-db", __name__)


@seller_db_bp.route("/create", methods=["POST"])
def create_seller():
    data = request.get_json()

    try:
        with db.session.begin_nested():
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
        labels = Label.query.filter_by(id_seller=id_seller)

        if not labels:
            return jsonify({"message": "No labels found!"}), 404

        serialized_labels = serialize_label(labels)

        return jsonify(serialized_labels)

    except SQLAlchemyError as e:

        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@seller_db_bp.route("/get-one-label/<string:name>", methods=["GET"])
def get_one_showcase_label(name):
    print(name)
    
    try:
        label = Label.query.filter(Label.name.ilike(f"%{name}%")).first()

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
        
        existing_label = Label.query.filter_by(name=name).first()

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
        existing_label = Label.query.filter_by(name=name).first()

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
