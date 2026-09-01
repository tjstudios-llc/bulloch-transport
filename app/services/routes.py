import logging
from typing import List, Dict, Any, Optional
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from app.config.firebase import db, rtdb
from app.services.geocoding import get_street_name_from_coords

logger = logging.getLogger("bulloch.services.routes")


# =========================================================
# HELPER VALIDATIONS
# =========================================================

def _validate_coordinates(lat: float, lng: float) -> bool:
    """Validates latitude and longitude range limits."""
    return -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0


# =========================================================
# ROUTE CRUD OPERATIONS
# =========================================================

def create_route(
    route_name: str,
    bus_number: str,
    shift: str,
    stops: List[Dict[str, Any]],
    path_polyline: Optional[List[Any]] = None,
    assigned_driver: str = "Unassigned",
) -> bool:
    """Validates coordinates and persists a new route document to Firestore."""
    if not route_name or not route_name.strip():
        logger.error("Route creation failed: Name cannot be empty.")
        return False

    try:
        cleaned_stops = []
        for idx, stop in enumerate(stops):
            try:
                lat = float(stop["lat"])
                lng = float(stop["lng"])
            except (KeyError, ValueError, TypeError):
                logger.error(f"Invalid coordinate types in stop index {idx}")
                return False

            if not _validate_coordinates(lat, lng):
                logger.error(f"Coordinates out of bounds in stop index {idx}: ({lat}, {lng})")
                return False

            street = stop.get("street_name")
            if not street:
                street = get_street_name_from_coords(lat, lng)

            cleaned_stop = {
                "name": str(stop.get("name", f"Stop #{idx + 1}")).strip(),
                "street_name": str(street).strip(),
                "lat": lat,
                "lng": lng,
                "status": str(stop.get("status", "current" if idx == 0 else "pending")),
            }
            cleaned_stops.append(cleaned_stop)

        cleaned_polyline = []
        if path_polyline:
            for coord in path_polyline:
                if isinstance(coord, dict):
                    lat = float(coord.get("lat", 0.0))
                    lng = float(coord.get("lng", 0.0))
                else:
                    lat = float(coord[0])
                    lng = float(coord[1])

                if _validate_coordinates(lat, lng):
                    cleaned_polyline.append({"lat": lat, "lng": lng})

        route_doc = {
            "name": str(route_name).strip(),
            "assigned_bus": str(bus_number).strip(),
            "bus_number": str(bus_number).strip(),
            "shift": str(shift).strip(),
            "assigned_driver": str(assigned_driver).strip(),
            "stops": cleaned_stops,
            "path_polyline": cleaned_polyline,
            "active": True,
            "created_at": firestore.SERVER_TIMESTAMP,
        }

        db.collection("routes").add(route_doc)
        logger.info(f"Successfully created route '{route_name}' for Bus #{bus_number}.")
        return True

    except Exception as e:
        logger.exception(f"Error creating route '{route_name}': {e}")
        return False


def fetch_all_routes() -> List[Dict[str, Any]]:
    """Retrieves all configured routes from the 'routes' collection."""
    try:
        docs = db.collection("routes").stream()
        routes_list = []
        for doc in docs:
            data = doc.to_dict() or {}
            data["id"] = doc.id
            routes_list.append(data)
        return routes_list
    except Exception as e:
        logger.error(f"Error fetching routes from Firestore: {e}")
        return []


def update_route(route_id: str, updated_data: Dict[str, Any]) -> bool:
    """Updates an existing route document with whitelist protection."""
    if not route_id or not route_id.strip():
        return False

    allowed_fields = {
        "name",
        "assigned_bus",
        "bus_number",
        "shift",
        "assigned_driver",
        "stops",
        "path_polyline",
        "active",
    }
    filtered_payload = {k: v for k, v in updated_data.items() if k in allowed_fields}

    if not filtered_payload:
        logger.warning(f"No valid fields provided for route update ID: {route_id}")
        return False

    try:
        db.collection("routes").document(route_id.strip()).update(filtered_payload)
        logger.info(f"Successfully updated route ID '{route_id}'.")
        return True
    except Exception as e:
        logger.error(f"Error updating route ID '{route_id}': {e}")
        return False


