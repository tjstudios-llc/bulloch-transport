import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from app.config.firebase import db

logger = logging.getLogger("bulloch.middleware.device")

device_id_header = APIKeyHeader(name="X-Device-ID", auto_error=False)
device_key_header = APIKeyHeader(name="X-Device-Key", auto_error=False)


async def verify_device_credentials(
    x_device_id: str = Header(None, alias="X-Device-ID"),
    x_device_key: str = Header(None, alias="X-Device-Key"),
) -> Dict[str, Any]:
    """
    Verifies dual-header device credentials (X-Device-ID and X-Device-Key).
    Uses constant-time comparison against SHA-256 hashed secret keys stored in Firestore.
    Fails closed if device is missing, revoked, or key does not match.
    """
    if not x_device_id or not x_device_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Device authentication headers (X-Device-ID, X-Device-Key) required.",
        )

    device_id = x_device_id.strip()
    device_key = x_device_key.strip()

    if not device_id or not device_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid device authentication credentials.",
        )

    # Retrieve hardware registration record from Firestore
    try:
        device_ref = db.collection("devices").document(device_id)
        doc = device_ref.get()
    except Exception as e:
        logger.error(f"Firestore query error for device ID {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error verifying device authorization.",
        )

    if not doc.exists:
        logger.warning(
            f"Device authentication rejected: Unknown device ID '{device_id}'"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid device credentials.",
        )

    device_data = doc.to_dict() or {}

    # Verify device active status (fails closed if revoked or suspended)
    if device_data.get("status") != "active":
        logger.warning(
            f"Device authentication rejected for non-active device '{device_id}' (Status: {device_data.get('status')})"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device identity has been revoked, suspended, or not activated.",
        )

    # Constant-time comparison of SHA-256 key hash to prevent timing attacks
    stored_hash = device_data.get("key_hash", "")
    computed_hash = hashlib.sha256(device_key.encode("utf-8")).hexdigest()

    if not stored_hash or not hmac.compare_digest(stored_hash, computed_hash):
        logger.warning(
            f"Device key signature mismatch for device ID '{device_id}'"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid device credentials.",
        )

    # Record device heartbeat
    try:
        device_ref.update(
            {"last_seen": datetime.now(timezone.utc).isoformat()}
        )
    except Exception as e:
        logger.warning(f"Failed to update last_seen for device {device_id}: {e}")

    return device_data


async def verify_device_id(
    x_device_id: str = Security(device_id_header),
    x_device_key: str = Security(device_key_header),
) -> str:
    """
    Backward-compatible helper that enforces full dual-header credential verification
    and returns the verified device ID string.
    """
    device_data = await verify_device_credentials(
        x_device_id=x_device_id, x_device_key=x_device_key
    )
    return device_data.get("device_id", x_device_id)