import pandas as pd
from datetime import datetime
from app.models import Category, Product, Vehicle, Compatibility
from app.extensions import db


def extract_compat_to_list(compat_str):
    if not compat_str or pd.isna(compat_str):
        return []

    trimmed = compat_str.strip("[]")

    if not trimmed:
        return []

    items = trimmed.split(";")
    # Remove both outer quotes and whitespace
    vehicles = [item.strip().strip("'").strip() for item in items]

    return vehicles


def generate_category_hash(category_name):
    # Process category
    now = datetime.now()
    dt_string = now.strftime("%d%m%Y%H%M%S")
    
    # Simple hash function
    category_hash = f"{category_name}-{dt_string}"
    
    return category_hash


def process_excel(file_path):
    try:
        # Read the Excel file
        df = pd.read_excel(file_path)

        # Check if all required columns exist
        required_columns = [
            "COD_PRODUCT", "NAME_PRODUCT", "CATEGORY", "CROSS_REF",
            "GEAR_QUANTITY", "GEAR_DIMENSIONS", "BAR_CODE"
        ]

        # Convert column names to uppercase for case-insensitive matching
        df.columns = [col.upper() for col in df.columns]

        print(df.columns)

        # Check for missing columns
        missing_columns = [
            col for col in required_columns if col not in df.columns]

        if missing_columns:
            return {"error": f"Missing columns: {', '.join(missing_columns)}"}

        # Process the data
        results = {
            "processed": 0,
            "categories_created": 0,
            "products_created": 0,
            "vehicles_created": 0,
            "compatibilities_created": 0,
            "images_created": 0,
            "errors": []
        }

        products = []

        created_categories = {}
        created_vehicles = {}

        # Process each row
        for index, row in df.iterrows():
            try:
                """ Data Processing Logic """
                category_name = row["CATEGORY"]

                # Convert product to dictionary for JSON serialization
                product_dict = {
                    "cod_product": row["COD_PRODUCT"],
                    "name_product": row["NAME_PRODUCT"],
                    "bar_code": row["BAR_CODE"],
                    "gear_quantity": None if pd.isna(row["GEAR_QUANTITY"]) else row["GEAR_QUANTITY"],
                    "gear_dimensions": None if pd.isna(row["GEAR_DIMENSIONS"]) else row["GEAR_DIMENSIONS"],
                    "cross_reference": None if pd.isna(row["CROSS_REF"]) else row["CROSS_REF"],
                    # "image": row["IMAGE"]
                }

                # Store the values in string variables
                vehicles_names_string = row["COMPATIBILITY"]
                start_year_string = row["START_YEAR"]
                end_year_string = row["END_YEAR"]
                vehicle_type_string = row["TYPE_VEICULO"]

                # Extract the values from the strings to lists
                vehicles_names_list = extract_compat_to_list(
                    vehicles_names_string)
                start_year_list = extract_compat_to_list(start_year_string)
                end_year_list = extract_compat_to_list(end_year_string)
                vehicle_type_list = extract_compat_to_list(vehicle_type_string)

                res_vehicles_list = []
                compatibility_list = []

                compat_qtd = len(vehicles_names_list)

                for range_qtd in range(compat_qtd):
                    vehicle = {
                        "vehicle_name": vehicles_names_list[range_qtd],
                        "start_year": start_year_list[range_qtd],
                        "end_year": end_year_list[range_qtd] if end_year_list[range_qtd] != "Desconhecido" and end_year_list[range_qtd] != "Desconhecido." else None,
                        "type_vehicle": vehicle_type_list[range_qtd]
                    }

                    compatibility_dict = {
                        "cod_product": product_dict["cod_product"],
                        "vehicles": vehicles_names_list[range_qtd]
                    }

                    res_vehicles_list.append(vehicle)
                    compatibility_list.append(compatibility_dict)

                """ Database Insertion Logic """
                # Create the categories
                if category_name in created_categories:
                    category_hash = created_categories[category_name]
                else:
                    existing_category = Category.query.filter_by(name_category=category_name).first()
                    if existing_category:
                        category_hash = existing_category.hash_category
                    else:
                        category_hash = generate_category_hash(category_name)
                        category = Category(
                            hash_category=category_hash,
                            name_category=category_name
                        )
                        db.session.add(category)
                        db.session.flush()
                        results["categories_created"] += 1
                    created_categories[category_name] = category_hash

                # Create product object (without adding to database)
                product = Product(**product_dict, hash_category=category_hash)

                with db.session.no_autoflush:
                    existing_product = Product.query.filter_by(
                        cod_product=product.cod_product).first()

                if not existing_product:
                    db.session.add(product)
                    results["products_created"] += 1

                for vehicle_dict in res_vehicles_list:
                    if not vehicle_dict:
                        continue

                    vehicle_name = vehicle_dict["vehicle_name"]
                    vehicle = Vehicle.query.get(vehicle_name)

                    if not vehicle:
                        vehicle = Vehicle(
                            vehicle_name=vehicle_dict["vehicle_name"].strip(),
                            start_year=vehicle_dict["start_year"].strip(),
                            end_year=vehicle_dict["end_year"].strip() if vehicle_dict["end_year"] else None,
                            vehicle_type=vehicle_dict["type_vehicle"].strip()
                        )

                        db.session.add(vehicle)
                        results["vehicles_created"] += 1

                    created_vehicles[vehicle_name] = True

                    compatibility = Compatibility(
                        cod_product=product.cod_product,  # Use attribute access for the product object
                        vehicle_name=vehicle_name  # Use the extracted vehicle_name
                    )
                    
                    existing_compat = Compatibility.query.filter_by(cod_product=product.cod_product, vehicle_name=vehicle_name).first()
                    
                    if not existing_compat:
                        db.session.add(compatibility)
                        
                        results["compatibilities_created"] += 1

                    db.session.commit()

            except Exception as e:
                db.session.rollback()
                results["errors"].append(f"Error on row {index + 2}: {str(e)}")

        return {
            "products": products,
            "stats": results
        }

    except Exception as e:
        return {"error": str(e)}
