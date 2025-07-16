import math
from flask import Blueprint, jsonify, request
from sqlalchemy import text, or_
from app.middleware.api_token import require_api_key
from app.models import Product, Images
from app.extensions import db
from app.services.product_service import process_excel
import tempfile
import os
from app.dal.S3_client import S3ClientSingleton
from app.utils.functions import is_image_file, extract_existing_product_codes, serialize_product, serialize_meta_pagination


product_bp = Blueprint("products", __name__)


@product_bp.route("/all", methods=["GET"])
@require_api_key
def get_products():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 16, type=int)

    pagination = Product.query.paginate(
        page=page, per_page=per_page, error_out=False)

    products = serialize_product(pagination.items)

    meta = serialize_meta_pagination(
        pagination.total,
        pagination.pages,
        pagination.page,
        pagination.per_page
    )

    return jsonify({
        "products": products,
        "meta": meta
    }), 200

@product_bp.route("/get-all-by-seller/<string:id_seller>", methods=["GET"])
@require_api_key
def get_products_by_seller(id_seller):
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 16, type=int)
    is_manufactured_str = request.args.get("is_manufactured")

    is_manufactured = None
    if is_manufactured_str is not None:
        is_manufactured = is_manufactured_str.lower() == "true"

    pagination = None

    if is_manufactured is None:
        pagination = Product.query.filter(
            Product.id_seller == id_seller
        ).paginate(page=page, per_page=per_page, error_out=False)

    else:
        pagination = Product.query.filter(
            Product.is_manufactured == is_manufactured,
            Product.id_seller == id_seller
        ).paginate(page=page, per_page=per_page, error_out=False)

    filtered_products = serialize_product(pagination.items)

    meta = serialize_meta_pagination(
        pagination.total,
        pagination.pages,
        pagination.page,
        pagination.per_page
    )

    return jsonify({
        "products": filtered_products,
        "meta": meta
    }), 200
    

@product_bp.route("/category/<string:hash_category>", methods=["GET"])
@require_api_key
def get_products_by_category(hash_category):
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 16, type=int)
    id_seller = request.args.get("id_seller", type=int)
    is_manufactured_str = request.args.get("is_manufactured")

    is_manufactured = None
    if is_manufactured_str is not None:
        is_manufactured = is_manufactured_str.lower() == "true"

    transformed_hash_category = hash_category.replace("|", "/")

    pagination = None

    print(id_seller)

    if not hash_category:
        return jsonify({"message": "Nenhuma categoria fornecida"}), 400

    if is_manufactured is None:
        pagination = Product.query.filter_by(
            hash_category=transformed_hash_category,
            id_seller=id_seller
        ).paginate(
            page=page, per_page=per_page, error_out=False
        )

    else:
        pagination = Product.query.filter(
            Product.hash_category == transformed_hash_category,
            Product.is_manufactured == is_manufactured,
            Product.id_seller == id_seller
        ).paginate(
            page=page, per_page=per_page, error_out=False
        )

    products = serialize_product(pagination.items)

    print(products)

    meta = serialize_meta_pagination(
        pagination.total,
        pagination.pages,
        pagination.page,
        pagination.per_page
    )

    return jsonify({
        "products": products,
        "meta": meta
    }), 200


