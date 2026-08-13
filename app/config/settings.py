import os
import base64
import json
from typing import Dict, Any, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application Config
    APP_NAME: str = "Bulloch Transport System"
    ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "reLw5O12yVv6BegtVToa5Ts3HGjSFsBun7EHNroGb2D"

    # Firebase Client Credentials
    FIREBASE_API_KEY: str = ""
    FIREBASE_AUTH_DOMAIN: str = ""
    FIREBASE_PROJECT_ID: str = ""
    FIREBASE_STORAGE_BUCKET: str = ""
    FIREBASE_MESSAGING_SENDER_ID: str = ""
    FIREBASE_APP_ID: str = ""
    FIREBASE_DATABASE_URL: str = ""
    
    # Firebase Admin SDK Options (Checked in priority order)
    FIREBASE_CREDENTIALS_BASE64: Optional[str] = None
    FIREBASE_CREDENTIALS_JSON: Optional[str] = None
    FIREBASE_CREDENTIALS_PATH: Optional[str] = "firebase_config.json"

    # External APIs
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

    @property
    def firebase_admin_credentials(self) -> Dict[str, Any]:
        """
        Resolves Firebase Admin credentials and always returns a sanitized dictionary.
        Priority:
          1. FIREBASE_CREDENTIALS_BASE64 (Best for Render/Cloud)
          2. FIREBASE_CREDENTIALS_JSON (Raw JSON string)
          3. FIREBASE_CREDENTIALS_PATH (Local file path fallback)
        """
        # 1. Base64 String
        if self.FIREBASE_CREDENTIALS_BASE64:
            decoded_bytes = base64.b64decode(self.FIREBASE_CREDENTIALS_BASE64)
            cred_dict = json.loads(decoded_bytes.decode("utf-8"))
            return self._sanitize_private_key(cred_dict)

        # 2. Raw JSON String
        if self.FIREBASE_CREDENTIALS_JSON:
            cred_dict = json.loads(self.FIREBASE_CREDENTIALS_JSON)
            return self._sanitize_private_key(cred_dict)

        # 3. File Path Fallback (Read & sanitize directly)
        if self.FIREBASE_CREDENTIALS_PATH and os.path.exists(self.FIREBASE_CREDENTIALS_PATH):
            with open(self.FIREBASE_CREDENTIALS_PATH, "r", encoding="utf-8") as f:
                cred_dict = json.load(f)
            return self._sanitize_private_key(cred_dict)

        raise ValueError(
            f"No valid Firebase Admin SDK credentials found! Checked Base64, JSON string, and path: {self.FIREBASE_CREDENTIALS_PATH}"
        )

    @staticmethod
    def _sanitize_private_key(cred_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Replaces literal '\\n' backslash escapes with actual newline characters."""
        if "private_key" in cred_dict and isinstance(cred_dict["private_key"], str):
            cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
        return cred_dict


settings = Settings()