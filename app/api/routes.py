# app/api/routes.py

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.services.google_maps import compute_bus_route
from app.middleware.auth import verify_firebase_token

router = APIRouter(tags=["Routes"])


class RouteCalculationRequest(BaseModel):
    origin_lat: float
    origin_lng: float
    dest_lat: float
    dest_lng: float


@router.post("/compute-route")
async def calculate_route(payload: RouteCalculationRequest, user=Depends(verify_firebase_token)):
    path = await compute_bus_route(
        payload.origin_lat, 
        payload.origin_lng, 
        payload.dest_lat, 
        payload.dest_lng
    )
    if not path:
        raise HTTPException(status_code=400, detail="Could not compute route path.")
    return {"status": "success", "path": path}