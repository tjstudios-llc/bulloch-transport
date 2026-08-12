# app/services/geocoding.py

import logging
from typing import Optional
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

logger = logging.getLogger(__name__)

# Initialize Nominatim geocoder with a custom user agent
geolocator = Nominatim(user_agent="bulloch_county_schools_transport")


def get_street_name_from_coords(lat: float, lng: float) -> str:
    """
    Converts latitude and longitude into a street name or physical address.
    Returns the street address if found, otherwise falls back to lat/lng format.
    """
    try:
        location = geolocator.reverse((lat, lng), exactly_one=True, timeout=5)
        if location and location.raw.get("address"):
            addr = location.raw["address"]
            
            # Extract road name or fallback building/locality
            road = addr.get("road") or addr.get("pedestrian") or addr.get("suburb")
            house_num = addr.get("house_number", "")
            
            if road:
                return f"{house_num} {road}".strip()
            
            # Fallback to first line of full address
            return location.address.split(",")[0]
            
        return f"{lat:.4f}, {lng:.4f}"
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        logger.warning(f"Geocoding service timeout or error: {e}")
        return f"{lat:.4f}, {lng:.4f}"
    except Exception as e:
        logger.error(f"Unexpected geocoding error: {e}")
        return f"{lat:.4f}, {lng:.4f}"