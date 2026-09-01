import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from firebase_admin import auth
from app.config.firebase import db
from app.config.settings import settings
from app.models.user import UserRole

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger("bulloch.api.auth")


class SessionTokenPayload(BaseModel):
    # Accepts both 'idToken' from frontend JS and 'id_token' from backend calls
    id_token: str = Field(..., alias="idToken")

    model_config = ConfigDict(populate_by_name=True)


@router.post("/store-session")
async def store_session(payload: SessionTokenPayload, request: Request):
    """
    Verifies incoming Firebase ID Token server-side and checks user provisioned
    status/role in Firestore before establishing an encrypted session cookie.
    """
    token_str = payload.id_token.strip() if payload.id_token else ""
    if not token_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Firebase ID token required.",
        )

    # 1. Cryptographically verify the Firebase ID token
    try:
        # Note: check_revoked=False prevents service-account network overhead if key credentials are degraded
        decoded_token = auth.verify_id_token(token_str, check_revoked=False)
    except Exception as e:
        logger.error(f"Session creation failed during ID token verification: {e}", exc_info=True)
        
        # Include detailed error in dev mode to identify configuration mismatches
        error_detail = f"Token verification failed: {e}" if settings.ENV.lower() != "production" else "Invalid or expired authentication token."
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_detail,
        )

    uid = decoded_token.get("uid")
    email = decoded_token.get("email", "")

    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing valid identity claim.",
        )

    # 2. Query Firestore for authoritative user record and role
    try:
        user_doc = db.collection("users").document(uid).get()
    except Exception as e:
        logger.error(f"Firestore database query failed during session creation for UID {uid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify authorization state.",
        )

    if not user_doc.exists:
        logger.warning(f"Session establishment rejected: Unprovisioned UID {uid} ({email})")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account '{email}' is not provisioned in application directory.",
        )

    user_data = user_doc.to_dict() or {}

    # 3. Check account activation status
    if not user_data.get("active", True):
        logger.warning(f"Session establishment rejected: Inactive UID {uid}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive or disabled.",
        )

    # Resolve normalized role string
    db_role = str(user_data.get("role", "driver")).lower().strip()
    admin_val = UserRole.ADMIN.value if hasattr(UserRole.ADMIN, "value") else "admin"
    driver_val = UserRole.DRIVER.value if hasattr(UserRole.DRIVER, "value") else "driver"
    role_value = db_role if db_role in [admin_val, driver_val, "admin", "dispatch", "dispatcher"] else driver_val

    user_payload = {
        "uid": uid,
        "name": user_data.get("name") or decoded_token.get("name", "User"),
        "email": email or user_data.get("email", ""),
        "picture": decoded_token.get("picture") or user_data.get("picture"),
        "role": role_value,
        "assigned_bus": user_data.get("assigned_bus"),
    }

    # 4. Write verified state directly into Starlette encrypted session cookie
    request.session["authenticated"] = True
    request.session["uid"] = uid
    request.session["role"] = role_value
    request.session["user_role"] = role_value
    request.session["user"] = user_payload

    logger.info(f"Established authenticated session for UID {uid} ({email}) with role '{role_value}'")

    return {
        "status": "success",
        "user": user_payload,
    }


@router.post("/logout")
async def logout(request: Request):
    """Clears the encrypted session cookie."""
    try:
        request.session.clear()
    except Exception as e:
        logger.warning(f"Error clearing request session: {e}")

    return {"status": "success"}