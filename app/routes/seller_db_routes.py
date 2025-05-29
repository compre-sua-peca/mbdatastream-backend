from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import Seller
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
            
            