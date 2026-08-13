from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    DRIVER = "driver"
    ADMIN = "admin"
    DISPATCH = "dispatch"


class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: UserRole = UserRole.DRIVER
    picture: Optional[str] = None


class DriverProfile(UserBase):
    assigned_bus_id: Optional[str] = Field(default=None, description="Current assigned vehicle ID (e.g., BUS-104)")
    assigned_route_id: Optional[str] = Field(default=None, description="Active assigned route ID")
    is_on_duty: bool = False


class UserSession(BaseModel):
    user: UserBase
    auth_token: str
    last_login_utc: str