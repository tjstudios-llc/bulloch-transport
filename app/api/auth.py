# app/api/auth.py

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from app.middleware.auth import determine_user_role

router = APIRouter(prefix="/auth", tags=["Authentication"])


class SessionPayload(BaseModel):
    name: str
    email: EmailStr
    picture: str | None = None


@router.post("/store-session")
async def store_session(payload: SessionPayload, request: Request):
    """Stores session data inside the encrypted session cookie."""
    try:
        role = determine_user_role(payload.email)
        role_value = role.value if hasattr(role, "value") else str(role)

        # Write directly to Starlette session cookie
        request.session["authenticated"] = True
        request.session["role"] = role_value
        request.session["user_role"] = role_value
        request.session["user"] = {
            "name": payload.name,
            "email": payload.email,
            "picture": payload.picture,
            "role": role_value,
        }

        return {
            "status": "success",
            "user": {
                "name": payload.name,
                "email": payload.email,
                "role": role_value,
                "picture": payload.picture,
            },
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to store user session: {str(exc)}"
        )


@router.post("/logout")
async def logout(request: Request):
    """Clears the session cookie."""
    try:
        request.session.clear()
    except Exception:
        pass

    return {"status": "success"}