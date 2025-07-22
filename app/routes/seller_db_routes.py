from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import Seller, User_seller, User
from sqlalchemy.exc import SQLAlchemyError


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


@seller_db_bp.route("/user", methods=["GET"])
def get_user_by_seller_id():
    seller_id = request.args.get("id_seller", type=int)
    try:
        users = User.query.join(User_seller, User.id == User_seller.id_user).filter(
            User_seller.id_seller == seller_id).all()
        data = [
            {
                "id": user.id,
                "email": user.email
            }
            for user in users
        ]
        if not users:
            return jsonify({"error": "Nenhum usuário encontrado!"}), 400
        else:
            return jsonify(data), 200
    except Exception as e:
        return jsonify({"Erro": f"{e}"}), 400
