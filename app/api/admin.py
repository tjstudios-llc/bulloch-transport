import time
import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from app.middleware.auth import require_admin
from app.config.firebase import db, rtdb

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = logging.getLogger("bulloch.api.admin")

# Record server startup timestamp for uptime calculations
START_TIME = time.time()


class HealthCheckResponse(BaseModel):
    status: str
    uptime: str
    services: Dict[str, str]


def _get_formatted_uptime() -> str:
    """Calculates formatted uptime duration since process initialization."""
    seconds = int(time.time() - START_TIME)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or days > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or hours > 0 or days > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")

    return " ".join(parts)


@router.get("/health", response_model=HealthCheckResponse)
async def admin_health_check(
    admin_user: Dict[str, Any] = Depends(require_admin),
):
    """
    Returns system health status, active database connection checks, and application uptime.
    Requires administrator privileges.
    """
    firestore_status = "ok"
    rtdb_status = "ok"

    # Probe Firestore connection
    try:
        db.collection("users").limit(1).get()
    except Exception as e:
        logger.error(f"Admin health check - Firestore probe failed: {e}")
        firestore_status = "error"

    # Probe Realtime Database connection
    try:
        rtdb.reference("health_check").get()
    except Exception as e:
        logger.error(f"Admin health check - RTDB probe failed: {e}")
        rtdb_status = "error"

    overall_status = (
        "ok" if firestore_status == "ok" and rtdb_status == "ok" else "degraded"
    )

    return HealthCheckResponse(
        status=overall_status,
        uptime=_get_formatted_uptime(),
        services={
            "firestore": firestore_status,
            "realtime_database": rtdb_status,
        },
    )