import logging
from functools import lru_cache
from typing import Optional
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

logger = logging.getLogger("bulloch.services.geocoding")

# Initialize Nominatim geocoder with specific app user-agent
geolocator = Nominatim(user_agent="bulloch_county_schools_transportation_v1")


def _validate_coordinates(lat: float, lng: float) -> bool:
    """Validates latitude and longitude range limits."""
    return -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0


@lru_cache(maxsize=1024)
def _cached_reverse_geocode(rounded_lat: float, rounded_lng: float) -> Optional[str]:
    """
    Executes reverse geocoding request with LRU caching based on 4-decimal-place rounded coordinates.
    4 decimal places provides ~11-meter precision.
    """
    try:
        location = geolocator.reverse((rounded_lat, rounded_lng), exactly_one=True, timeout=5)
        if not location or not location.raw.get("address"):
            return None

        addr = location.raw["address"]
        road = addr.get("road") or addr.get("pedestrian") or addr.get("suburb") or addr.get("neighbourhood")
        house_num = addr.get("house_number", "")

        if road:
            return f"{house_num} {road}".strip()

        # Fallback to initial segment of full address string
        full_addr = str(location.address or "")
        return full_addr.split(",")[0].strip() if full_addr else None

    except (GeocoderTimedOut, GeocoderServiceError) as e:
        logger.warning(f"Geocoding service unavailable for ({rounded_lat}, {rounded_lng}): {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected geocoding error for ({rounded_lat}, {rounded_lng}): {e}")
        return None


def get_street_name_from_coords(lat: float, lng: float) -> str:
    """
    Converts latitude and longitude into a street name or physical address.
    Utilizes coordinate caching and bounds validation with fallback formatting.
    """
    try:
        lat_val = float(lat)
        lng_val = float(lng)
    except (ValueError, TypeError):
        logger.error(f"Invalid coordinate types provided: lat={lat}, lng={lng}")
        return "Unknown Location"

    if not _validate_coordinates(lat_val, lng_val):
        logger.error(f"Coordinates out of physical bounds: ({lat_val}, {lng_val})")
        return f"{lat_val:.4f}, {lng_val:.4f}"

    # Round coordinates to 4 decimal places (~11 meters) to maximize cache hits
    rounded_lat = round(lat_val, 4)
    rounded_lng = round(lng_val, 4)

    street_name = _cached_reverse_geocode(rounded_lat, rounded_lng)

    if street_name:
        return street_name

    return f"{lat_val:.4f}, {lng_val:.4f}"