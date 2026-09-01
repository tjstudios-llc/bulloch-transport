import logging
from typing import Any, Dict, Optional
import httpx
from app.config.settings import settings

logger = logging.getLogger("bulloch.services.weather")

# Default coordinates: Bulloch County, GA
DEFAULT_LAT = 32.4488
DEFAULT_LON = -81.7832
TIMEOUT_SECONDS = 5.0


def _validate_coordinates(lat: float, lon: float) -> bool:
    """Validates latitude and longitude geographical limits."""
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0


def _safe_round(value: Any, default: int = 0) -> int:
    """Safely coerces and rounds numerical values, falling back to default on invalid inputs."""
    if value is None:
        return default
    try:
        return round(float(value))
    except (ValueError, TypeError):
        return default


async def fetch_current_weather(
    lat: float = DEFAULT_LAT, 
    lon: float = DEFAULT_LON
) -> Optional[Dict[str, Any]]:
    """
    Fetches real-time current weather metrics from OpenWeatherMap API v2.5.
    Returns temperature in Fahrenheit and speed in mph (units=imperial).
    """
    api_key = settings.OPENWEATHER_API_KEY
    if not api_key:
        logger.warning("OPENWEATHER_API_KEY is not configured in settings.")
        return None

    try:
        lat_val = float(lat)
        lon_val = float(lon)
    except (ValueError, TypeError):
        logger.error(f"Invalid coordinate format provided: lat={lat}, lon={lon}")
        return None

    if not _validate_coordinates(lat_val, lon_val):
        logger.error(f"Coordinates out of valid range: lat={lat_val}, lon={lon_val}")
        return None

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat_val,
        "lon": lon_val,
        "appid": api_key,
        "units": "imperial",  # Fahrenheit & mph
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.get(url, params=params)
            
            if response.status_code != 200:
                logger.error(
                    "OpenWeather API returned HTTP %s: %s", 
                    response.status_code, 
                    response.text[:200]
                )
                return None

            data = response.json()
            if not isinstance(data, dict):
                logger.error("Unexpected JSON response structure from OpenWeather API.")
                return None

            weather_list = data.get("weather")
            weather_item = weather_list[0] if isinstance(weather_list, list) and len(weather_list) > 0 else {}
            main_data = data.get("main") if isinstance(data.get("main"), dict) else {}
            wind_data = data.get("wind") if isinstance(data.get("wind"), dict) else {}

            icon_code = str(weather_item.get("icon", "01d"))

            return {
                "city": str(data.get("name") or "Bulloch County"),
                "temp": _safe_round(main_data.get("temp")),
                "feels_like": _safe_round(main_data.get("feels_like")),
                "temp_min": _safe_round(main_data.get("temp_min")),
                "temp_max": _safe_round(main_data.get("temp_max")),
                "humidity": _safe_round(main_data.get("humidity")),
                "wind_speed": _safe_round(wind_data.get("speed")),
                "condition": str(weather_item.get("main") or "Clear"),
                "description": str(weather_item.get("description") or "").title(),
                "icon_code": icon_code,
                "icon_url": f"https://openweathermap.org/img/wn/{icon_code}@2x.png",
            }

    except httpx.TimeoutException:
        logger.error("OpenWeather API request timed out.")
        return None
    except httpx.RequestError as exc:
        logger.error("Network error while reaching OpenWeather API: %s", exc)
        return None
    except Exception as exc:
        logger.exception("Unexpected error while fetching weather data: %s", exc)
        return None