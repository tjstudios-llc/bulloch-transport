import secrets
import hashlib
import time
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from fastapi import HTTPException, status
from app.config.firebase import rtdb, db
from app.services.geocoding import get_street_name_from_coords

logger = logging.getLogger(__name__)

_ACTIVATION_RATE_LIMITS: Dict[str, list] = {}


# =========================================================
# RATE LIMITING & SECURITY HELPERS
# =========================================================

def check_activation_rate_limit(key: str, max_requests: int = 5, window_seconds: int = 300) -> None:
    """
    In-memory rate limiter to mitigate brute-force attempts against activation codes.
    """
    now = time.time()
    timestamps = _ACTIVATION_RATE_LIMITS.get(key, [])
    timestamps = [ts for ts in timestamps if now - ts < window_seconds]
    
    if len(timestamps) >= max_requests:
        logger.warning(f"Rate limit exceeded for activation key: {key}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many activation attempts. Please wait before trying again.",
        )
        
    timestamps.append(now)
    _ACTIVATION_RATE_LIMITS[key] = timestamps


# =========================================================
# CORE DEVICE CRUD OPERATIONS (REALTIME DATABASE)
# =========================================================

def fetch_all_devices() -> List[Dict[str, Any]]:
    """Retrieves all tracking hardware devices from Firebase Realtime Database."""
    try:
        ref = rtdb.reference("devices")
        snapshot = ref.get()

        if not snapshot:
            return []

        devices = []
        for device_id, data in snapshot.items():
            if isinstance(data, dict):
                data["id"] = device_id

                lat = data.get("lat") or data.get("latitude") or data.get("current_lat")
                lng = data.get("lng") or data.get("longitude") or data.get("current_lng")
                raw_address = data.get("address") or data.get("last_location_name")

                if raw_address:
                    data["formatted_location"] = raw_address
                elif lat and lng:
                    street = get_street_name_from_coords(float(lat), float(lng))
                    data["formatted_location"] = f"{street}, Statesboro, GA"
                else:
                    data["formatted_location"] = "Location Unavailable / Offline"

                devices.append(data)
        return devices
    except Exception as e:
        logger.error(f"Error fetching devices from RTDB: {e}")
        return []


def create_device(device_data: Dict[str, Any]) -> bool:
    """Adds a new tracking device unit to Realtime Database."""
    try:
        ref = rtdb.reference("devices")
        ref.push(device_data)
        logger.info(f"Device '{device_data.get('serial_number')}' added successfully to RTDB.")
        return True
    except Exception as e:
        logger.error(f"Failed to create device in RTDB: {e}")
        return False


def update_device(device_id: str, updated_data: Dict[str, Any]) -> bool:
    """Updates device details in Realtime Database."""
    try:
        rtdb.reference(f"devices/{device_id}").update(updated_data)
        logger.info(f"Device '{device_id}' updated successfully in RTDB.")
        return True
    except Exception as e:
        logger.error(f"Failed to update device '{device_id}' in RTDB: {e}")
        return False


def delete_device(device_id: str) -> bool:
    """Permanently removes a device node from Realtime Database."""
    try:
        rtdb.reference(f"devices/{device_id}").delete()
        logger.info(f"Device '{device_id}' deleted successfully from RTDB.")
        return True
    except Exception as e:
        logger.error(f"Failed to delete device '{device_id}' from RTDB: {e}")
        return False


def search_devices(query: str) -> List[Dict[str, Any]]:
    """Filters devices by Serial Number, Assigned Bus Number, or Device Model."""
    all_devices = fetch_all_devices()
    if not query or not query.strip():
        return all_devices

    q = query.strip().lower()
    return [
        d for d in all_devices
        if q in str(d.get("serial_number", "")).lower()
        or q in str(d.get("assigned_bus", "")).lower()
        or q in str(d.get("bus_number", "")).lower()
        or q in str(d.get("model", "")).lower()
    ]


# =========================================================
# HARDENED DEVICE ACTIVATION & PROVISIONING OPERATIONS
# =========================================================

