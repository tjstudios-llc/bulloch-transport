from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class Location(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees.")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees.")


class RouteStop(BaseModel):
    stop_id: str = Field(..., min_length=1, description="Unique route stop identifier.")
    name: str = Field(..., min_length=1, description="Human-readable stop name.")
    location: Location = Field(..., description="GPS location for the stop.")
    sequence: int = Field(..., ge=1, description="Order of this stop within the route.")
    scheduled_time: Optional[datetime] = Field(None, description="Planned arrival time at this stop.")
    is_boarding: bool = Field(True, description="Whether passengers board at this stop.")
    is_active: bool = Field(True, description="Whether this stop is currently enabled.")
    notes: Optional[str] = Field(None, description="Optional driver notes for the stop.")

    @field_validator("stop_id", "name", mode="before")
    @classmethod
    def normalize_text_fields(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        note_text = str(value).strip()
        return note_text or None


class BusRoute(BaseModel):
    route_id: str = Field(..., min_length=1, description="Unique route identifier.")
    name: str = Field(..., min_length=1, description="Route display name.")
    description: Optional[str] = Field(None, description="Optional route description.")
    origin: Optional[str] = Field(None, description="Canonical route origin name.")
    destination: Optional[str] = Field(None, description="Canonical route destination name.")
    stops: List[RouteStop] = Field(default_factory=list, description="Ordered list of stops along the route.")
    active: bool = Field(True, description="Whether the route is active for use.")
    estimated_distance_km: Optional[float] = Field(None, ge=0.0, description="Estimated route distance in kilometers.")
    estimated_duration_minutes: Optional[float] = Field(None, ge=0.0, description="Estimated route duration in minutes.")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Route creation timestamp."
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Route last update timestamp."
    )
    metadata: Dict[str, str] = Field(default_factory=dict, description="Optional metadata for route tooling.")

    @field_validator("route_id", "name", mode="before")
    @classmethod
    def normalize_string_fields(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def validate_route_configuration(self) -> BusRoute:
        if not self.stops:
            raise ValueError("BusRoute must contain at least one RouteStop.")

        sequence_values = [stop.sequence for stop in self.stops]
        if sequence_values != sorted(sequence_values):
            raise ValueError("Route stops must be ordered by sequence.")

        if sequence_values != list(range(1, len(self.stops) + 1)):
            raise ValueError("Route stop sequence numbers must be consecutive starting at 1.")

        # Fallback for origin and destination if missing
        if not self.origin:
            self.origin = self.stops[0].name
        if not self.destination:
            self.destination = self.stops[-1].name

        if self.created_at and self.updated_at and self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be earlier than created_at.")

        return self


class UserSession(BaseModel):
    session_id: str = Field(..., min_length=1, description="Unique session identifier.")
    uid: str = Field(..., min_length=1, description="Firebase user UID.")
    email: Optional[str] = Field(None, description="User email address.")
    display_name: Optional[str] = Field(None, description="User display name.")
    role: str = Field("driver", description="Session role in the fleet management system.")
    route_id: Optional[str] = Field(None, description="Assigned route identifier.")
    bus_id: Optional[str] = Field(None, description="Assigned bus identifier.")
    login_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Session login timestamp."
    )
    last_active_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Most recent session activity timestamp."
    )
    device_id: Optional[str] = Field(None, description="Hardware device identifier for the session.")
    firebase_token: Optional[str] = Field(None, description="Optional Firebase auth token.")
    metadata: Dict[str, str] = Field(default_factory=dict, description="Additional session metadata.")

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("role must be a string")
        normalized = value.strip().lower()
        allowed_roles = {"driver", "admin", "dispatcher", "manager", "parent"}
        if normalized not in allowed_roles:
            raise ValueError(f"role must be one of {sorted(allowed_roles)}")
        return normalized

    @field_validator("email", "display_name", "route_id", "bus_id", "device_id", "firebase_token", mode="before")
    @classmethod
    def normalize_optional_strings(cls, value: Any) -> Optional[str]:
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned if cleaned else None
        return value