import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from app.middleware.auth import require_authenticated_user
from app.services.google_maps import compute_bus_route

router = APIRouter(prefix="/routes", tags=["Routes"])
logger = logging.getLogger("bulloch.api.routes")


class RouteCalculationRequest(BaseModel):
    origin_lat: float = Field(..., ge=-90.0, le=90.0, description="Origin latitude (-90 to 90)")
    origin_lng: float = Field(..., ge=-180.0, le=180.0, description="Origin longitude (-180 to 180)")
    dest_lat: float = Field(..., ge=-90.0, le=90.0, description="Destination latitude (-90 to 90)")
    dest_lng: float = Field(..., ge=-180.0, le=180.0, description="Destination longitude (-180 to 180)")


class RouteCalculationResponse(BaseModel):
    status: str
    path: List[Dict[str, Any]]


@router.post("/compute-route", response_model=RouteCalculationResponse)
async def calculate_route(
    payload: RouteCalculationRequest,
    current_user: Dict[str, Any] = Depends(require_authenticated_user),
):
    """
    Computes an optimized bus route path between origin and destination coordinates.
    Requires an authenticated user session.
    """
    try:
        path = await compute_bus_route(
            payload.origin_lat,
            payload.origin_lng,
            payload.dest_lat,
            payload.dest_lng,
        )
    except Exception as e:
        logger.error(f"Error invoking route calculation service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate route due to an internal service error.",
        )

    if not path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not compute route path for the provided coordinates.",
        )

    return RouteCalculationResponse(status="success", path=path)