from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.middleware.auth import verify_firebase_token

router = APIRouter(prefix="/admin", tags=["Admin"])


class HealthCheckResponse(BaseModel):
    status: str
    uptime: str


@router.get("/health", response_model=HealthCheckResponse)
async def admin_health_check(user=Depends(verify_firebase_token)):
    return {"status": "ok", "uptime": "unknown"}
