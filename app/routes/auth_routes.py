from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.extensions import db
from app.models import User

auth_bp = Blueprint("authentication", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
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
    db.session.commit()

    return jsonify({"message": "User registered successfully!"}), 201


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
