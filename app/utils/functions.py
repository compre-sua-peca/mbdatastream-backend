import asyncio

from flask import json
from app.models import Images
from app.extensions import db
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from app.dal.encryptor import HashGenerator

""" --------------------------------- Functions to handle product, category, compatibility and vehicles insertions on the database --------------------------------- """
# Extract compatibilities from the compat column from Excel and tranform it in an array/list


def extract_compat_to_list(compat_str: str) -> list[str]:
    """
    Turns strings like:
      "[ '1974' ; '1973' ; '1984' ]"
      "'Desconhecido', 'Desconhecido', 'Desconhecido'"
      "A,B,C"
      ""
    into lists of clean values: ["1974","1973","1984"], ["Desconhecido",…], ["A","B","C"], []
    """
    # 1) guard clauses
    if not compat_str or pd.isna(compat_str):
        return []

    # 2) remove outer brackets, parens, and any quotes
    cleaned = re.sub(r"^[\[\(\s]*|[\]\)\s]*$", "",
                     compat_str)  # strip [] or ()
    cleaned = cleaned.replace("'", "").replace('"', "")

    # 3) split on semicolons OR commas (one or more)
    parts = re.split(r"[;,]+", cleaned)

    # 4) strip whitespace and drop blank entries
    return [p.strip() for p in parts if p.strip()]

# Asynchronous processing function to process the product insertion in batches after reading the Excel


async def _process_excel_async(file_path, batch_size, id_seller):
    try:
        # Read the Excel file
        if not id_seller:
            return {"error": "ID do vendedor não fornecido"}
        
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
            "images_created": 0,
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
                results,
                id_seller
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


async def process_batch(batch_df, batch_idx, created_categories, created_vehicles, created_brands, results, id_seller):
    """
    Processa cada linha em batch_df, abrindo um AsyncSession por linha.
    Se process_row não lançar exceção, dá commit; senão, dá rollback e registra erro.
    """

    # Para cada linha do DataFrame, criamos uma sessão independente
    for index, row in batch_df.iterrows():
        try:
            # 1) Abre um session novo para esta linha
            async with db.async_session() as session:
                try:
                    # 2) Processa a linha (essa função NÃO comita nem dá rollback)
                    await process_row(
                        index,
                        row,
                        session,
                        created_categories,
                        created_vehicles,
                        created_brands,
                        results,
                        id_seller
                    )
                    # 3) Se não houve erro, commit desta transação
                    await session.commit()
                    results["processed"] += 1

                except Exception as e:
                    # 4) Se der qualquer erro em process_row, faz rollback
                    await session.rollback()
                    # Lança novamente para o bloco de fora capturar e registrar a mensagem
                    raise

        except Exception as e:
            # Aqui está fora do "async with session", ou seja, já rollbackado e session fechado
            results["errors"].append(f"Error on row {index + 2}: {str(e)}")
            # Continua para a próxima linha, sem interromper todo o batch
            continue