def generate_activation_code(assigned_bus: str, admin_uid: str) -> Dict[str, Any]:
    """
    Generates a cryptographically strong 6-digit activation code with 15-minute TTL.
    """
    # Use secrets module instead of random for cryptographic security
    code = "".join([str(secrets.randbelow(10)) for _ in range(6)])
    expires_at = int(datetime.now(timezone.utc).timestamp()) + 900  # 15 min TTL

    try:
        # Store activation code record in RTDB
        rtdb.reference(f"activation_codes/{code}").set({
            "code": code,
            "assigned_bus": assigned_bus,
            "created_by": admin_uid,
            "expires_at": expires_at,
            "used": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        
        logger.info(f"Generated secure activation code {code} for Bus #{assigned_bus}")
        return {"code": code, "expires_at": expires_at, "assigned_bus": assigned_bus}
    except Exception as e:
        logger.error(f"Error persisting activation code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate activation code.",
        )


def verify_activation_code(code: str) -> Optional[Dict[str, Any]]:
    """
    Validates code existence, active status, and expiration TTL in Realtime Database.
    Removes hardcoded legacy token fallbacks.
    """
    cleaned_code = code.strip()
    if not cleaned_code or len(cleaned_code) != 6 or not cleaned_code.isdigit():
        return None

    try:
        ref = rtdb.reference(f"activation_codes/{cleaned_code}")
        code_data = ref.get()

        if not code_data or not isinstance(code_data, dict):
            return None

        now_ts = int(datetime.now(timezone.utc).timestamp())
        
        if code_data.get("used", False) or now_ts > code_data.get("expires_at", 0):
            # Cleanup expired or used code
            ref.delete()
            return None

        return code_data
    except Exception as e:
        logger.error(f"Error validating activation code {cleaned_code}: {e}")
        return None


def register_activated_device(
    activation_code: str,
    device_info: Dict[str, Any],
    bus_assignment: str,
    permissions: Dict[str, bool],
    client_ip: str = "unknown"
) -> Tuple[str, str]:
    """
    Validates code, burns it atomically, provisions the device node, and issues a SHA-256 hashed X-Device-Key.
    Returns tuple of (device_id, raw_device_key).
    """
    check_activation_rate_limit(f"activation_{client_ip}")
    cleaned_code = activation_code.strip()

    code_data = verify_activation_code(cleaned_code)
    if not code_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired activation code.",
        )

    device_id = f"BT-BUS-{str(bus_assignment).zfill(3)}"
    raw_device_key = f"bt_key_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_device_key.encode("utf-8")).hexdigest()

    device_payload = {
        "device_id": device_id,
        "serial_number": device_info.get("serial_number", f"SN-{bus_assignment}-GPS"),
        "model": device_info.get("model", "Telematics Unit"),
        "assigned_bus": bus_assignment,
        "bus_number": bus_assignment,
        "key_hash": key_hash,
        "status": "active",
        "permissions": {
            "location_access": permissions.get("location", True),
            "serial_sync": permissions.get("serial", True),
            "telemetry_access": permissions.get("telemetry", True),
            "remote_diagnostics": permissions.get("diagnostics", False)
        },
        "address": "Bulloch County Bus Garage, Statesboro, GA",
        "activated_at": datetime.now(timezone.utc).isoformat(),
        "last_seen": datetime.now(timezone.utc).isoformat(),
    }

    try:
        # Register in RTDB devices node
        rtdb.reference(f"devices/{device_id}").set(device_payload)

        # Register in Firestore devices collection for middleware authentication
        db.collection("devices").document(device_id).set({
            "device_id": device_id,
            "bus_number": bus_assignment,
            "key_hash": key_hash,
            "status": "active",
            "activated_at": datetime.now(timezone.utc).isoformat(),
            "last_seen": datetime.now(timezone.utc).isoformat(),
            "revoked_at": None,
        })

        # Burn activation code to prevent reuse
        rtdb.reference(f"activation_codes/{cleaned_code}").delete()

        logger.info(f"Successfully activated device {device_id} via code {cleaned_code}.")
        return device_id, raw_device_key

    except Exception as e:
        logger.error(f"Failed to register activated device {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete device registration.",
        )


def revoke_device(device_id: str, admin_uid: str) -> None:
    """
    Revokes device identity across both RTDB and Firestore.
    """
    try:
        revocation_data = {
            "status": "revoked",
            "revoked_at": datetime.now(timezone.utc).isoformat(),
            "revoked_by": admin_uid,
        }
        
        # Update RTDB
        rtdb.reference(f"devices/{device_id}").update(revocation_data)
        
        # Update Firestore
        db.collection("devices").document(device_id).update(revocation_data)
        
        logger.info(f"Device {device_id} revoked by admin UID {admin_uid}.")
    except Exception as e:
        logger.error(f"Failed to revoke device {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke device.",
        )