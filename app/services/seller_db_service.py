from flask import jsonify
from sqlalchemy import text
from app.models import CustomShowcase, Label, Seller
from app.extensions import db
from app.utils.functions import serialize_seller_showcase_items

""" Seller functions """

def get_all_db_sellers():
    sellers = Seller.query.all()
    
    return sellers


def get_one_db_seller(id):
    seller = Seller.query.filter_by(id=id).first()
    
    return seller


def get_one_db_seller_by_name(name):
    seller = Seller.query.filter_by(name=name).first()
    
    return seller


def get_one_db_seller_by_cnpj(cnpj):
    seller = Seller.query.filter_by(cnpj=cnpj).first()
    
    return seller


""" Labels functions """

def get_all_labels(id_seller):
    labels = Label.query.filter_by(id_seller=id_seller).all()
    
    return labels


def get_one_label(name):
    label = Label.query.filter_by(name=name).first()
    
    return label


def get_one_similar_label(name):
    label = Label.query.filter(Label.name.ilike(f"%{name}%")).first()
    
    return label
    
    
""" Showcase functions """

def get_all_showcase_items():
    showcase_items = CustomShowcase.query.all()
    
    return showcase_items


def get_one_showcase_item(item):
    item = CustomShowcase.query.filter_by(
        cod_product=item.get("cod_product"),
        name=item.get("name"),
        order=item.get("order")
    ).first()
    
    return item

def get_all_labeled_custom_showcases(serialized_labels, id_seller):
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
    
    return items_by_label