# app/services/google_maps.py

import httpx
import logging
from typing import Dict, Any, List
from app.config.settings import settings

logger = logging.getLogger("bulloch-transport.maps")


async def compute_bus_route(origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float) -> List[Dict[str, float]]:
    """
    Async computation of bus routes enforcing curbside drops using Google Routes API v2.
    """
    if not settings.GOOGLE_MAPS_API_KEY:
        logger.error("Google Maps API key is missing.")
        return []

    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": "routes.legs.steps.startLocation,routes.legs.steps.endLocation"
    }

    body = {
        "origin": {"location": {"latLng": {"latitude": origin_lat, "longitude": origin_lng}}},
        "destination": {"location": {"latLng": {"latitude": dest_lat, "longitude": dest_lng}}},
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE"
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(url, json=body, headers=headers)
            response.raise_for_status()
            data = response.json()

            path = []
            routes = data.get("routes", [])
            if routes and "legs" in routes[0]:
                for step in routes[0]["legs"][0].get("steps", []):
                    start = step.get("startLocation", {}).get("latLng", {})
                    end = step.get("endLocation", {}).get("latLng", {})
                    if start:
                        path.append({"lat": start.get("latitude"), "lng": start.get("longitude")})
                    if end:
                        path.append({"lat": end.get("latitude"), "lng": end.get("longitude")})
            return path

        except Exception as e:
            logger.error(f"Failed to calculate route from Google API: {e}")
            return []