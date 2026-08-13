# app/services/fleet.py

import logging
from typing import Dict, Any, List
from firebase_admin import firestore

logger = logging.getLogger("bulloch-transport")


def get_firestore_client():
    """Returns an active Firestore database client instance."""
    return firestore.client()


def fetch_live_bus_locations() -> List[Dict[str, Any]]:
    """
    Fetches the latest live positions for all active buses from Firestore.
    """
    try:
        db = get_firestore_client()
        docs = db.collection("buses").stream()
        
        buses = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            buses.append(data)
            
        return buses
    except Exception as exc:
        logger.error("Error fetching live bus data from Firestore: %s", exc)
        return []


def listen_to_bus_updates(callback):
    """
    Sets up a real-time snapshot listener on the 'buses' collection.
    Executes 'callback(buses_list)' whenever a bus position changes.
    """
    db = get_firestore_client()
    buses_ref = db.collection("buses")

    def on_snapshot(col_snapshot, changes, read_time):
        buses = [doc.to_dict() | {"id": doc.id} for doc in col_snapshot]
        callback(buses)

    # Attach listener
    query_watch = buses_ref.on_snapshot(on_snapshot)
    return query_watch