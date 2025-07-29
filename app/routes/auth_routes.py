from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.extensions import db
from app.middleware.api_token import require_api_key
from app.models import User, SellerUsers
from app.utils.functions import serialize_users


auth_bp = Blueprint("authentication", __name__)


@auth_bp.route("/register/<string:id_seller>", methods=["POST"])
def register(id_seller):
    data = request.get_json()

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    cnpj = data.get("cnpj")
    whatsapp = data.get("whatsapp")

    if not username or not email or not password:
        return jsonify({"message": "Todos os campos são obrigatórios"}), 400

    existing_user = User.query.filter_by(email=email).first()

    if existing_user:
        return jsonify({"message": "O email já está em uso", "user": existing_user.serialize()}), 400

    # Hash the user password before storing
    new_user = User(
        email=email,
        username=username,
        password=generate_password_hash(password),
        cnpj=cnpj,
        whatsapp=whatsapp
    )
    
    db.session.add(new_user)
    db.session.flush()
    
    user_seller = SellerUsers(
        id_seller=id_seller,
        id_user=new_user.id
    )

    db.session.add(user_seller)
    db.session.commit()

    return jsonify({"message": "Usuário registrado com sucesso!"}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password, password):
        return jsonify({"message": "Credenciais inválidas"}), 401

    # Create a enw JWT token with the user's id as identity
    access_token = create_access_token(identity=str(user.id))

    logged_user = {
        "username": user.username,
        "email": user.email
    }

    return jsonify({
        "message": "Login bem sucediddo",
        "access_token": access_token,
        "user": logged_user
    }), 200


@auth_bp.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    return jsonify({
        "message": f"Bem vindo {user.username}",
    })
    
    
@auth_bp.route("/get-seller-users/<string:id_seller>", methods=["GET"])
@require_api_key
def get_seller_users(id_seller):    
    if not id_seller:
        return jsonify({"error": "Query parameter 'id_seller' (integer) is required."}), 400
    
    user_rows = (
        db.session.query(User)
            .join(SellerUsers, SellerUsers.id_user == User.id)
            .filter(SellerUsers.id_seller == id_seller)
            .all()
    )
    
    serialized_seller_users = serialize_users(user_rows)
    
    return jsonify(serialized_seller_users) 