# app/services/routes.py

import logging
from typing import List, Dict, Any, Optional
from firebase_admin import firestore
from app.config.firebase import db
from app.services.geocoding import get_street_name_from_coords

logger = logging.getLogger(__name__)


# =========================================================
# ROUTE CRUD OPERATIONS
# =========================================================

def create_route(
    route_name: str, 
    bus_number: str, 
    shift: str, 
    stops: List[Dict[str, Any]], 
    path_polyline: Optional[List[List[float]]] = None,
    assigned_driver: str = "Unassigned"
) -> bool:
    """Saves a new route document to Firestore."""
    try:
        cleaned_stops = []
        for idx, stop in enumerate(stops):
            cleaned_stop = {
                "name": str(stop.get("name", f"Stop #{idx + 1}")),
                "street_name": str(stop.get("street_name") or get_street_name_from_coords(stop["lat"], stop["lng"])),
                "lat": float(stop["lat"]),
                "lng": float(stop["lng"]),
                "status": str(stop.get("status", "current" if idx == 0 else "pending"))
            }
            cleaned_stops.append(cleaned_stop)

        cleaned_polyline = []
        if path_polyline:
            for coord in path_polyline:
                cleaned_polyline.append([float(coord[0]), float(coord[1])])

        route_doc = {
            "name": str(route_name),
            "assigned_bus": str(bus_number),
            "bus_number": str(bus_number),
            "shift": str(shift),
            "assigned_driver": str(assigned_driver),
            "stops": cleaned_stops,
            "path_polyline": cleaned_polyline,
            "active": True,
            "created_at": firestore.SERVER_TIMESTAMP
        }
        
        db.collection("routes").add(route_doc)
        logger.info(f"Successfully created route '{route_name}'.")
        return True
    except Exception as e:
        logger.error(f"Error creating route '{route_name}': {e}")
        return False


def fetch_all_routes() -> List[Dict[str, Any]]:
    """Retrieves all configured routes from the 'routes' collection."""
    try:
        docs = db.collection("routes").stream()
        routes_list = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            routes_list.append(data)
        return routes_list
    except Exception as e:
        logger.error(f"Error fetching routes from Firestore: {e}")
        return []


def update_route(route_id: str, updated_data: Dict[str, Any]) -> bool:
    """Updates an existing route document in Firestore."""
    try:
        db.collection("routes").document(route_id).update(updated_data)
        logger.info(f"Successfully updated route ID '{route_id}'.")
        return True
    except Exception as e:
        logger.error(f"Error updating route ID '{route_id}': {e}")
        return False


def delete_route(route_id: str) -> bool:
    """Permanently deletes a route from Firestore."""
    try:
        db.collection("routes").document(route_id).delete()
        logger.info(f"Successfully deleted route ID '{route_id}'.")
        return True
    except Exception as e:
        logger.error(f"Error deleting route ID '{route_id}': {e}")
        return False


def fetch_active_route_for_bus(bus_number: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetches the active assigned route for a given bus number."""
    try:
        routes_ref = db.collection("routes")
        if bus_number:
            bus_str = str(bus_number)
            query = routes_ref.where("assigned_bus", "==", bus_str).where("active", "==", True).limit(1).stream()
            for doc in query:
                data = doc.to_dict()
                data["id"] = doc.id
                return data

        fallback_query = routes_ref.where("active", "==", True).limit(1).stream()
        for doc in fallback_query:
            data = doc.to_dict()
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
    """Updates a single stop's status within a route document."""
    try:
        route_ref = db.collection("routes").document(route_id)
        doc = route_ref.get()
        if doc.exists:
            stops = doc.to_dict().get("stops", [])
            if 0 <= stop_index < len(stops):
                stops[stop_index]["status"] = status
                route_ref.update({"stops": stops})
                return True
        return False
    except Exception as e:
        logger.error(f"Error updating stop status for route '{route_id}': {e}")
        return False


def update_stop_status_in_firestore(route_id: str, stops: List[Dict[str, Any]]) -> bool:
    """Bulk updates all stop statuses for a route in Firestore."""
    try:
        db.collection("routes").document(route_id).update({"stops": stops})
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
    location: Optional[Dict[str, float]] = None
) -> bool:
    """Logs an urgent SOS dispatch alert to the 'alerts' collection in Firestore."""
    try:
        alert_doc = {
            "bus_number": str(bus_number),
            "driver_name": str(driver_name),
            "message": str(message),
            "type": "SOS",
            "status": "active",
            "location": location or {},
            "timestamp": firestore.SERVER_TIMESTAMP
        }
        db.collection("alerts").add(alert_doc)
        logger.warning(f"🚨 EMERGENCY SOS DISPATCHED for Bus #{bus_number}")
        return True
    except Exception as e:
        logger.error(f"Failed to transmit emergency SOS for Bus #{bus_number}: {e}")
        return False