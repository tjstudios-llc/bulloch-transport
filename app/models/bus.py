from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class GeoLocation(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees.")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees.")
    heading_deg: Optional[float] = Field(None, ge=0.0, le=360.0, description="Vehicle heading in degrees.")
    speed_kph: Optional[float] = Field(None, ge=0.0, description="Current vehicle speed in kilometers per hour.")
    accuracy_meters: Optional[float] = Field(None, ge=0.0, description="GPS accuracy estimate in meters.")
    reported_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when location was reported."
    )


class BusStatus(BaseModel):
    bus_id: str = Field(..., min_length=1, description="Unique bus identifier.")
    route_id: Optional[str] = Field(None, description="Current assigned route identifier.")
    driver_id: Optional[str] = Field(None, description="Assigned driver identifier.")
    status: str = Field(..., description="Operational state of the bus.")
    location: GeoLocation = Field(..., description="Most recent vehicle location snapshot.")
    occupancy: Optional[int] = Field(None, ge=0, description="Number of passengers on board.")
    capacity: Optional[int] = Field(None, ge=0, description="Maximum passenger capacity.")
    fuel_level_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Fuel level percentage.")
    battery_level_pct: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="Battery level percentage for electric or hybrid vehicles."
    )
    is_serviceable: bool = Field(True, description="Whether this bus is currently in service.")
    next_stop_id: Optional[str] = Field(None, description="Identifier for the next scheduled stop.")
    estimated_arrival: Optional[datetime] = Field(None, description="Estimated arrival time at next stop.")
    last_reported: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when this status was last updated."
    )
    warnings: List[str] = Field(default_factory=list, description="Active warning messages for the bus.")
    metadata: Dict[str, str] = Field(default_factory=dict, description="Optional metadata for the bus status.")

    # --- Pydantic V2 Field Validators ---

    @field_validator("bus_id", mode="before")
    @classmethod
    def normalize_bus_id(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status_field(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("status", mode="after")
    @classmethod
    def validate_status_value(cls, value: str) -> str:
        normalized = value.lower()
        allowed = {"active", "idle", "delayed", "offline", "maintenance", "enroute"}
        if normalized not in allowed:
            raise ValueError(f"status must be one of {sorted(allowed)}")
        return normalized

    # --- Pydantic V2 Model Validator ---

    @model_validator(mode="after")
    def validate_bus_status_logic(self) -> BusStatus:
        # Occupancy vs Capacity check
        if self.occupancy is not None and self.capacity is not None:
            if self.occupancy > self.capacity:
                raise ValueError("occupancy cannot exceed capacity")

        # Arrival time check
        if self.estimated_arrival and self.last_reported:
            if self.estimated_arrival < self.last_reported:
                raise ValueError("estimated_arrival cannot be earlier than last_reported")

        return self