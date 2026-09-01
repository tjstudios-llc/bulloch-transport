import logging
from typing import Dict, Any, List, Callable, Optional
from app.config.firebase import db, rtdb

logger = logging.getLogger("bulloch.services.fleet")


def fetch_live_bus_locations() -> List[Dict[str, Any]]:
    """
    Fetches live positions for all active buses, merging Firestore bus configuration
    with Realtime Database live telemetry feeds.
    """
    try:
        # Load authoritative bus metadata from Firestore
        bus_docs = {doc.id: doc.to_dict() for doc in db.collection("buses").stream()}

        # Load live streaming telemetry from RTDB
        rtdb_buses = rtdb.reference("buses").get() or {}
        rtdb_devices = rtdb.reference("devices").get() or {}

        buses = []
        all_bus_ids = set(bus_docs.keys()).union(
            set(rtdb_buses.keys()) if isinstance(rtdb_buses, dict) else set()
        )

        for bus_id in all_bus_ids:
            fs_data = bus_docs.get(bus_id, {})
            rt_bus = rtdb_buses.get(bus_id, {}) if isinstance(rtdb_buses, dict) else {}
            
            device_id = fs_data.get("device_id") or rt_bus.get("device_id") or f"bus_{bus_id}"
            rt_device = rtdb_devices.get(device_id, {}) if isinstance(rtdb_devices, dict) else {}

            # Normalize lat/lng coordinates across schemas
            raw_lat = (
                rt_bus.get("lat")
                or rt_bus.get("latitude")
                or rt_device.get("lat")
                or rt_device.get("latitude")
                or fs_data.get("lat")
            )
            raw_lng = (
                rt_bus.get("lng")
                or rt_bus.get("longitude")
                or rt_device.get("lng")
                or rt_device.get("longitude")
                or fs_data.get("lng")
            )

            try:
                lat = float(raw_lat) if raw_lat is not None else None
                lng = float(raw_lng) if raw_lng is not None else None
            except (ValueError, TypeError):
                lat, lng = None, None

            bus_info = {
                "id": bus_id,
                "bus_number": fs_data.get("bus_number") or rt_bus.get("bus_number") or bus_id,
                "status": rt_bus.get("status") or fs_data.get("status", "inactive"),
                "lat": lat,
                "lng": lng,
                "speed": rt_bus.get("speed") or rt_device.get("speed", 0.0),
                "heading": rt_bus.get("heading") or rt_device.get("heading", 0.0),
                "driver_id": rt_bus.get("driver_id") or fs_data.get("assigned_driver_id"),
                "driver_name": rt_bus.get("driver_name") or fs_data.get("assigned_driver_name"),
                "route_id": rt_bus.get("route_id") or fs_data.get("assigned_route_id"),
                "last_updated": rt_bus.get("last_updated") or rt_device.get("last_seen") or fs_data.get("last_updated"),
            }

            buses.append(bus_info)

        return buses

    except Exception as exc:
        logger.error(f"Error fetching live bus fleet data: {exc}")
        return []


def listen_to_bus_updates(callback: Callable[[List[Dict[str, Any]]], None]):
    """
    Attaches a real-time snapshot listener on the 'buses' collection.
    Executes callback safely with error isolation.
    """
    try:
        buses_ref = db.collection("buses")

        def on_snapshot(col_snapshot, changes, read_time):
            buses = []
            for doc in col_snapshot:
                data = doc.to_dict() or {}
                data["id"] = doc.id
                buses.append(data)
            try:
                callback(buses)
            except Exception as cb_err:
                logger.error(f"Error executing callback in fleet snapshot listener: {cb_err}")

        query_watch = buses_ref.on_snapshot(on_snapshot)
        logger.info("Established Firestore real-time listener for bus updates.")
        return query_watch

    except Exception as e:
        logger.error(f"Failed to attach snapshot listener for bus updates: {e}")
        return None