# app/services/users.py

import logging
from typing import List, Dict, Any
from app.config.firebase import rtdb

logger = logging.getLogger(__name__)


def fetch_all_users() -> List[Dict[str, Any]]:
    """
    Fetches all user/driver nodes directly from Firebase Realtime Database.
    """
    try:
        ref = rtdb.reference('users')
        snapshot = ref.get()

        if not snapshot:
            return []

        users = []
        # RTDB returns a dict of {user_id: user_data}
        for user_id, data in snapshot.items():
            if isinstance(data, dict):
                data['id'] = user_id
                data['formatted_location'] = data.get('address') or data.get('location', 'Statesboro, GA')
                users.append(data)

        return users

    except Exception as e:
        logger.error(f"Error reading from Firebase Realtime Database: {e}")
        return []


def update_user(user_id: str, updated_data: Dict[str, Any]) -> bool:
    """Updates a specific user's node in RTDB."""
    try:
        ref = rtdb.reference(f'users/{user_id}')
        ref.update(updated_data)
        logger.info(f"User {user_id} updated in RTDB.")
        return True
    except Exception as e:
        logger.error(f"Failed to update user {user_id}: {e}")
        return False


def delete_user(user_id: str) -> bool:
    """Removes a user node from RTDB."""
    try:
        ref = rtdb.reference(f'users/{user_id}')
        ref.delete()
        logger.info(f"User {user_id} removed from RTDB.")
        return True
    except Exception as e:
        logger.error(f"Failed to delete user {user_id}: {e}")
        return False


def search_users(query: str) -> List[Dict[str, Any]]:
    """Filters live RTDB users by name, email, or bus assignment."""
    all_users = fetch_all_users()
    if not query or not query.strip():
        return all_users

    q = query.strip().lower()
    return [
        u for u in all_users
        if q in str(u.get('name', '')).lower()
        or q in str(u.get('email', '')).lower()
        or q in str(u.get('assigned_bus', '')).lower()
        or q in str(u.get('bus_number', '')).lower()
    ]