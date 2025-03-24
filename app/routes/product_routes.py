from flask import Blueprint, jsonify, request
from app.models import Product, Category, Images, Compatibility, Vehicle
from app.extensions import db
from app.utils.functions import process_excel
import tempfile
import os
from app.dal.S3_client import S3ClientSingleton
from app.utils.functions import is_image_file

product_bp = Blueprint("products", __name__)

@product_bp.route("/", methods=["GET"])
def get_products():
    products = Product.query.all()
    result = []
    
    for product in products:
        # Get related category name if available
        category_name = product.category.name_category if product.category else None
        
        # Get list of image URLs
        image_urls = [image.url for image in product.images]
        
        # Get list of vehicles this product is compatible with
        compatibility = [{"vehicle_name": comp.vehicle_name} for comp in product.compatibilities]
        
        result.append({
            "cod_product": product.cod_product,
            "name_product": product.name_product,
            "bar_code": product.bar_code,
            "gear_quantity": product.gear_quantity,
            "gear_dimensions": product.gear_dimensions,
            "cross_reference": product.cross_reference,
            "category": category_name,
            "images": image_urls,
            "compatibilities": compatibility
        })
    
    return jsonify(result), 200


@product_bp.route("/", methods=["POST"])
def create_product():
    data = request.json
    
    # Create the product instance
    new_product = Product(
        cod_product=data["cod_product"],
        name_product=data["name_product"],
        bar_code=data["bar_code"],
        gear_quantity=data["gear_quantity"],
        gear_dimensions=data["gear_dimensions"],
        cross_reference=data["cross_reference"],
        hash_category=data["hash_category"]
    )
    
    db.session.add(new_product)
    db.session.commit()
    
    return jsonify({"message": "Produto criado com sucesso"}), 201


@product_bp.route("/create-from-csv", methods=["POST"])
def create_products_from_csv():
    if 'file' not in request.files:
        return jsonify({"message": "Nenhum arquivo enviado"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"message": "Nenhum arquivo selecionado"}), 400
    
    if not file.filename.endswith('.xlsx'):
        return jsonify({"message": "Arquivo inválido"}), 400
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp:
        file.save(temp.name)
        temp_path = temp.name
    
    try:
        products = process_excel(temp_path)
        
        return jsonify({
            "message": "Produtos criados com sucesso", 
            "data": products
        }), 201
    finally:
        # Always ensure the temporary file is removed
        if os.path.exists(temp_path):
            os.remove(temp_path)

@product_bp.route("/<string:cod_product>", methods=["GET"])
def get_product(cod_product):
    product = Product.query.filter_by(cod_product=cod_product).first()
    
    if not product:
        return jsonify({"message": "Produto não encontrado"}), 404
    
    category_name = product.category.name_category if product.category else None
    
    image_urls = [image.url for image in product.images]
    
    compatibility = [{"vehicle_name": comp.vehicle_name} for comp in product.compatibilities]
    
    data = {
        "cod_product": product.cod_product,
        "name_product": product.name_product,
        "bar_code": product.bar_code,
        "gear_quantity": product.gear_quantity,
        "gear_dimensions": product.gear_dimensions,
        "cross_reference": product.cross_reference,
        "category": category_name,
        "images": image_urls,
        "compatibilities": compatibility
    }
    
    return jsonify(data), 200


@product_bp.route("/<string:cod_product>", methods=["PUT"])
def update_product(cod_product):
    product = Product.query.filter_by(cod_product=cod_product).first()
    
    if not product:
        return jsonify({"message": "Produto não encontrado"}), 404
    
    data = request.json()
    
    product.name_product = data.get("name_product", product.name_product)
    product.bar_code = data.get("bar_code", product.bar_code)
    product.gear_quantity = data.get("gear_quantity", product.gear_quantity)
    product.gear_dimensions = data.get("gear_dimensions", product.gear_dimensions)
    product.cross_reference = data.get("cross_reference", product.cross_reference)
    product.hash_category = data.get("hash_category", product.hash_category)
    
    db.session.commit()
    
    return jsonify({"message": "Produto atualizado com sucesso"}), 200


@product_bp.route("/upload-product-images", methods=["POST"])
def upload_product_images():
    s3_client = S3ClientSingleton()
    
    BUCKET_NAME = "mb-datastream"
    FOLDER = os.path.join("app", "uploads")
    
    product_codes = {product.cod_product for product in db.session.query(Product.cod_product).all()}
    
    count = 0
    uploaded_files = []
    
    for filename in os.listdir(FOLDER):
        file_path = os.path.join(FOLDER, filename)
        
        print(file_path)
        
        filename_no_ext, _ = os.path.splitext(filename)

        """"""
        if filename_no_ext in product_codes and is_image_file(filename):
            object_name = filename
            response = s3_client.upload_image_from_folder(file_path, BUCKET_NAME, object_name)
            
            print(response)
            
            image = {
                "cod_product": filename_no_ext,
                "url": f"https://{BUCKET_NAME}.s3.amazonaws.com/{object_name}"
            }
            
            new_image = Images(**image)            
            
            if response:                
                db.session.add(new_image)
                db.session.commit()
                
                uploaded_files.append(image)
                
                count += 1
            else:
                print(f"Failed to upload {filename}")

            # Return early after uploading 2 images
            if count == 2:
                return jsonify({"message": "Imagens enviadas com sucesso", "files": uploaded_files}), 201
        
    
    # Ensure response even if fewer than 2 images were uploaded
    return jsonify({"message": "Upload process completed", "files": uploaded_files}), 201


@product_bp.route("/<string:cod_product>", methods=["DELETE"])
def delete_product(cod_product):
    product = Product.query.filter_by(cod_product=cod_product).first()
    
    if not product:
        return jsonify({"message": "Produto não encontrado"}), 200