# Function to check the existence of the data and then register each row on the database
async def process_row(index, row, session, created_categories, created_vehicles, created_brands, results, id_seller):
    """Process a single row from the Excel file"""
    if not id_seller:
            return {"error": "ID do vendedor não fornecido"}
        
    try:
        # Get category
        category_name = row.get("CATEGORY", "")
        category_hash = await get_or_create_category(
            session,
            category_name,
            created_categories,
            results
        )

        cod_product = await get_or_create_product(session, row, category_hash, results, id_seller)

        images = row.get("IMAGES", "")
        if images:
            image_list = images.split("|")
            
            await create_image(session, cod_product, image_list, results)

            await session.commit()

        # Extract vehicle compatibility info
        vehicles_names_string = row.get("COMPATIBILITY", "")
        start_year_string = row.get("START_YEAR", "")
        end_year_string = row.get("END_YEAR", "")
        vehicle_type_string = row.get("TYPE_VEHICLE", "")
        vehicle_brands_string = row.get("VEHICLE_BRAND", "")

        # Extract the values from the strings to lists
        names = extract_compat_to_list(vehicles_names_string)
        starts = extract_compat_to_list(start_year_string)
        ends = extract_compat_to_list(end_year_string)
        types = extract_compat_to_list(vehicle_type_string)
        brands = extract_compat_to_list(vehicle_brands_string)

        # Process vehicle compatibilities with zip_longest to grant same lengths, nulling if not equal
        for name, start, end, vtype, brand in zip_longest(
            names, starts, ends, types, brands, fillvalue=None
        ):

            # normalize & skip empties
            if not (name and brand):
                continue
            name = name.strip()
            brand = brand.strip()

            # normalize unknown years
            def norm_year(y):
                if not y or y.lower().startswith("desconhecido"):
                    return None
                return y.strip()

            start = norm_year(start)
            end = norm_year(end)

            # wrap in no_autoflush to avoid the Query-invoked autoflush error
            with session.no_autoflush:
                brand_hash = await get_or_create_vehicle_brand(
                    session, brand, created_brands, results
                )
                await get_or_create_vehicle(
                    session,
                    name,
                    start,
                    end,
                    vtype.strip() if vtype else None,
                    brand_hash,
                    created_vehicles,
                    results
                )

            # now it’s safe to commit/flush or do another query
            await get_or_create_compatibility(
                session, cod_product, name, results
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


async def get_or_create_product(session, row, category_hash, results, id_seller) -> str:
    """
    Verifica se já existe um Product.cod_product no banco. Se não existir,
    faz todos os checks de validação (nome, código de barras, quantidades, etc.),
    cria um novo Product, faz flush para garantir o INSERT antes de retornarmos,
    e incrementa o contador em results. Retorna sempre cod_product como string.
    """

    # Extrair e validar campos do row
    
    if not id_seller:
        raise ValueError("ID do vendedor não fornecido")
    
    name_product = row["NAME_PRODUCT"]
    name_check = name_product.split("-")[0].strip()
    is_manufactured = True

    # Se o prefixo for "ITEM DESCONTINUADO", ajustamos o nome e marcamos como não fabricado
    if name_check == "ITEM DESCONTINUADO":
        # Ex.: "ITEM DESCONTINUADO - Produto X"
        name_product = name_product.split("-", 1)[1].strip()
        is_manufactured = False

    # Validar bar_code: se for NaN, deixa None; senão, tenta converter para int
    bar_code = row["BAR_CODE"]
    if pd.isna(bar_code):
        bar_code = None
    else:
        try:
            bar_code = int(bar_code)
        except (ValueError, TypeError):
            bar_code = None

    # Validar gear_quantity: se for NaN, deixa None; senão, tenta converter para int
    gear_quantity = row["GEAR_QUANTITY"]
    if pd.isna(gear_quantity):
        gear_quantity = None
    else:
        try:
            gear_quantity = int(gear_quantity)
        except (ValueError, TypeError):
            gear_quantity = None

    # Outros campos simples (se vierem NaN, colocamos None)
    gear_dimensions = None if pd.isna(row.get("GEAR_DIMENSIONS", None)) else row.get("GEAR_DIMENSIONS")
    cross_reference = None if pd.isna(row.get("CROSS_REF", None)) else row.get("CROSS_REF")
    cod_product = str(row["COD_PRODUCT"]).strip()
    # Montar o dicionário que será passado ao construtor de Product
    product_dict = {
        "cod_product": cod_product,
        "name_product": name_product,
        "description": row.get("DESCRIPTION", "").strip(),
        "is_manufactured": is_manufactured,
        "bar_code": bar_code,
        "gear_quantity": gear_quantity,
        "gear_dimensions": gear_dimensions,
        "cross_reference": cross_reference,
        "hash_category": category_hash,
        "id_seller": id_seller,
    }

    # Verificar se o produto já existe no banco
    stmt = select(Product).where(Product.cod_product == cod_product)
    result = await session.execute(stmt)
    existing_product = result.scalars().first()

    # Se não existe, criamos e fazemos flush imediato
    if not existing_product:
        product = Product(**product_dict)
        session.add(product)
        # Incrementa contador local de produtos criados
        results["products_created"] = results.get("products_created", 0) + 1

        try:
            # Burla o autoflush tardio, envia o INSERT de Product ao banco agora
            await session.flush()
        except Exception as e:
            # Se der erro (PK duplicada, FK inválida, etc.), desfaz esta parte da transação
            await session.rollback()
            results.setdefault("errors", []).append(
                f"Erro ao criar Product {product_dict['cod_product']}: {str(e)}"
            )
            # Relança para que quem chamar possa tratar/abortar o processamento desta linha
            raise

    # Ao chegar aqui, ou o produto já existia, ou acabamos de criá-lo e dar flush.
    return cod_product


async def get_or_create_category(session, raw_name, created_categories, results):
    """
    Return the hash of an existing or newly-created Category.
    Guarantees no duplicate INSERT for same logical name.
    """

    # Normalize the name: strip whitespace and unify casing
    name_norm = raw_name.strip().upper()
    if not name_norm:
        raise ValueError("Empty category name!")

    # Check in-memory cache
    if name_norm in created_categories:
        return created_categories[name_norm]

    # Check the database by the normalized name
    stmt = select(Category).where(Category.name_category == name_norm)
    result = await session.execute(stmt)
    existing = result.scalars().first()

    if existing:
        cat_hash = existing.hash_category

    else:
        # Generate a hash, then attempt INSERT
        cat_hash = HashGenerator().generate_hash(name_norm)
        new_cat = Category(
            hash_category=cat_hash,
            name_category=name_norm,
            display_order=0
        )

        session.add(new_cat)

        try:
            await session.flush()   # push to DB so that IntegrityError happens now

            results["categories_created"] += 1

        except IntegrityError:
            # If someone else inserted the same hash concurrently,
            # roll back that insert, then re-query for the existing row:
            await session.rollback()
            stmt2 = select(Category).where(Category.hash_category == cat_hash)
            result2 = await session.execute(stmt2)
            existing = result2.scalars().first()
            if existing:
                cat_hash = existing.hash_category
            else:
                # This really shouldn't happen
                raise

    # Cache and return
    created_categories[name_norm] = cat_hash

    return cat_hash


async def get_or_create_vehicle(session, vehicle_name, start_year, end_year, vehicle_type, hash_brand, created_vehicles, results):
    """Get an existing vehicle or create a new one"""
    # Check if already processed
    if vehicle_name in created_vehicles:
        return

    # Check if brand exist
    # brand_check = await session.execute(
    #     select(VehicleBrand).where(VehicleBrand.hash_brand == hash_brand)
    # )
    # brand = brand_check.scalars().first()
    # if not brand:
    #     raise ValueError(f"Brand with hash '{hash_brand}' does not exist for vehicle '{vehicle_name}'")
    
    treated_vehicle_name = vehicle_name.upper()

    # Check database
    stmt = select(Vehicle).where(Vehicle.vehicle_name == treated_vehicle_name)
    result = await session.execute(stmt)
    existing_vehicle = result.scalars().first()

    if not existing_vehicle:
        new_vehicle = Vehicle(
            vehicle_name=treated_vehicle_name,
            start_year=start_year,
            end_year=end_year,
            vehicle_type=vehicle_type,
            hash_brand=hash_brand
        )
        session.add(new_vehicle)
        results["vehicles_created"] += 1

    created_vehicles[treated_vehicle_name] = True


async def get_or_create_compatibility(session, product_code, vehicle_name, results):
    """Create a compatibility if it doesn't exist"""
    
    treated_vehicle_name = vehicle_name.upper()
    
    # Check if compatibility exists
    stmt = select(Compatibility).where(
        Compatibility.cod_product == product_code,
        Compatibility.vehicle_name == treated_vehicle_name
    )
    result = await session.execute(stmt)
    existing_compat = result.scalars().first()

    if not existing_compat:
        compatibility = Compatibility(
            cod_product=product_code,
            vehicle_name=treated_vehicle_name
        )
        session.add(compatibility)
        results["compatibilities_created"] += 1


async def create_image(
    session,
    cod_product: str,
    urls: list[str],
    results: dict
):
    """
    Insere novas imagens para <cod_product>, numerando id_image como "<cod_product>-<número>".
    Antes de cada SELECT, faz flush para que não exista inconsisência entre pendências e BD real.
    Além disso, se encontrar exatamente id_image == cod_product (sem suffix), trata como sufixo 0.
    E, para cada novo new_id gerado, verifica explicitamente se ele já existe no banco. 
    Se existir, pula para o próximo.
    """

    # 1) Flush de quaisquer INSERTs/UPDATEs pendentes na sessão
    await session.flush()

    # 2) Busca todos os id_image que já existem no banco para este produto:
    stmt = select(Images.id_image).where(Images.id_image.like(f"{cod_product}%"))
    result = await session.execute(stmt)
    raw_existing = result.scalars().all()
    # Exemplo de raw_existing: ["2110655", "2110655-1", "2110655-2", ...]

    # 3) Determinar qual é o maior sufixo numérico. Se existir uma entrada igual a cod_product puro,
    #    vamos tratá-la como "sucesso zero" (ou seja, consideramos max_suffix >= 0).
    max_suffix = -1
    for full_id_image in raw_existing:
        if full_id_image == cod_product:
            # existe id_image exatamente igual ao cod_product
            max_suffix = max(max_suffix, 0)
            continue

        # se vier algo do tipo "2110655-17", fazemos rsplit:
        parts = full_id_image.rsplit("-", 1)
        if len(parts) == 2 and parts[0] == cod_product and parts[1].isdigit():
            num = int(parts[1])
            if num > max_suffix:
                max_suffix = num

    # Se não havia NADA (nem cod_product puro nem "<cod_product>-n"), max_suffix = -1
    # Logo, next_suffix = 0? Não, queremos iniciar em 1 mesmo que não tivesse imagem,
    # porque nosso primeiro id_image deverá ser "<cod_product>-1".
    # Mas se max_suffix == 0 (significa que existia um registro "cod_product" sem suffix),
    # então next_suffix = 1 gera "<cod_product>-1" sem colisão. Se max_suffix == 2,
    # next_suffix = 3, etc.
    next_suffix = max_suffix + 1
    if next_suffix < 1:
        next_suffix = 1

    # 4) Agora percorremos cada URL e tentamos inserir
    for url in urls:
        treated_url = url.strip()
        
        # Recalcular new_id com o next_suffix corrente
        new_id = f"{cod_product}-{next_suffix}"

        # 4.1) Verificar se já existe um registro com esse mesmo new_id
        stmt2 = select(Images).where(Images.id_image == new_id)
        r2 = await session.execute(stmt2)
        if r2.scalars().first():
            # Se id_image == new_id já existe, pulamos diretamente para o próximo sufixo
            next_suffix += 1
            # (não incrementamos imagens_created, pois nada foi inserido)
            continue

        # 4.2) Caso não exista, criamos e adicionamos
        image = Images(cod_product=cod_product, id_image=new_id, url=treated_url)
        session.add(image)
        results["images_created"] = results.get("images_created", 0) + 1

        # 4.3) Incrementa pour o próximo new_id
        next_suffix += 1

    # Atenção: não commitamos aqui. Quem chamou create_image deve chamar `await session.commit()`
    # após processar a linha inteira. Se ocorrer qualquer erro mais adiante, basta fazer rollback.


# Synchronous wrapper function to handle the batch loop
def process_excel(file_path, id_seller, batch_size=100):
    """
    Synchronous wrapper for asynchronous processing function.
    This is what you'll call from your Flask routes.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_process_excel_async(file_path, batch_size, id_seller))
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
        "cnpj": seller.cnpj,
        "seller_domain": seller.seller_domain
    }
    
    return result


def serialize_users(users):
    result = []
    
    for user in users:
        result.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "cnpj": user.cnpj,
            "whatsapp": user.whatsapp
        })
        
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