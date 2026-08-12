# app/services/drivers.py

import logging
from typing import List, Dict, Any, Optional
from app.config.firebase import db

logger = logging.getLogger(__name__)


def fetch_all_drivers() -> List[Dict[str, Any]]:
    """Fetches all users with the role 'driver' (or all registered drivers)."""
    try:
        # Assuming drivers are stored in 'users' collection with role 'driver'
        # Adjust collection name if stored in 'drivers'
        docs = db.collection("users").where("role", "==", "driver").stream()
        drivers = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            drivers.append(data)
        
        # Fallback: If no role filter is used, return from 'drivers' collection
        if not drivers:
            docs = db.collection("drivers").stream()
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                drivers.append(data)

        return drivers
    except Exception as e:
        logger.error(f"Error fetching drivers: {e}")
        return []


def search_drivers(query: str) -> List[Dict[str, Any]]:
    """
    Searches drivers by Name or Email (case-insensitive substring match).
    """
    all_drivers = fetch_all_drivers()
    if not query or not query.strip():
        return all_drivers

    clean_query = query.strip().lower()
    matched = []

    for driver in all_drivers:
        name = str(driver.get("name", "")).lower()
        email = str(driver.get("email", "")).lower()
        bus_number = str(driver.get("bus_number", "")).lower()

        if clean_query in name or clean_query in email or clean_query in bus_number:
            matched.append(driver)

    return matched