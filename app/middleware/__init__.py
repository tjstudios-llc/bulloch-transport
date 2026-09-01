# app/middleware/auth.py

def determine_user_role(decoded_token: dict) -> str:
    """
    Determines user role from Firebase custom claims or session data.
    """
    if not isinstance(decoded_token, dict):
        return "driver"

    # Check custom claims or fall back to default role
    role = decoded_token.get("role") or decoded_token.get("user_role") or "driver"
    return str(role).lower().strip()