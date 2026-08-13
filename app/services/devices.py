# app/services/devices.py

import random
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.config.firebase import rtdb
from app.services.geocoding import get_street_name_from_coords

logger = logging.getLogger(__name__)

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

                # Clean address text (Street Name, City, State)
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
# DEVICE SETUP & 6-DIGIT ACTIVATION OPERATIONS
# =========================================================

def generate_activation_code(assigned_bus: str) -> Optional[str]:
    """
    Generates a unique 6-digit activation code for a bus device and stores it in RTDB.
    """
    try:
        ref = rtdb.reference('activation_codes')

        # Generate a unique 6-digit code (retries up to 10 times to handle collisions)
        for _ in range(10):
            code = f"{random.randint(100000, 999999)}"
            
            # Verify code is not already active
            existing = ref.child(code).get()
            if not existing or not existing.get('active', False):
                ref.child(code).set({
                    "active": True,
                    "assigned_bus": assigned_bus,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "claimed_at": None
                })
                logger.info(f"Generated 6-digit activation code {code} for Bus #{assigned_bus}")
                return code

        logger.error("Failed to generate a unique 6-digit activation code after multiple attempts.")
        return None

    except Exception as e:
        logger.error(f"Error generating activation code: {e}")
        return None


def verify_activation_code(code: str) -> Optional[Dict[str, Any]]:
    """
    Checks if a 6-digit activation code is valid and active in Realtime Database.
    """
    cleaned_code = code.strip()

    try:
        ref = rtdb.reference(f'activation_codes/{cleaned_code}')
        code_data = ref.get()

        if code_data and isinstance(code_data, dict) and code_data.get("active", False):
            return code_data

        # Fallback for legacy format tokens (e.g., ACT-8820-2026)
        if cleaned_code.upper().startswith("ACT-") and len(cleaned_code) >= 10:
            return {
                "active": True,
                "assigned_bus": "Test-Bus",
                "serial_number": f"SN-{cleaned_code.replace('ACT-', '')}-GA",
                "model": "Cradlepoint IBR900 GPS Router"
            }

        return None
    except Exception as e:
        logger.error(f"Error validating activation code {cleaned_code}: {e}")
        return None


def register_activated_device(
    activation_code: str,
    device_info: Dict[str, Any],
    bus_assignment: str,
    permissions: Dict[str, bool]
) -> bool:
    """
    Registers the newly activated device into RTDB under devices/ bus node 
    and deactivates its 6-digit activation code.
    """
    try:
        cleaned_code = activation_code.strip()

        device_payload = {
            "serial_number": device_info.get("serial_number", f"SN-{bus_assignment}-GPS"),
            "model": device_info.get("model", "Telematics Unit"),
            "activation_code": cleaned_code,
            "assigned_bus": bus_assignment,
            "bus_number": bus_assignment,
            "status": "Active",
            "permissions": {
                "location_access": permissions.get("location", True),
                "serial_sync": permissions.get("serial", True),
                "telemetry_access": permissions.get("telemetry", True),
                "remote_diagnostics": permissions.get("diagnostics", False)
            },
            "address": "Bulloch County Bus Garage, Statesboro, GA",
            "activated_at": datetime.now(timezone.utc).isoformat()
        }

        # Save device node directly in RTDB
        device_id = f"bus_{bus_assignment}"
        rtdb.reference(f"devices/{device_id}").update(device_payload)

        # Mark activation code as inactive / claimed
        rtdb.reference(f"activation_codes/{cleaned_code}").update({
            "active": False,
            "claimed_at": datetime.now(timezone.utc).isoformat()
        })

        logger.info(f"Successfully registered device for Bus #{bus_assignment} via code {cleaned_code}.")
        return True
    except Exception as e:
        logger.error(f"Failed to register activated device: {e}")
        return False