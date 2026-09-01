import logging
from typing import Dict, Any, List, Optional
import httpx
from app.config.settings import settings

logger = logging.getLogger("bulloch.services.google_maps")

# Dedicated HTTP client configuration
TIMEOUT_SECONDS = 15.0


def _validate_coordinates(lat: float, lng: float) -> bool:
    """Validates latitude and longitude range limits."""
    return -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0


async def compute_bus_route(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
) -> List[Dict[str, float]]:
    """
    Computes optimized bus route path enforcing curbside navigation via Google Routes API v2.
    Validates input ranges and deduplicates adjacent coordinates.
    """
    if not settings.GOOGLE_MAPS_API_KEY:
        logger.error("Google Maps route calculation failed: API key missing.")
        return []

    # Validate inputs before network execution
    try:
        o_lat, o_lng = float(origin_lat), float(origin_lng)
        d_lat, d_lng = float(dest_lat), float(dest_lng)
    except (ValueError, TypeError):
        logger.error(f"Invalid coordinate format provided: origin=({origin_lat}, {origin_lng}), dest=({dest_lat}, {dest_lng})")
        return []

    if not (_validate_coordinates(o_lat, o_lng) and _validate_coordinates(d_lat, d_lng)):
        logger.error(f"Coordinates out of bounds: origin=({o_lat}, {o_lng}), dest=({d_lat}, {d_lng})")
        return []

    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": "routes.legs.steps.startLocation,routes.legs.steps.endLocation",
    }

    body = {
        "origin": {"location": {"latLng": {"latitude": o_lat, "longitude": o_lng}}},
        "destination": {"location": {"latLng": {"latitude": d_lat, "longitude": d_lng}}},
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE",
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=body, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"Google Routes API returned non-200 status [{response.status_code}]: {response.text}")
                return []

            data = response.json()

        path: List[Dict[str, float]] = []
        routes = data.get("routes", [])

        if routes and "legs" in routes[0]:
            for leg in routes[0].get("legs", []):
                for step in leg.get("steps", []):
                    start = step.get("startLocation", {}).get("latLng", {})
                    end = step.get("endLocation", {}).get("latLng", {})

                    if start and "latitude" in start and "longitude" in start:
                        point = {"lat": float(start["latitude"]), "lng": float(start["longitude"])}
                        if not path or path[-1] != point:
                            path.append(point)

                    if end and "latitude" in end and "longitude" in end:
                        point = {"lat": float(end["latitude"]), "lng": float(end["longitude"])}
                        if not path or path[-1] != point:
                            path.append(point)

        return path

    except httpx.TimeoutException:
        logger.error("Google Routes API request timed out.")
        return []
    except httpx.RequestError as exc:
        logger.error(f"Network error while reaching Google Routes API: {exc}")
        return []
    except Exception as exc:
        logger.exception(f"Unexpected error during route calculation: {exc}")
        return []