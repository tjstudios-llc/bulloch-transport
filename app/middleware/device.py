from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from app.config.settings import settings


device_header = APIKeyHeader(name="X-Device-ID", auto_error=False)


async def verify_device_id(device_id: str = Security(device_header)) -> str:
    """Verify that the request is coming from a registered bus device."""
    if not device_id:
        raise HTTPException(status_code=401, detail="Missing device identifier.")

    normalized_device_id = device_id.strip()
    if not normalized_device_id:
        raise HTTPException(status_code=401, detail="Invalid device identifier.")

    if settings.ENV == "production" and len(normalized_device_id) < 3:
        raise HTTPException(status_code=401, detail="Device identifier does not meet minimum validation requirements.")

    return normalized_device_id
