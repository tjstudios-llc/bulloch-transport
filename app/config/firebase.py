# app/config/firebase.py

import os
import logging
import firebase_admin
from firebase_admin import credentials, firestore, db as realtime_db
from app.config.settings import settings

logger = logging.getLogger("bulloch-transport.firebase")

_firebase_app = None


def init_firebase() -> firebase_admin.App:
    """
    Initializes the Firebase Admin SDK using local service account credentials
    and settings configuration.
    """
    global _firebase_app

    if _firebase_app or firebase_admin._apps:
        _firebase_app = firebase_admin.get_app()
        return _firebase_app

    cred_path = settings.FIREBASE_CREDENTIALS_PATH

    options = {}
    if hasattr(settings, 'FIREBASE_DATABASE_URL') and settings.FIREBASE_DATABASE_URL:
        options['databaseURL'] = settings.FIREBASE_DATABASE_URL

    if os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        _firebase_app = firebase_admin.initialize_app(cred, options if options else None)
        logger.info("Firebase Admin SDK initialized successfully with service account.")
    else:
        logger.warning(
            f"Firebase service account file not found at '{cred_path}'. "
            "Initializing with default credentials (check environment)."
        )
        try:
            _firebase_app = firebase_admin.initialize_app(options=options if options else None)
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
            raise e

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