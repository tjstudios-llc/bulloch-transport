import logging
import os
import sys
from typing import Optional

import firebase_admin
from firebase_admin import credentials, db as realtime_db, firestore
from app.config.settings import settings

logger = logging.getLogger("bulloch.config.firebase")

_firebase_app: Optional[firebase_admin.App] = None


def init_firebase() -> firebase_admin.App:
    """
    Initializes the Firebase Admin SDK using credentials resolved from settings.
    Enforces fail-closed credential verification in production environments.
    """
    global _firebase_app

    if firebase_admin._apps:
        _firebase_app = firebase_admin.get_app()
        return _firebase_app

    options = {}
    if getattr(settings, "FIREBASE_PROJECT_ID", None):
        options["projectId"] = settings.FIREBASE_PROJECT_ID
    if getattr(settings, "FIREBASE_DATABASE_URL", None):
        options["databaseURL"] = settings.FIREBASE_DATABASE_URL

    try:
        # Retrieve resolved credentials (dict or path string)
        cred_source = settings.firebase_admin_credentials

        if isinstance(cred_source, str) and not os.path.exists(cred_source):
            raise FileNotFoundError(
                f"Firebase credentials file not found at path '{cred_source}'"
            )

        # Initialize Certificate with dictionary or path
        cred = credentials.Certificate(cred_source)
        _firebase_app = firebase_admin.initialize_app(
            cred, options if options else None
        )
        logger.info("Firebase Admin SDK initialized successfully.")
        return _firebase_app

    except Exception as e:
        logger.critical(
            f"Failed to initialize Firebase Admin SDK with configured credentials: {e}"
        )
        if settings.ENV.lower() == "production":
            sys.stderr.write(
                f"\n[CRITICAL FIREBASE ERROR] Production credential failure: {e}\n\n"
            )
            raise e

        # Fallback to Application Default Credentials (ADC) for local/dev only
        logger.warning(
            "Attempting fallback initialization with Application Default Credentials (Non-Production)..."
        )
        try:
            _firebase_app = firebase_admin.initialize_app(
                options=options if options else None
            )
            logger.info(
                "Firebase Admin SDK initialized with Application Default Credentials."
            )
            return _firebase_app
        except Exception as fallback_error:
            logger.critical(
                f"Failed to initialize Firebase Admin SDK fallback: {fallback_error}"
            )
            raise fallback_error


def get_firestore_db() -> firestore.firestore.Client:
    """Retrieves the Cloud Firestore client instance."""
    if not firebase_admin._apps:
        init_firebase()
    return firestore.client()


def get_db_reference(path: str = "/"):
    """Retrieves a Firebase Realtime Database reference."""
    if not firebase_admin._apps:
        init_firebase()
    return realtime_db.reference(path)


# Ensure SDK initialization on import
init_firebase()

# Module exports
rtdb = realtime_db
db = get_firestore_db()