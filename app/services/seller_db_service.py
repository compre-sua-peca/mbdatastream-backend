from app.models import CustomShowcase, Label, Seller

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