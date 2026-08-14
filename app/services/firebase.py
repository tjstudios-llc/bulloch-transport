import os
import logging
import firebase_admin
from firebase_admin import credentials, firestore, db as realtime_db
from app.config.settings import settings

logger = logging.getLogger("bulloch-transport.firebase")

_firebase_app = None


def init_firebase() -> firebase_admin.App:
    """
    Initializes the Firebase Admin SDK using credentials resolved from settings
    (Base64 env var, raw JSON string, or local file path).
    """
    global _firebase_app

    if _firebase_app or firebase_admin._apps:
        _firebase_app = firebase_admin.get_app()
        return _firebase_app

    options = {}
    if getattr(settings, "FIREBASE_DATABASE_URL", None):
        options["databaseURL"] = settings.FIREBASE_DATABASE_URL

    try:
        # Retrieve resolved credentials (returns a sanitized dict OR a path string)
        cred_source = settings.firebase_admin_credentials

        # If cred_source is a file path string, ensure the file actually exists
        if isinstance(cred_source, str) and not os.path.exists(cred_source):
            raise FileNotFoundError(f"Firebase credentials file not found at path '{cred_source}'")

        # credentials.Certificate handles both dictionary input and path string input
        cred = credentials.Certificate(cred_source)
        _firebase_app = firebase_admin.initialize_app(cred, options if options else None)
        logger.info("Firebase Admin SDK initialized successfully.")

    except Exception as e:
        logger.warning(
            f"Failed to initialize Firebase with configured credentials ({e}). "
            "Attempting initialization with Application Default Credentials..."
        )
        try:
            _firebase_app = firebase_admin.initialize_app(options=options if options else None)
            logger.info("Firebase Admin SDK initialized with Application Default Credentials.")
        except Exception as fallback_error:
            logger.error(f"Failed to initialize Firebase Admin SDK: {fallback_error}")
            raise fallback_error

    return _firebase_app


def get_firestore_db():
    """
    Helper function to retrieve the Cloud Firestore client instance.
    """
    if not firebase_admin._apps:
        init_firebase()
    return firestore.client()


def get_db_reference(path: str = "/"):
    """
    Helper function to retrieve a Firebase Realtime Database reference.
    """
    if not firebase_admin._apps:
        init_firebase()
    return realtime_db.reference(path)


# Ensure SDK initialization on import
init_firebase()

# Export Realtime Database module reference for services (e.g., rtdb.reference(...))
rtdb = realtime_db

# Export Firestore instance for backward compatibility across other services
db = get_firestore_db()