def delete_route(route_id: str) -> bool:
    """Permanently deletes a route from Firestore."""
    if not route_id or not route_id.strip():
        return False

    try:
        db.collection("routes").document(route_id.strip()).delete()
        logger.info(f"Successfully deleted route ID '{route_id}'.")
        return True
    except Exception as e:
        logger.error(f"Error deleting route ID '{route_id}': {e}")
        return False


def fetch_active_route_for_bus(bus_number: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Fetches the active route assigned strictly to the specified bus number.
    Removes arbitrary fallbacks to prevent assigning unintended routes.
    """
    if not bus_number or not str(bus_number).strip():
        return None

    bus_str = str(bus_number).strip()

    try:
        routes_ref = db.collection("routes")
        query = (
            routes_ref.where(filter=FieldFilter("assigned_bus", "==", bus_str))
            .where(filter=FieldFilter("active", "==", True))
            .limit(1)
            .stream()
        )

        for doc in query:
            data = doc.to_dict() or {}
            data["id"] = doc.id
            return data

        # Secondary match check against legacy field naming
        query_alt = (
            routes_ref.where(filter=FieldFilter("bus_number", "==", bus_str))
            .where(filter=FieldFilter("active", "==", True))
            .limit(1)
            .stream()
        )
        for doc in query_alt:
            data = doc.to_dict() or {}
            data["id"] = doc.id
            return data

        return None

    except Exception as e:
        logger.error(f"Error fetching active route for bus '{bus_number}': {e}")
        return None


# =========================================================
# STOP STATUS UPDATES
# =========================================================

def update_stop_status(route_id: str, stop_index: int, status: str) -> bool:
    """Updates a single stop status safely within Firestore."""
    if not route_id or stop_index < 0:
        return False

    try:
        route_ref = db.collection("routes").document(route_id.strip())
        doc = route_ref.get()

        if not doc.exists:
            return False

        stops = doc.to_dict().get("stops", [])
        if 0 <= stop_index < len(stops):
            stops[stop_index]["status"] = str(status).strip()
            route_ref.update({"stops": stops})
            return True

        return False

    except Exception as e:
        logger.error(f"Error updating stop index {stop_index} for route '{route_id}': {e}")
        return False


def update_stop_status_in_firestore(route_id: str, stops: List[Dict[str, Any]]) -> bool:
    """Bulk updates all stop statuses for a route in Firestore."""
    if not route_id:
        return False

    try:
        db.collection("routes").document(route_id.strip()).update({"stops": stops})
        return True
    except Exception as e:
        logger.error(f"Error updating stops bulk for route '{route_id}': {e}")
        return False


# =========================================================
# EMERGENCY DISPATCH SERVICES
# =========================================================

def send_emergency_sos(
    bus_number: str,
    driver_name: str = "Driver",
    message: str = "EMERGENCY SOS SIGNAL ACTIVATED",
    location: Optional[Dict[str, float]] = None,
) -> bool:
    """
    Transmits an urgent emergency SOS alert to both Firestore and RTDB for instant dashboard push notification.
    """
    try:
        bus_str = str(bus_number).strip()
        loc_payload = {}
        if location and isinstance(location, dict):
            lat = float(location.get("lat", 0.0))
            lng = float(location.get("lng", 0.0))
            if _validate_coordinates(lat, lng):
                loc_payload = {"lat": lat, "lng": lng}

        alert_payload = {
            "bus_number": bus_str,
            "driver_name": str(driver_name).strip(),
            "message": str(message).strip(),
            "type": "SOS",
            "status": "active",
            "location": loc_payload,
            "timestamp": firestore.SERVER_TIMESTAMP,
        }

        # Save record in Firestore alerts collection
        doc_ref = db.collection("alerts").add(alert_payload)

        # Broadcast real-time alert event to RTDB
        rtdb_payload = {
            "alert_id": doc_ref[1].id,
            "bus_number": bus_str,
            "driver_name": str(driver_name).strip(),
            "message": str(message).strip(),
            "type": "SOS",
            "status": "active",
            "location": loc_payload,
            "created_at": firestore.SERVER_TIMESTAMP,
        }
        rtdb.reference(f"active_alerts/bus_{bus_str}").set(rtdb_payload)

        logger.warning(f"🚨 EMERGENCY SOS DISPATCHED for Bus #{bus_str}")
        return True

    except Exception as e:
        logger.error(f"Failed to transmit emergency SOS for Bus #{bus_number}: {e}")
        return False