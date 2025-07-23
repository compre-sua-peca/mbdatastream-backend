import asyncio

from flask import json
from app.models import Images
from app.extensions import db

def is_image_file(filename):
    valid_extensions = ('.png', '.jpg', '.jpeg', '.webp')

    return filename.lower().endswith(valid_extensions)


def extract_existing_product_codes():
    existing_images = db.session.query(Images.cod_product).filter(
        Images.cod_product.like("f{filename_no_ext}%")
    ).all()

    existing_codes = {img.cod_product for img in existing_images}

    if existing_codes:
        numbers = [int(code.split("+")[-1])
                   for code in existing_codes if "-" in code]
        next_num = max(numbers) + 1 if numbers else 1

        return next_num
    else:
        next_num = 1

        return next_num


""" ----------------------------- Function to handle json from the database ------------------------------ """


def serialize_products(products):
    result = []

    for product in products:
        # Get related category name if available
        category_name = product.category.name_category if product.category else None

        # Get list of image URLs
        image_urls = [image.url for image in product.images]

        # Get list of vehicles this product is compatible with
        compatibility = []
        for comp in product.compatibilities:
            vehicle = comp.vehicle

            # Get vehicle brand using the existing relationship
            brand_name = None
            if vehicle:
                # Use the relationship established by the ORM
                vehicle_brand = vehicle.vehicle_brand if hasattr(
                    vehicle, 'vehicle_brand') else None
                brand_name = vehicle_brand.brand_name if vehicle_brand else None

            vehicle_data = {
                "vehicle_name": comp.vehicle_name,
                "vehicle_type": vehicle.vehicle_type if vehicle else None,
                "start_year": vehicle.start_year if vehicle else None,
                "end_year": vehicle.end_year if vehicle else None,
                "brand": brand_name
            }
            compatibility.append(vehicle_data)

        result.append({
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
        })

    return result


def serialize_vehicle(vehicles):
    result = []

    for vehicle in vehicles:
        result.append({
            "vehicle_name": vehicle.vehicle_name,
            "vehicle_type": vehicle.vehicle_type,
            "start_year": vehicle.start_year,
            "end_year": vehicle.end_year,
            "hash_brand": vehicle.hash_brand
        })

    return result


def serialize_brand(brands):
    result = []

    for brand in brands:
        result.append({
            "hash_brand": brand.hash_brand,
            "brand_name": brand.brand_name,
            "brand_image": brand.brand_image
        })

    return result


def serialize_category(categories):
    result = []

    for category in categories:
        result.append({
            "hash_category": category.hash_category,
            "name_category": category.name_category
        })

    return result


def serialize_label(labels):
    result = []
    
    for label in labels:
        result.append({
            "name": label.name
        })
        
    return result


def serialize_custom_showcase(custom_showcase):
    result = []
    
    for item in custom_showcase:
        result.append({
            "cod_product": item.cod_product,
            "order": item.order,
            "name": item.name
        })
        
    return result


def serialize_vehicle_product_count(vehicles):
    result = []

    for vehicle, product_count in vehicles:
        result.append({
            "vehicle_name": vehicle.vehicle_name,
            "start_year": vehicle.start_year,
            "end_year": vehicle.end_year,
            "vehicle_type": vehicle.vehicle_type,
            "product_count": product_count
        })

    return result


def serialize_seller(sellers):
    result = []
    
    for seller in sellers:
        result.append({
            "id": seller.id,
            "name": seller.name,
            "cnpj": seller.cnpj
        })
    
    return result


def serialize_one_seller(seller):
    result = {
        "id": seller.id,
        "name": seller.name,
        "cnpj": seller.cnpj
    }
    
    return result


def serialize_seller_showcase_items(seller_showcase_items):
    result = []
    
    for item in seller_showcase_items:
        # Get the raw images as string (JSON)
        raw_images = item.images
        
        # Parse the strings
        if isinstance(raw_images, str):
            try:
                parsed = json.loads(raw_images)
                
                images_list = parsed if isinstance(parsed, list) else []
                
            except json.JSONDecodeError:
                images_list = []
                
        else:
            images_list = raw_images
            
        images = []
        
        # Normalize each entry to a dict with the url
        for img in images_list:
            if isinstance(img, dict) and "url" in img:
                images.append(img["url"])
                
            elif isinstance(img, str):
                images.append(img)
                
            else:
                continue
        
        result.append({
            "order": item.order,
            "label": item.label,
            "cod_product": item.cod_product,
            "name_product": item.name_product,
            "bar_code": item.bar_code,
            "gear_quantity": item.gear_quantity,
            "cross_reference": item.cross_reference,
            "hash_category": item.hash_category,
            "gear_dimensions": item.gear_dimensions,
            "description": item.description,
            "is_active": item.is_active,
            "is_manufactured": item.is_manufactured,
            "images": images
        })
        
    return result


def serialize_meta_pagination(total, pages, page, per_page):

    return {
        "total_items": total,
        "total_pages": pages,
        "current_page": page,
        "per_page": per_page
    }
