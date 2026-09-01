import logging
from typing import Any, Dict, Optional
from app.config.firebase import rtdb

logger = logging.getLogger("bulloch.services.settings")

DEFAULT_AUTO_APPROVE: bool = False


def get_auto_approve_setting() -> bool:
    """
    Fetches the auto-approve route setting from Firebase Realtime Database.
    Falls back to safe default (False) on database or connectivity failures.
    """
    try:
        ref = rtdb.reference("settings/auto_approve_routes")
        value = ref.get()

        if value is None:
            return DEFAULT_AUTO_APPROVE

        return bool(value)

    except Exception as e:
        logger.error(f"Error fetching auto-approve setting from RTDB: {e}")
        return DEFAULT_AUTO_APPROVE


def set_auto_approve_setting(enabled: bool) -> bool:
    """
    Updates the auto-approve setting in Firebase Realtime Database.
    Validates parameter types and returns boolean execution status.
    """
    if not isinstance(enabled, bool):
        logger.error(f"Invalid payload type for auto-approve setting: expected bool, got {type(enabled)}")
        return False

    try:
        ref = rtdb.reference("settings/auto_approve_routes")
        ref.set(enabled)
        logger.info(f"Successfully updated auto_approve_routes setting to: {enabled}")
        return True

    except Exception as e:
        logger.error(f"Failed to update auto-approve setting in RTDB: {e}")
        return False