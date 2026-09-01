import logging
from typing import List, Dict, Any, Optional
from app.config.firebase import db, rtdb

logger = logging.getLogger("bulloch.services.drivers")


def fetch_all_drivers(include_inactive: bool = False) -> List[Dict[str, Any]]:
    """
    Retrieves driver profiles from Firestore, merged with live operational state from RTDB.
    Filters out inactive driver accounts by default to safeguard dispatch workflows.
    """
    try:
        # Query primary user records in Firestore where role == "driver"
        drivers_ref = db.collection("users").where("role", "==", "driver")
        docs = list(drivers_ref.stream())

        # Fallback to legacy 'drivers' collection if 'users' has no driver roles provisioned
        if not docs:
            docs = list(db.collection("drivers").stream())

        # Fetch live operational state from RTDB
        rtdb_snapshot = rtdb.reference("users").get() or {}

        drivers = []
        for doc in docs:
            data = doc.to_dict() or {}
            driver_id = doc.id
            
            # Skip inactive accounts unless explicitly requested
            is_active = data.get("active", True)
            if not include_inactive and not is_active:
                continue

            rt_data = rtdb_snapshot.get(driver_id, {}) if isinstance(rtdb_snapshot, dict) else {}

            driver_profile = {
                "id": driver_id,
                "uid": driver_id,
                "name": data.get("name") or rt_data.get("name", "Unknown Driver"),
                "email": data.get("email") or rt_data.get("email", ""),
                "role": "driver",
                "assigned_bus": data.get("assigned_bus") or rt_data.get("assigned_bus"),
                "bus_number": data.get("assigned_bus") or rt_data.get("bus_number"),
                "active": is_active,
                "status": rt_data.get("status", "off_duty"),
                "formatted_location": rt_data.get("address") or rt_data.get("location", "Statesboro, GA"),
                "phone": data.get("phone") or rt_data.get("phone", ""),
            }
            drivers.append(driver_profile)

        return drivers

    except Exception as e:
        logger.error(f"Error fetching driver records across databases: {e}")
        return []


def get_driver_by_id(driver_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetches a specific driver profile by UID, joining Firestore identity with RTDB state.
    """
    if not driver_id or not driver_id.strip():
        return None

    cleaned_id = driver_id.strip()

    try:
        doc = db.collection("users").document(cleaned_id).get()
        if not doc.exists:
            doc = db.collection("drivers").document(cleaned_id).get()
            if not doc.exists:
                return None

        data = doc.to_dict() or {}
        rt_data = rtdb.reference(f"users/{cleaned_id}").get() or {}

        return {
            "id": cleaned_id,
            "uid": cleaned_id,
            "name": data.get("name") or rt_data.get("name", "Unknown Driver"),
            "email": data.get("email") or rt_data.get("email", ""),
            "role": data.get("role", "driver"),
            "assigned_bus": data.get("assigned_bus") or rt_data.get("assigned_bus"),
            "bus_number": data.get("assigned_bus") or rt_data.get("bus_number"),
            "active": data.get("active", True),
            "status": rt_data.get("status", "off_duty"),
            "formatted_location": rt_data.get("address") or rt_data.get("location", "Statesboro, GA"),
            "phone": data.get("phone") or rt_data.get("phone", ""),
        }
    except Exception as e:
        logger.error(f"Error fetching driver profile for ID '{cleaned_id}': {e}")
        return None


def search_drivers(query: str, include_inactive: bool = False) -> List[Dict[str, Any]]:
    """
    Searches drivers by Name, Email, or Assigned Bus Number.
    """
    all_drivers = fetch_all_drivers(include_inactive=include_inactive)
    if not query or not query.strip():
        return all_drivers

    clean_query = query.strip().lower()
    return [
        d for d in all_drivers
        if clean_query in str(d.get("name", "")).lower()
        or clean_query in str(d.get("email", "")).lower()
        or clean_query in str(d.get("assigned_bus", "")).lower()
        or clean_query in str(d.get("bus_number", "")).lower()
    ]