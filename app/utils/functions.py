import pandas as pd
import asyncio
from app.models import Category, Product, Vehicle, Compatibility, Images, VehicleBrand
from app.extensions import db
from sqlalchemy.future import select
from app.dal.encryptor import HashGenerator

""" --------------------------------- Functions to handle product, category, compatibility and vehicles insertions on the database --------------------------------- """
# Extract compatibilities from the compat column from Excel and tranform it in an array/list
def extract_compat_to_list(compat_str):
    if not compat_str or pd.isna(compat_str):
        return []

    trimmed = compat_str.strip("[]")
    if not trimmed:
        return []

    items = trimmed.split(";")
    vehicles = [item.strip().strip("'").strip() for item in items]
    return vehicles

# Asynchronous processing function to process the product insertion in batches after reading the Excel
async def _process_excel_async(file_path, batch_size):
    try:
        # Read the Excel file
        df = pd.read_excel(file_path)

        # Check if all required columns exist
        required_columns = [
            "COD_PRODUCT", "NAME_PRODUCT", "CATEGORY", "CROSS_REF",
            "GEAR_QUANTITY", "GEAR_DIMENSIONS", "BAR_CODE", "VEHICLE_BRAND"
        ]

        # Convert column names to uppercase
        df.columns = [col.upper() for col in df.columns]
        print(f"Found columns: {df.columns}")

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
            "brands_created": 0,
            "compatibilities_created": 0,
            "errors": []
        }

        # Process batches for better performance
        total_rows = len(df)
        batches = [df[i:i+batch_size]
                   for i in range(0, total_rows, batch_size)]
        
        print(batches)

        # Store created categories, brands and vehicles across batches
        created_categories = {}
        created_vehicles = {}
        created_brands = {}

        for batch_idx, batch_df in enumerate(batches):
            print(f"Processing batch {batch_idx+1}/{len(batches)}")

            # Process each batch with a new session
            await process_batch(
                batch_df,
                batch_idx,
                created_categories,
                created_vehicles,
                created_brands,
                results
            )

        return {
            "stats": results
        }

    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }

# Function to start the process of batches to insert into the database
async def process_batch(batch_df, batch_idx, created_categories, created_vehicles, created_brands, results):
    """Process a batch of rows with a single session"""
    # Process each row with its own session to prevent cascading failures
    for index, row in batch_df.iterrows():
        try:
            async with db.async_session() as session:
                async with session.begin():
                    await process_row(
                        index,
                        row,
                        session,
                        created_categories,
                        created_vehicles,
                        created_brands,
                        results
                    )

            results["processed"] += 1
        except Exception as e:
            results["errors"].append(
                f"Error on row {index + 2}: {str(e)}"
            )


# Function to check the existence of the data and then register each row on the database
async def process_row(index, row, session, created_categories, created_vehicles, created_brands, results):
    """Process a single row from the Excel file"""
    try:
        # Get category
        category_name = row["CATEGORY"]
        category_hash = await get_or_create_category(
            session,
            category_name,
            created_categories,
            results
        )
        
        cod_product = await get_or_create_product(session, row, category_hash, results)

        # Extract vehicle compatibility info
        vehicles_names_string = row.get("COMPATIBILITY", "")
        start_year_string = row.get("START_YEAR", "")
        end_year_string = row.get("END_YEAR", "")
        vehicle_type_string = row.get("TYPE_VEHICLE", "")
        vehicle_brands_string = row.get("VEHICLE_BRAND", "")

        # Extract the values from the strings to lists
        vehicles_names_list = extract_compat_to_list(vehicles_names_string)
        start_year_list = extract_compat_to_list(start_year_string)
        end_year_list = extract_compat_to_list(end_year_string)
        vehicle_type_list = extract_compat_to_list(vehicle_type_string)
        vehicle_brands_list = extract_compat_to_list(vehicle_brands_string)

        # Process vehicle compatibilities
        compat_qtd = len(vehicles_names_list)
        for i in range(compat_qtd):
            if (i >= len(start_year_list) or
                i >= len(end_year_list) or
                i >= len(vehicle_type_list) or
                i >= len(vehicle_brands_list)):
                continue

            vehicle_name = vehicles_names_list[i].strip()
            vehicle_brand = vehicle_brands_list[i].strip()

            # Skip empty vehicle names or brands
            if not vehicle_name or not vehicle_brand:
                continue

            # Create or get brand first
            brand_hash = await get_or_create_vehicle_brand(
                session,
                vehicle_brand,
                created_brands,
                results
            )

            # Create or get vehicle
            await get_or_create_vehicle(
                session,
                vehicle_name,
                start_year_list[i].strip(),
                end_year_list[i].strip() if end_year_list[i] not in [
                    "Desconhecido", "Desconhecido.", "/Desconhecido"] else None,
                vehicle_type_list[i].strip(),
                brand_hash,
                created_vehicles,
                results
            )

            # Create compatibility if needed
            await get_or_create_compatibility(
                session,
                cod_product,
                vehicle_name,
                results
            )

    except Exception as e:
        results["errors"].append(f"Error on row {index + 2}: {str(e)}")
        

