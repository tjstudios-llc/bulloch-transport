import logging
from typing import Dict, Any
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth
from app.config.firebase import db
from app.models.user import UserRole

security = HTTPBearer(auto_error=True)
logger = logging.getLogger("bulloch.middleware.auth")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> Dict[str, Any]:
    """
    Verifies Firebase ID Token and loads authoritative server-side user identity
    and role from Firestore. Fails closed if token is revoked or user is unprovisioned.
    """
    token = credentials.credentials
    try:
        # Enforce revocation checks on Firebase ID tokens
        decoded_token = auth.verify_id_token(token, check_revoked=True)
    except Exception as e:
        logger.warning(f"Authentication failure: Invalid or expired Firebase ID token ({e})")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    uid = decoded_token.get("uid")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing valid identity claim.",
        )

    # Resolve authoritative role strictly from Firestore database (users/{uid})
    try:
        user_doc = db.collection("users").document(uid).get()
    except Exception as e:
        logger.error(f"Firestore database query failed for UID {uid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error verifying user authorization.",
        )

    if not user_doc.exists:
        logger.warning(f"Authorization rejected: Unprovisioned UID attempted access: {uid}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not provisioned in application directory.",
        )

    user_data = user_doc.to_dict() or {}

    # Account status check
    if not user_data.get("active", True):
        logger.warning(f"Authorization rejected: Inactive account UID: {uid}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive or disabled.",
        )

    # Derive role from database record
    db_role = user_data.get("role", "driver")
    admin_val = UserRole.ADMIN.value if hasattr(UserRole.ADMIN, "value") else "admin"
    driver_val = UserRole.DRIVER.value if hasattr(UserRole.DRIVER, "value") else "driver"

    role = db_role if db_role in [admin_val, driver_val, "admin", "driver"] else driver_val

    return {
        "uid": uid,
        "email": decoded_token.get("email", user_data.get("email", "")),
        "role": role,
        "assigned_bus": user_data.get("assigned_bus"),
        "active": user_data.get("active", True),
    }


async def verify_firebase_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> Dict[str, Any]:
    """
    Backward-compatible dependency for token verification.
    """
    return await get_current_user(credentials)


def require_authenticated_user(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    return current_user


def require_admin(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    admin_val = UserRole.ADMIN.value if hasattr(UserRole.ADMIN, "value") else "admin"
    if current_user.get("role") not in [admin_val, "admin"]:
        logger.warning(
            f"Authorization failure: Non-admin UID {current_user['uid']} attempted admin operation."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation requires explicit administrator privileges.",
        )
    return current_user


def require_driver(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    admin_val = UserRole.ADMIN.value if hasattr(UserRole.ADMIN, "value") else "admin"
    driver_val = UserRole.DRIVER.value if hasattr(UserRole.DRIVER, "value") else "driver"
    if current_user.get("role") not in [admin_val, driver_val, "admin", "driver"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation requires driver or administrator privileges.",
        )
    return current_user