# app/services/settings.py

from app.services.firebase import get_db_reference


def get_auto_approve_setting() -> bool:
    """Fetch the auto-approve setting from Firebase."""
    try:
        ref = get_db_reference("settings/auto_approve_routes")
        value = ref.get()
        return bool(value) if value is not None else False
    except Exception:
        return False


def set_auto_approve_setting(enabled: bool) -> None:
    """Update the auto-approve setting in Firebase."""
    try:
        ref = get_db_reference("settings/auto_approve_routes")
        ref.set(enabled)
    except Exception as e:
        print(f"Error updating auto-approve setting: {e}")