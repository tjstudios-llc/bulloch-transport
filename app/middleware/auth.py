# app/middleware/auth.py

from typing import Set
from fastapi import Request, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth
from app.models.user import UserRole

security = HTTPBearer()

# Explicit whitelist of administrator email addresses
ADMIN_EMAILS: Set[str] = {
    "tjrobinson476@gmail.com",
    # Add additional admin emails here as needed
}


def determine_user_role(email: str) -> UserRole:
    """
    Determines user role based on admin whitelist, email keywords, or domain mapping.
    """
    email_lower = email.lower().strip()
    
    if (
        email_lower in ADMIN_EMAILS
        or "admin" in email_lower
        or email_lower.endswith("@bullochschools.org")
    ):
        return UserRole.ADMIN
        
    return UserRole.DRIVER


async def verify_firebase_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """
    Validates incoming Firebase Bearer ID Tokens.
    """
    token = credentials.credentials
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired authentication token.")