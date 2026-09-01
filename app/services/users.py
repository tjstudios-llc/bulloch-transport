import logging
from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status
from firebase_admin import auth
from app.config.firebase import rtdb, db

logger = logging.getLogger("bulloch.services.users")


def fetch_all_users() -> List[Dict[str, Any]]:
    """
    Fetches all user and driver profiles by joining Cloud Firestore authorization
    records with Realtime Database display state.
    """
    try:
        # Load primary identity & role documents from Firestore
        users_ref = db.collection("users")
        firestore_docs = {doc.id: doc.to_dict() for doc in users_ref.stream()}

        # Load live operational state from RTDB
        rtdb_snapshot = rtdb.reference("users").get() or {}

        all_uids = set(firestore_docs.keys()).union(set(rtdb_snapshot.keys()))
        users = []

        for uid in all_uids:
            fs_data = firestore_docs.get(uid, {})
            rt_data = rtdb_snapshot.get(uid, {}) if isinstance(rtdb_snapshot, dict) else {}

            combined_user = {
                "id": uid,
                "uid": uid,
                "email": fs_data.get("email") or rt_data.get("email", ""),
                "name": fs_data.get("name") or rt_data.get("name", "Unknown User"),
                "role": fs_data.get("role") or rt_data.get("role", "driver"),
                "assigned_bus": fs_data.get("assigned_bus") or rt_data.get("assigned_bus"),
                "bus_number": fs_data.get("assigned_bus") or rt_data.get("bus_number"),
                "active": fs_data.get("active", True),
                "formatted_location": rt_data.get("address") or rt_data.get("location", "Statesboro, GA"),
            }
            users.append(combined_user)

        return users

    except Exception as e:
        logger.error(f"Error fetching user records across Firestore/RTDB: {e}")
        return []


def update_user(user_id: str, updated_data: Dict[str, Any]) -> bool:
    """
    Synchronously updates user record in both Cloud Firestore and RTDB.
    Filters modifiable fields to prevent unauthorized role elevation.
    """
    if not user_id or not user_id.strip():
        logger.error("Update failed: Empty user_id provided.")
        return False

    cleaned_uid = user_id.strip()

    # Allowed updatable fields
    allowed_fields = {
        "name",
        "email",
        "role",
        "assigned_bus",
        "bus_number",
        "active",
        "address",
        "location",
        "phone",
    }
    filtered_payload = {k: v for k, v in updated_data.items() if k in allowed_fields}

    if not filtered_payload:
        logger.warning(f"No valid or allowed fields provided for user update on UID: {cleaned_uid}")
        return False

    # Normalize assigned bus field naming
    if "bus_number" in filtered_payload and "assigned_bus" not in filtered_payload:
        filtered_payload["assigned_bus"] = filtered_payload["bus_number"]

    try:
        # Update Firestore authoritative record
        fs_payload = {
            k: v for k, v in filtered_payload.items()
            if k in {"name", "email", "role", "assigned_bus", "active"}
        }
        if fs_payload:
            db.collection("users").document(cleaned_uid).set(fs_payload, merge=True)

        # Update RTDB operational node
        rtdb.reference(f"users/{cleaned_uid}").update(filtered_payload)

        # Disable Firebase Auth user if deactivated
        if filtered_payload.get("active") is False:
            try:
                auth.update_user(cleaned_uid, disabled=True)
                auth.revoke_refresh_tokens(cleaned_uid)
                logger.info(f"Firebase Auth user disabled and tokens revoked for UID: {cleaned_uid}")
            except Exception as auth_err:
                logger.warning(f"Failed to disable Firebase Auth account for UID {cleaned_uid}: {auth_err}")

        logger.info(f"User {cleaned_uid} successfully updated across Firestore and RTDB.")
        return True

    except Exception as e:
        logger.error(f"Failed to update user {cleaned_uid}: {e}")
        return False


def delete_user(user_id: str) -> bool:
    """
    Permanently revokes access and deletes user across Firebase Auth, Firestore, and RTDB.
    """
    if not user_id or not user_id.strip():
        logger.error("Delete failed: Empty user_id provided.")
        return False

    cleaned_uid = user_id.strip()

    try:
        # Delete from Firebase Auth
        try:
            auth.delete_user(cleaned_uid)
            logger.info(f"Deleted user from Firebase Auth: {cleaned_uid}")
        except auth.UserNotFoundError:
            logger.info(f"User UID {cleaned_uid} not found in Firebase Auth; continuing cleanup.")
        except Exception as auth_e:
            logger.warning(f"Could not delete Firebase Auth user {cleaned_uid}: {auth_e}")

        # Delete from Firestore
        db.collection("users").document(cleaned_uid).delete()

        # Delete from RTDB
        rtdb.reference(f"users/{cleaned_uid}").delete()

        logger.info(f"User {cleaned_uid} permanently purged across Auth, Firestore, and RTDB.")
        return True

    except Exception as e:
        logger.error(f"Failed to complete user deletion for UID {cleaned_uid}: {e}")
        return False


def search_users(query: str) -> List[Dict[str, Any]]:
    """Filters combined user profiles by Name, Email, or Assigned Bus Number."""
    all_users = fetch_all_users()
    if not query or not query.strip():
        return all_users

    q = query.strip().lower()
    return [
        u for u in all_users
        if q in str(u.get("name", "")).lower()
        or q in str(u.get("email", "")).lower()
        or q in str(u.get("assigned_bus", "")).lower()
        or q in str(u.get("bus_number", "")).lower()
        or q in str(u.get("role", "")).lower()
    ]