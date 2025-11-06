from asyncio.log import logger
import os
from typing import Any, Dict, Optional, Set
import requests
from requests import RequestException
from flask import jsonify
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.dal.encryptor import HashGenerator
from app.extensions import db
from app.models import Compatibility, Vehicle, VehicleBrand, SellerVehicles, SellerBrands


class DatabaseError(Exception):
    pass


def get_compatibility_info(ids_model: list[int]):
    COMPAT_URL = os.environ.get('COMPAT_URL')

    try:
        response = requests.post(
            f"{COMPAT_URL}/get-models-aggr", json=ids_model)

        return response.json()

    except RequestException as e:
        return jsonify({"error": e})


def get_or_create_vehicle_brand(
    brand_name: str,
    id_seller: str
) -> VehicleBrand:
    """Get existing VehicleBrand or create a new one. Returns the model instance."""
    if not brand_name or not isinstance(brand_name, str):
        raise ValueError("brand_name must be a non-empty string")

    hash_generator = HashGenerator()
    brand_name_up = brand_name.upper().strip()
    treated_brand_name = brand_name_up.replace(" ", "")

    try:
        # 1) Try to find existing brand
        stmt = select(VehicleBrand).where(
            VehicleBrand.brand_name == brand_name_up)
        result = db.session.execute(stmt)
        existing_brand = result.scalars().first()
        if existing_brand:
            return existing_brand

        # 2) Create new brand (transaction context manager commits for us)
        hash_brand = hash_generator.generate_hash(treated_brand_name)
        new_brand = VehicleBrand(
            hash_brand=hash_brand,
            brand_name=brand_name_up,
            brand_image=None
        )
        
        seller_brand = SellerBrands(
            id_seller=id_seller,
            hash_brand=hash_brand
        )

        try:
            db.session.add(new_brand)
            db.session.add(seller_brand)
            db.session.commit()

            return new_brand

        except IntegrityError as ie:
            # Race condition: another process created the brand between select() and add()
            logger.warning(
                "IntegrityError creating VehicleBrand %s: %s", brand_name_up, ie)
            db.session.rollback()
            # reselect
            stmt = select(VehicleBrand).where(
                VehicleBrand.brand_name == brand_name_up)
            result = db.session.execute(stmt)
            existing_after = result.scalars().first()
            if existing_after:
                return existing_after
            raise DatabaseError(
                f"Integrity error creating brand '{brand_name_up}': {ie}") from ie

    except SQLAlchemyError as e:
        logger.exception(
            "Database error in get_or_create_vehicle_brand(%s)", brand_name_up)
        db.session.rollback()
        raise DatabaseError(
            f"DB error while getting/creating vehicle brand '{brand_name_up}': {e}") from e


def get_or_create_vehicle(
    hash_brand: str,
    vehicle: Dict[str, Any],
    vehicles: list,
    id_seller: str,
    seen_vehicles: Optional[Set[str]] = None
):
    treated_vehicle_name = vehicle.get("vehicle_name").upper()

    try:
        # Check if vehicle exists
        stmt = select(Vehicle).where(
            Vehicle.vehicle_name == treated_vehicle_name
        )
        result = db.session.execute(stmt)
        existing = result.scalars().first()

        if treated_vehicle_name in seen_vehicles:
            return

        if existing:
            vehicles.append(vehicle)
            return existing

        # Create new vehicle
        new_vehicle = Vehicle(
            vehicle_name=treated_vehicle_name,
            start_year=vehicle.get("start_year"),
            end_year=vehicle.get("end_year"),
            vehicle_type=vehicle.get("vehicle_type"),
            hash_brand=hash_brand
        )
        
        seller_vehicle = SellerVehicles(
            id_seller=id_seller,
            vehicle_name=new_vehicle.vehicle_name
        )

        try:
            db.session.add(new_vehicle)
            db.session.add(seller_vehicle)
            db.session.commit()

            vehicles.append(vehicle)
            return new_vehicle

        except IntegrityError as ie:
            logger.warning("IntegrityError creating Vehicle %s: %s",
                           treated_vehicle_name, ie)
            db.session.rollback()

            # try to recover by reselecting
            stmt = select(Vehicle).where(
                Vehicle.vehicle_name == treated_vehicle_name)
            result = db.session.execute(stmt)
            existing_after = result.scalars().first()
            if existing_after:
                return existing_after
            raise DatabaseError(
                f"Integrity error creating vehicle '{treated_vehicle_name}': {ie}") from ie

    except SQLAlchemyError as e:
        logger.exception(
            "Database error in get_or_create_vehicle(%s)", treated_vehicle_name)
        db.session.rollback()
        raise DatabaseError(
            f"DB error while getting/creating vehicle '{treated_vehicle_name}': {e}") from e


def handle_brand_compatibility(
    brand_name: str,
    hash_brand: str,
    seen_hash_brands: dict,
    brands: list
):
    dedupe_key = hash_brand if hash_brand else (brand_name or None)

    if dedupe_key in seen_hash_brands:
        return

    brands.append({
        "brand_name": brand_name,
        "hash_brand": hash_brand
    })

    seen_hash_brands.add(hash_brand)

    return


def handle_compatibility(
    cod_product: str,
    vehicles: list
):
    # vehicle_name = vehicle.get("vehicle_name")
    
    try:
        stmt = select(Compatibility).where(
            Compatibility.cod_product == cod_product
        )
        
        # Querying the existent compats for that product
        query = db.session.execute(stmt)
        db_compats = query.scalars().all()
        
        # Existing compatibility ids stored in DB
        kept_compats = [c.vehicle_name for c in db_compats]
        
        incoming_ids = []
        
        for vehicle in vehicles:
            if vehicle is None:
                continue
            
            incoming_ids.append(vehicle.get("vehicle_name"))
            
        # Normalizing the ids
        incoming_ids = [i for i in incoming_ids if i is not None]
        
        # Take the compatibilites that aren't anymore on the database and save them to be deleted
        be_deleted = [kept_compat for kept_compat in kept_compats if kept_compat not in incoming_ids]
        
        if be_deleted:
            del_stmt = delete(Compatibility).where(Compatibility.vehicle_name.in_(be_deleted))
            db.session.execute(del_stmt)
            db.session.commit()
            
        else:
            db.session.rollback()
            
        to_create = [incoming_id for incoming_id in incoming_ids if incoming_id not in kept_compats]
        
        if to_create:
            for vehicle_name in to_create:
                new_compat = Compatibility(
                    cod_product=cod_product,
                    vehicle_name=vehicle_name
                )
                db.session.add(new_compat)
                db.session.commit()
            
        return {
            "kept": kept_compats,
            "incoming": to_create,
            "to_delete": be_deleted
        }
        
    except SQLAlchemyError as e:
        db.session.rollback()
        raise DatabaseError(
            f"DB error while creating compatibilities for product with code '{cod_product}': {e}") from e

# def handle_vehicle_compatibility():