async def get_or_create_vehicle_brand(session, brand_name, created_brands, results):
    """Get an existing vehicle brand or create a new one"""
    hash_generator = HashGenerator()
    
    if brand_name in created_brands:
        return created_brands[brand_name]
    
    # Check database
    stmt = select(VehicleBrand).where(VehicleBrand.brand_name == brand_name)
    result = await session.execute(stmt)
    existing_brand = result.scalars().first()
    
    treated_brand_name = brand_name.replace(" ", "")

    if existing_brand:
        brand_hash = existing_brand.hash_brand
    else:
        brand_hash = hash_generator.generate_hash(treated_brand_name)
        new_brand = VehicleBrand(
            hash_brand=brand_hash,
            brand_name=brand_name,
            brand_image=None  # Set default to None, can be updated later
        )
        session.add(new_brand)
        results["brands_created"] += 1

    created_brands[brand_name] = brand_hash
    return brand_hash


async def get_or_create_product(session, row, category_hash, results):
    name_product = row["NAME_PRODUCT"]
    
    name_check = name_product.split("-")[0].strip()
    is_manufactured = True
    
    if name_check == "ITEM DESCONTINUADO":
        name_product = name_product.split("-")[1].strip()
        is_manufactured = False
    
    # Create product dict
    product_dict = {
        "cod_product": row["COD_PRODUCT"],
        "name_product": name_product,
        "description": row["DESCRIPTION"],
        "is_manufactured": is_manufactured,
        "bar_code": row["BAR_CODE"],
        "gear_quantity": None if pd.isna(row["GEAR_QUANTITY"]) else row["GEAR_QUANTITY"],
        "gear_dimensions": None if pd.isna(row["GEAR_DIMENSIONS"]) else row["GEAR_DIMENSIONS"],
        "cross_reference": None if pd.isna(row["CROSS_REF"]) else row["CROSS_REF"],
        "hash_category": category_hash
    }

    # Check if product exists before adding
    sql_statement = select(Product).where(
        Product.cod_product == product_dict["cod_product"])
    result = await session.execute(sql_statement)
    existing_product = result.scalars().first()

    if not existing_product:
        product = Product(**product_dict)
        session.add(product)
        results["products_created"] += 1
        
    return product_dict["cod_product"]


async def get_or_create_category(session, category_name, created_categories, results):
    """Get an existing category or create a new one"""
    hash_generator = HashGenerator()
    
    # Check cache first
    if category_name in created_categories:
        return created_categories[category_name]

    # Check database
    stmt = select(Category).where(Category.name_category == category_name)
    result = await session.execute(stmt)
    existing_category = result.scalars().first()
    
    treated_category_name = category_name.replace(" ", "")

    if existing_category:
        category_hash = existing_category.hash_category
    else:
        category_hash = hash_generator.generate_hash(treated_category_name)
        new_category = Category(
            hash_category=category_hash,
            name_category=category_name
        )
        session.add(new_category)
        results["categories_created"] += 1

    created_categories[category_name] = category_hash
    return category_hash


async def get_or_create_vehicle(session, vehicle_name, start_year, end_year, vehicle_type, hash_brand, created_vehicles, results):
    """Get an existing vehicle or create a new one"""
    # Check if already processed
    if vehicle_name in created_vehicles:
        return

    # Check database
    stmt = select(Vehicle).where(Vehicle.vehicle_name == vehicle_name)
    result = await session.execute(stmt)
    existing_vehicle = result.scalars().first()

    if not existing_vehicle:
        new_vehicle = Vehicle(
            vehicle_name=vehicle_name,
            start_year=start_year,
            end_year=end_year,
            vehicle_type=vehicle_type,
            hash_brand=hash_brand
        )
        session.add(new_vehicle)
        results["vehicles_created"] += 1

    created_vehicles[vehicle_name] = True


async def get_or_create_compatibility(session, product_code, vehicle_name, results):
    """Create a compatibility if it doesn't exist"""
    # Check if compatibility exists
    stmt = select(Compatibility).where(
        Compatibility.cod_product == product_code,
        Compatibility.vehicle_name == vehicle_name
    )
    result = await session.execute(stmt)
    existing_compat = result.scalars().first()

    if not existing_compat:
        compatibility = Compatibility(
            cod_product=product_code,
            vehicle_name=vehicle_name
        )
        session.add(compatibility)
        results["compatibilities_created"] += 1

# Synchronous wrapper function to handle the batch loop
def process_excel(file_path, batch_size=100):
    """
    Synchronous wrapper for asynchronous processing function.
    This is what you'll call from your Flask routes.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_process_excel_async(file_path, batch_size))
    finally:
        loop.close()
        
def is_image_file(filename):
    valid_extensions = ('.png', '.jpg', '.jpeg', '.webp')
    
    return filename.lower().endswith(valid_extensions)

def extract_existing_product_codes():
    existing_images = db.session.query(Images.cod_product).filter(
        Images.cod_product.like("f{filename_no_ext}%")
    ).all()
    
    existing_codes = {img.cod_product for img in existing_images}
    
    if existing_codes:
        numbers = [int(code.split("+")[-1]) for code in existing_codes if "-" in code]
        next_num = max(numbers) + 1 if numbers else 1
        
        return next_num
    else:
        next_num = 1
        
        return next_num
    

""" ----------------------------- Function to handle json from the database ------------------------------ """

def serialize_product(products):
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
                vehicle_brand = vehicle.vehicle_brand if hasattr(vehicle, 'vehicle_brand') else None
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

def serialize_meta_pagination(total, pages, page, per_page):
    
    return {
        "total_items": total,
        "total_pages": pages,
        "current_page": page,
        "per_page": per_page
    }
