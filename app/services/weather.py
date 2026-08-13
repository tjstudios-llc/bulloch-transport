# app/services/weather.py

import logging
from typing import Any, Dict, Optional
import httpx
from app.config.settings import settings

logger = logging.getLogger("bulloch-transport")

# Default coordinates: Bulloch County, GA
DEFAULT_LAT = 32.4488
DEFAULT_LON = -81.7832


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
        logger.warning("OPENWEATHER_API_KEY is not configured in environment.")
        return None

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "imperial",  # Fahrenheit & mph
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                weather_item = data.get("weather", [{}])[0]
                
                return {
                    "city": data.get("name", "Bulloch County"),
                    "temp": round(data.get("main", {}).get("temp", 0)),
                    "feels_like": round(data.get("main", {}).get("feels_like", 0)),
                    "temp_min": round(data.get("main", {}).get("temp_min", 0)),
                    "temp_max": round(data.get("main", {}).get("temp_max", 0)),
                    "humidity": data.get("main", {}).get("humidity", 0),
                    "wind_speed": round(data.get("wind", {}).get("speed", 0)),
                    "condition": weather_item.get("main", "Clear"),
                    "description": weather_item.get("description", "").title(),
                    "icon_code": weather_item.get("icon", "01d"),
                    "icon_url": f"https://openweathermap.org/img/wn/{weather_item.get('icon', '01d')}@2x.png",
                }
            
            logger.error("OpenWeather API Returned HTTP %s: %s", response.status_code, response.text)
            return None

    except Exception as exc:
        logger.error("Failed to fetch weather data: %s", exc)
        return None