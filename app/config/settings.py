# app/config/settings.py

from typing import Dict, Any, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application Config
    APP_NAME: str = "Bulloch Transport System"
    ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "super-secret-key-change-in-production"

    # Firebase Client Credentials
    FIREBASE_API_KEY: str = ""
    FIREBASE_AUTH_DOMAIN: str = ""
    FIREBASE_PROJECT_ID: str = ""
    FIREBASE_STORAGE_BUCKET: str = ""
    FIREBASE_MESSAGING_SENDER_ID: str = ""
    FIREBASE_APP_ID: str = ""
    FIREBASE_DATABASE_URL: str = ""
    
    # Firebase Admin SDK
    FIREBASE_CREDENTIALS_PATH: str = "firebase_service_account.json"

    # Google Maps API
    GOOGLE_MAPS_API_KEY: str = ""
    OPENWEATHER_API_KEY: str = ""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def firebase_web_config(self) -> Dict[str, str]:
        """Returns the dictionary needed for client-side Firebase Auth JS SDK."""
        return {
            "apiKey": self.FIREBASE_API_KEY,
            "authDomain": self.FIREBASE_AUTH_DOMAIN,
            "projectId": self.FIREBASE_PROJECT_ID,
            "storageBucket": self.FIREBASE_STORAGE_BUCKET,
            "messagingSenderId": self.FIREBASE_MESSAGING_SENDER_ID,
            "appId": self.FIREBASE_APP_ID,
            "databaseURL": self.FIREBASE_DATABASE_URL,
        }


settings = Settings()