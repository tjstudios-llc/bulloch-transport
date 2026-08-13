from app.api.auth import router as auth_router
from app.api.routes import router as routes_router
from app.api.admin import router as admin_router

__all__ = ["auth_router", "routes_router", "admin_router"]