@product_bp.route("/search/<string:search_term>", methods=["GET"])
@require_api_key
def search_product(search_term):
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 16, type=int)
    is_manufactured_str = request.args.get("is_manufactured")
    id_seller = request.args.get("id_seller")

    is_manufactured = None
    if is_manufactured_str is not None:
        is_manufactured = is_manufactured_str.lower() == "true"

    transformed_search_term = search_term.replace("|", "/")

    if not search_term:
        return jsonify({"message": "Nenhum termo de busca fornecido"}), 400

    pagination = None

    if is_manufactured is None:
        pagination = Product.query.filter(
            or_(
                Product.cod_product.ilike(f"%{transformed_search_term}%") |
                Product.name_product.ilike(f"%{transformed_search_term}%") |
                Product.cross_reference.ilike(f"%{transformed_search_term}%") |
                Product.bar_code.ilike(f"%{transformed_search_term}%")
            ),
            Product.id_seller == id_seller
        ).paginate(page=page, per_page=per_page, error_out=False)

    else:
        pagination = Product.query.filter(
            or_(
                Product.cod_product.ilike(f"%{transformed_search_term}%"),
                Product.name_product.ilike(f"%{transformed_search_term}%"),
                Product.cross_reference.ilike(f"%{transformed_search_term}%"),
                Product.bar_code.ilike(f"%{transformed_search_term}%"),
            ),
            Product.is_manufactured == is_manufactured,
            Product.id_seller == id_seller
        ).paginate(page=page, per_page=per_page, error_out=False)

    filtered_products = serialize_product(pagination.items)

    meta = serialize_meta_pagination(
        pagination.total,
        pagination.pages,
        pagination.page,
        pagination.per_page
    )

    return jsonify({
        "products": filtered_products,
        "meta": meta
    }), 200


@product_bp.route("/compatibility/<string:vehicle_name>", methods=["GET"])
@require_api_key
def get_by_compatibility(vehicle_name):
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 16, type=int)
    id_seller = request.args.get("id_seller", type=int)
    offset = (page - 1) * per_page

    if not vehicle_name:
        return jsonify({"message": "Nenhuma compatibilidade informada"}), 400

    upper_vehicle_name = vehicle_name.upper()

    # First get the list of product IDs that match the compatibility
    product_ids_sql = text("""
        SELECT DISTINCT p.cod_product
        FROM product p
        JOIN compatibility c ON p.cod_product = c.cod_product
        JOIN vehicle v ON c.vehicle_name = v.vehicle_name
        WHERE v.vehicle_name LIKE :vehicle_pattern AND p.id_seller = :id_seller
        LIMIT :limit OFFSET :offset
    """)

    product_ids_result = db.session.execute(
        product_ids_sql,
        {
            "vehicle_pattern": f"%{upper_vehicle_name}%",
            "id_seller": id_seller,
            "limit": per_page,
            "offset": offset
        }
    )

    product_ids = [row[0] for row in product_ids_result]

    # If no products found, return empty result
    if not product_ids:
        # Get total for pagination
        count_sql = text("""
            SELECT COUNT(DISTINCT p.cod_product) as total
            FROM product p
            JOIN compatibility c ON p.cod_product = c.cod_product
            JOIN vehicle v ON c.vehicle_name = v.vehicle_name
            WHERE v.vehicle_name LIKE :vehicle_pattern
        """)

        count_result = db.session.execute(
            count_sql, {"vehicle_pattern": f"%{upper_vehicle_name}%"}).first()
        total = count_result.total

        print(total)

        # Calculate pagination metadata
        total_pages = math.ceil(total / per_page)

        meta = serialize_meta_pagination(
            total,
            total_pages,
            page,
            per_page
        )

        return jsonify({
            "products": [],
            "meta": meta
        }), 200

    # Then get full details for these products, including all images
    details_sql = text("""
        SELECT 
            p.*,
            ct.hash_category,
            ct.name_category,
            img.url,
            img.cod_product AS image_cod_product,
            img.id_image
        FROM product p
        JOIN category ct ON ct.hash_category = p.hash_category
        LEFT JOIN images img ON p.cod_product = img.cod_product
        WHERE p.cod_product IN :product_ids
    """)

    details_result = db.session.execute(
        details_sql,
        {
            "product_ids": tuple(product_ids)
        }
    )

    # Organize the results by product
    products_dict = {}
    for row in details_result:
        row_dict = row._asdict()
        product_id = row_dict['cod_product']

        if product_id not in products_dict:
            # Initialize product data
            products_dict[product_id] = {
                key: row_dict[key] for key in row_dict
                if key not in ('url', 'id_image')
            }
            products_dict[product_id]['images'] = []

        # Add image URL if available
        if row_dict['url']:
            products_dict[product_id]['images'].append(row_dict['url'])

    # Convert dictionary to list
    products = list(products_dict.values())

    # Get total for pagination
    count_sql = text("""
        SELECT COUNT(DISTINCT p.cod_product) as total
        FROM product p
        JOIN compatibility c ON p.cod_product = c.cod_product
        JOIN vehicle v ON c.vehicle_name = v.vehicle_name
        WHERE v.vehicle_name LIKE :vehicle_pattern AND p.id_seller = :id_seller
    """)

    count_result = db.session.execute(
        count_sql, {"vehicle_pattern": f"%{upper_vehicle_name}%", "id_seller": id_seller}).first()
    total = count_result.total

    # Calculate pagination metadata
    total_pages = math.ceil(total / per_page)

    meta = serialize_meta_pagination(
        total,
        total_pages,
        page,
        per_page
    )

    return jsonify({
        "products": products,
        "meta": meta
    }), 200


