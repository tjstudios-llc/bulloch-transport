import os
import sys
import json
import base64
from typing import Dict, Any, List, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application Config
    APP_NAME: str = Field(
        default="Bulloch Transport System", validation_alias="APP_NAME"
    )
    ENV: str = Field(default="production", validation_alias="ENV")
    DEBUG: bool = Field(default=False, validation_alias="DEBUG")
    SECRET_KEY: str = Field(..., validation_alias="SECRET_KEY")

    # Firebase Client Credentials
    FIREBASE_API_KEY: str = Field(default="", validation_alias="FIREBASE_API_KEY")
    FIREBASE_AUTH_DOMAIN: str = Field(
        default="", validation_alias="FIREBASE_AUTH_DOMAIN"
    )
    FIREBASE_PROJECT_ID: str = Field(..., validation_alias="FIREBASE_PROJECT_ID")
    FIREBASE_STORAGE_BUCKET: str = Field(
        default="", validation_alias="FIREBASE_STORAGE_BUCKET"
    )
    FIREBASE_MESSAGING_SENDER_ID: str = Field(
        default="", validation_alias="FIREBASE_MESSAGING_SENDER_ID"
    )
    FIREBASE_APP_ID: str = Field(default="", validation_alias="FIREBASE_APP_ID")
    FIREBASE_DATABASE_URL: str = Field(
        default="", validation_alias="FIREBASE_DATABASE_URL"
    )

    # Firebase Admin SDK Options (Checked in priority order)
    FIREBASE_CREDENTIALS_BASE64: Optional[str] = Field(
        default=None, validation_alias="FIREBASE_CREDENTIALS_BASE64"
    )
    FIREBASE_CREDENTIALS_JSON: Optional[str] = Field(
        default=None, validation_alias="FIREBASE_CREDENTIALS_JSON"
    )
    FIREBASE_CREDENTIALS_PATH: Optional[str] = Field(
        default="/etc/bulloch/serviceAccountKey.json",
        validation_alias="FIREBASE_CREDENTIALS_PATH",
    )

    # External APIs
    GOOGLE_MAPS_API_KEY: str = Field(
        default="", validation_alias="GOOGLE_MAPS_API_KEY"
    )
    OPENWEATHER_API_KEY: str = Field(
        default="", validation_alias="OPENWEATHER_API_KEY"
    )

    # Security Settings
    ALLOWED_ORIGINS: Union[List[str], str] = Field(
        default=[
            "http://localhost:3000"
        ],
        validation_alias="ALLOWED_ORIGINS",
    )
    ACTIVATION_CODE_TTL_SECONDS: int = 900  # 15 Minutes

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        forbidden_defaults = [
            "secret",
            "changeme",
            "super-secret-key-change-in-production",
            "test",
            "12345",
            "development-secret",
            "reLw5O12yVv6BegtVToa5Ts3HGjSFsBun7EHNroGb2D",
        ]
        if not v or v.lower() in [f.lower() for f in forbidden_defaults] or len(v) < 32:
            raise ValueError(
                "FATAL: SECRET_KEY must be a cryptographically strong string of at least 32 characters and cannot match known defaults."
            )
        return v

    @field_validator("DEBUG")
    @classmethod
    def validate_debug_in_production(cls, v: bool) -> bool:
        env = os.getenv("ENV", "production")
        if env.lower() == "production" and v is True:
            raise ValueError("FATAL: DEBUG mode cannot be set to True in production.")
        return v

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return [item.strip() for item in v.split(",") if item.strip()]
        return v

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
        Resolves Firebase Admin credentials and returns a sanitized dictionary.
        Priority:
          1. FIREBASE_CREDENTIALS_BASE64
          2. FIREBASE_CREDENTIALS_JSON
          3. FIREBASE_CREDENTIALS_PATH
        """
        if self.FIREBASE_CREDENTIALS_BASE64 and self.FIREBASE_CREDENTIALS_BASE64.strip():
            b64_str = self.FIREBASE_CREDENTIALS_BASE64.strip()
            missing_padding = len(b64_str) % 4
            if missing_padding:
                b64_str += "=" * (4 - missing_padding)
            decoded_bytes = base64.b64decode(b64_str)
            cred_dict = json.loads(decoded_bytes.decode("utf-8"))
            return self._sanitize_private_key(cred_dict)

        if self.FIREBASE_CREDENTIALS_JSON and self.FIREBASE_CREDENTIALS_JSON.strip():
            cred_dict = json.loads(self.FIREBASE_CREDENTIALS_JSON.strip())
            return self._sanitize_private_key(cred_dict)

        if self.FIREBASE_CREDENTIALS_PATH and os.path.exists(
            self.FIREBASE_CREDENTIALS_PATH
        ):
            with open(
                self.FIREBASE_CREDENTIALS_PATH, "r", encoding="utf-8"
            ) as f:
                cred_dict = json.load(f)
            return self._sanitize_private_key(cred_dict)

        raise ValueError(
            f"No valid Firebase Admin SDK credentials found! Checked Base64, JSON string, and path: {self.FIREBASE_CREDENTIALS_PATH}"
        )

    @staticmethod
    def _sanitize_private_key(cred_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cleans carriage returns, replaces literal backslash escapes,
        and enforces trailing newlines required for Google OAuth RSA signatures.
        """
        if "private_key" in cred_dict and isinstance(
            cred_dict["private_key"], str
        ):
            key = cred_dict["private_key"]
            key = key.replace("\r", "")
            key = key.replace("\\n", "\n")
            cred_dict["private_key"] = key.strip() + "\n"
        return cred_dict


try:
    settings = Settings()
except Exception as e:
    sys.stderr.write(
        f"\n[CRITICAL CONFIGURATION ERROR] Startup aborted: {e}\n\n"
    )
    sys.exit(1)