@product_bp.route("/compatibility-all/<string:vehicle_name>", methods=["GET"])
@require_api_key
def get_all_by_compatibility(vehicle_name):
    if not vehicle_name:
        return jsonify({"message": "Nenhuma compatibilidade informada"}), 400

    upper_vehicle_name = vehicle_name.upper()

    id_seller = request.args.get("id_seller", type=int)

    # First get the list of product IDs that match the compatibility
    product_ids_sql = text("""
        SELECT DISTINCT p.cod_product
        FROM product p
        JOIN compatibility c ON p.cod_product = c.cod_product
        JOIN vehicle v ON c.vehicle_name = v.vehicle_name
        WHERE v.vehicle_name LIKE :vehicle_pattern AND p.id_seller = :id_seller
    """)

    product_ids_result = db.session.execute(
        product_ids_sql,
        {
            "vehicle_pattern": f"%{upper_vehicle_name}%",
            "id_seller": id_seller
        }
    )

    product_ids = [row[0] for row in product_ids_result]

    # If no products found, return empty result
    if not product_ids:
        return jsonify({
            "products": []
        }), 200

    # Then get full details for these products, including all images
    details_sql = text("""
        SELECT 
            p.*,
            ct.name_category AS category,
            img.url,
            img.cod_product AS image_cod_product,
            img.id_image
        FROM product p
        JOIN category ct ON ct.hash_category = p.hash_category
        LEFT JOIN images img ON p.cod_product = img.cod_product
        WHERE p.cod_product IN :product_ids
    """)

    details_result = db.session.execute(
        details_sql,
        {
            "product_ids": tuple(product_ids)
        }
    )

    # Organize the results by product
    products_dict = {}
    for row in details_result:
        row_dict = row._asdict()
        product_id = row_dict['cod_product']

        if product_id not in products_dict:
            # Initialize product data
            products_dict[product_id] = {
                key: row_dict[key] for key in row_dict
                if key not in ('url', 'id_image')
            }
            products_dict[product_id]['images'] = []

        # Add image URL if available
        if row_dict['url']:
            products_dict[product_id]['images'].append(row_dict['url'])

    # Convert dictionary to list
    products_list = list(products_dict.values())

    # products = serialize_product(products_list)

    # Get total for pagination
    count_sql = text("""
        SELECT COUNT(DISTINCT p.cod_product) as total
        FROM product p
        JOIN compatibility c ON p.cod_product = c.cod_product
        JOIN vehicle v ON c.vehicle_name = v.vehicle_name
        WHERE v.vehicle_name LIKE :vehicle_pattern AND p.id_seller = :id_seller
    """)

    count_result = db.session.execute(
        count_sql, {"vehicle_pattern": f"%{upper_vehicle_name}%", "id_seller": id_seller}).first()

    total = count_result.total

    return jsonify({
        "products": products_list,
        "total": total
    }), 200


@product_bp.route("/", methods=["POST"])
@require_api_key
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
@require_api_key
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
@require_api_key
def get_product(cod_product):
    product = Product.query.filter_by(cod_product=cod_product).first()

    if not product:
        return jsonify({"message": "Produto não encontrado"}), 404

    category_name = product.category.name_category if product.category else None

    image_urls = [image.url for image in product.images]

    compatibility = [{"vehicle_name": comp.vehicle_name}
                     for comp in product.compatibilities]

    data = {
        "cod_product": product.cod_product,
        "name_product": product.name_product,
        "description": product.description,
        "is_active": product.is_active,
        "is_manufactured": product.is_manufactured,
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
@require_api_key
def update_product(cod_product):
    product = Product.query.filter_by(cod_product=cod_product).first()

    if not product:
        return jsonify({"message": "Produto não encontrado"}), 404

    data = request.json()

    product.name_product = data.get("name_product", product.name_product)
    product.bar_code = data.get("bar_code", product.bar_code)
    product.gear_quantity = data.get("gear_quantity", product.gear_quantity)
    product.gear_dimensions = data.get(
        "gear_dimensions", product.gear_dimensions)
    product.cross_reference = data.get(
        "cross_reference", product.cross_reference)
    product.hash_category = data.get("hash_category", product.hash_category)

    db.session.commit()

    return jsonify({"message": "Produto atualizado com sucesso"}), 200


@product_bp.route("/upload-product-images-by-folder", methods=["POST"])
@require_api_key
def upload_product_images_by_folder():
    s3_client = S3ClientSingleton()

    BUCKET_NAME = "mb-datastream"
    FOLDER = os.path.join("app", "uploads")

    product_codes = {product.cod_product for product in db.session.query(
        Product.cod_product).all()}
    image_codes = {image.cod_product for image in db.session.query(
        Images.cod_product).all()}

    non_existing_prod_codes = product_codes.difference(image_codes)

    # print(non_existing_prod_codes)

    # count = 0
    uploaded_files = []

    for filename in os.listdir(FOLDER):
        file_path = os.path.join(FOLDER, filename)

        filename_no_ext, _ = os.path.splitext(filename)

        if filename_no_ext in non_existing_prod_codes and is_image_file(filename):

            next_num = extract_existing_product_codes()

            new_cod_product = f"{filename_no_ext}-{next_num}"

            object_name = filename

            response = s3_client.upload_image_from_folder(
                file_path, BUCKET_NAME, new_cod_product
            )

            # print(response)

            image = {
                "cod_product": filename_no_ext,
                "id_image": new_cod_product,
                "url": f"https://{BUCKET_NAME}.s3.amazonaws.com/{object_name}"
            }

            new_image = Images(**image)

            if response:
                db.session.add(new_image)
                db.session.commit()

                uploaded_files.append(image)

                # count += 1
            else:
                print(f"Failed to upload {filename}")

            """ Return early after uploading 2 images
            if count == 2:
                return jsonify({"message": "Imagens enviadas com sucesso", "files": uploaded_files}), 201
            """

    # Ensure response even if fewer than 2 images were uploaded
    return jsonify({"message": "Upload process completed", "files": uploaded_files}), 201


@product_bp.route("/upload-product-images-by-s3", methods=["POST"])
@require_api_key
def upload_product_images_by_s3():
    s3_client = S3ClientSingleton()

    BUCKET_NAME = "mb-datastream"
    FOLDER = os.path.join("app", "uploads")

    product_codes = {product.cod_product for product in db.session.query(
        Product.cod_product).all()}
    image_codes = {image.cod_product for image in db.session.query(
        Images.cod_product).all()}

    non_existing_prod_codes = product_codes.difference(image_codes)

    # print(non_existing_prod_codes)

    # count = 0
    uploaded_files = []

    for filename in os.listdir(FOLDER):
        file_path = os.path.join(FOLDER, filename)

        filename_no_ext, _ = os.path.splitext(filename)

        if filename_no_ext in non_existing_prod_codes and is_image_file(filename):

            next_num = extract_existing_product_codes()

            new_cod_product = f"{filename_no_ext}-{next_num}"

            object_name = filename

            response = s3_client.upload_image_from_folder(
                file_path, BUCKET_NAME, new_cod_product
            )

            # print(response)

            image = {
                "cod_product": filename_no_ext,
                "id_image": new_cod_product,
                "url": f"https://{BUCKET_NAME}.s3.amazonaws.com/{object_name}"
            }

            new_image = Images(**image)

            if response:
                db.session.add(new_image)
                db.session.commit()

                uploaded_files.append(image)

                # count += 1
            else:
                print(f"Failed to upload {filename}")

            """ Return early after uploading 2 images
            if count == 2:
                return jsonify({"message": "Imagens enviadas com sucesso", "files": uploaded_files}), 201
            """

    # Ensure response even if fewer than 2 images were uploaded
    return jsonify({"message": "Upload process completed", "files": uploaded_files}), 201


@product_bp.route("/<string:cod_product>", methods=["DELETE"])
@require_api_key
def delete_product(cod_product):
    product = Product.query.filter_by(cod_product=cod_product).first()

    if not product:
        return jsonify({"message": "Produto não encontrado"}), 400

    try:
        # Delete all related Images
        for image in product.images:
            db.session.delete(image)

        # Delete all related Compatibility records
        for comp in product.compatibilities:
            db.session.delete(comp)

        # Delete the product itself
        db.session.delete(product)

        # Commit all deletions
        db.session.commit()

    except Exception as e:
        db.session.rollback()

        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@product_bp.route("/seller/<int:id_seller>", methods=["DELETE"])
@require_api_key
def delete_products_by_seller(id_seller):
    # Search all products by seller
    products = Product.query.filter_by(id_seller=id_seller).all()

    if not products:
        return jsonify({"message": "Nenhum produto encontrado para este vendedor"}), 404

    try:
        deleted_count = 0

        for product in products:
            # Delete all linked images to the product
            for image in product.images:
                db.session.delete(image)
                
            # Delete all linked compatibilities of that product
            for comp in product.compatibilities:
                db.session.delete(comp)
                
            db.session.delete(product)
            deleted_count += 1
            
        db.session.commit()
        
        return (
            jsonify(
                {
                    "message": f"Deletados {deleted_count} produto(s) do vendedor {id_seller}"
                }
            )
        )

    except Exception as e:
        db.session.rollback()

        return (
            jsonify({"error": f"Ocorreu um erro ao deletar: {str(e)}"}),
            500
        )


@product_bp.route("/sync-images", methods=["PATCH"])
@require_api_key
def sync_images():
    s3_client = S3ClientSingleton()

    BUCKET_NAME = "mb-datastream"

    # Retrieve all images from S3
    online_images = s3_client.list_image_names(BUCKET_NAME)

    # Extract product codes from online images
    online_image_codes = {img.get("cod_prod")
                          for img in online_images if img.get("cod_prod")}

    # Query local images from the database and extract their product codes
    local_images = db.session.query(Images).all()
    local_image_codes = {img.cod_product for img in local_images}

    # Retrieve all valid product codes from the product table to avoid foreign key issues
    valid_products = db.session.query(Product.cod_product).all()
    valid_product_codes = {prod[0] for prod in valid_products}

    # Determine missing codes (images present online but not in the local DB)
    missing_codes = (online_image_codes -
                     local_image_codes) & valid_product_codes

    synced_images = []

    # total_num = len(missing_codes)
    # percentage = 0

    for image in online_images:
        # Check if this image is missing locally by its product code
        if image.get("cod_prod") in missing_codes:
            new_image = Images(
                cod_product=image.get("cod_prod"),
                id_image=image.get("name"),
                url=image.get("url", "")
            )

            db.session.add(new_image)
            synced_images.append(new_image)
            # percentage += 1

            # print(f"{percentage} | {total_num}")

    # Commit once after processing all images
    db.session.commit()

    if not synced_images:
        return jsonify({
            "message": "Nenhuma imagem para ser inserida",
            "s3-images": list(online_image_codes)
        })

    return jsonify({
        "message": "Imagens sincronizadas com sucesso!"
    })
