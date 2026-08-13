# app/main.py

import logging
import multiprocessing
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from nicegui import app as nicegui_app, ui
import uvicorn

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.routes import router as routes_router
from app.config.firebase import init_firebase
from app.config.settings import settings
from app.ui.admin.fleet_map import render_admin_dashboard
from app.ui.admin.routes import render_admin_routes_page
from app.ui.admin.users import render_admin_users_page
from app.ui.admin.devices import render_admin_devices_page
from app.ui.device_setup import render_device_setup_page
from app.ui.admin.settings import render_admin_settings_page
from app.ui.auth import render_login_page
from app.ui.driver.dashboard import render_driver_dashboard
from app.ui.driver.maps import render_driver_maps_page

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("bulloch-transport")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Bulloch Transport System...")
    init_firebase()
    logger.info("System startup complete. NiceGUI & FastAPI ready.")
    yield
    logger.info("Shutting down Bulloch Transport System...")


app = FastAPI(
    title="Bulloch County Schools - Bus Navigation & Tracking API",
    version="1.0.0",
    lifespan=lifespan
)

# Enable Starlette Session Middleware
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(routes_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


def get_current_user_from_request(request: Request):
    try:
        session = request.session
        authenticated = bool(session.get("authenticated", False))
        
        role = session.get("role") or session.get("user_role")
        if not role and isinstance(session.get("user"), dict):
            role = session.get("user", {}).get("role")
            
        role_str = str(role).lower().strip() if role else ""
        return authenticated, role_str
    except Exception as exc:
        logger.warning("Failed to access request.session: %s", exc)
        return False, ""


# --- UI ROUTES ---

@ui.page('/')
def index_page(request: Request):
    authenticated, role = get_current_user_from_request(request)
    if not authenticated:
        ui.navigate.to('/login')
        return
    render_driver_dashboard(user_role=role)


# 🚌 Aliases for driver paths -> redirect directly to /driver/maps
@ui.page('/driver')
@ui.page('/driver/map')
@ui.page('/driver/route')
def driver_alias_page(request: Request):
    ui.navigate.to('/driver/maps')


# 🗺️ Driver Live Navigation Page
@ui.page('/driver/maps')
def driver_maps_route(request: Request):
    authenticated, role = get_current_user_from_request(request)
    if not authenticated:
        ui.navigate.to('/login')
        return
    render_driver_maps_page()


@ui.page('/login')
def login_page(request: Request):
    authenticated, role = get_current_user_from_request(request)
    if authenticated:
        if role in ("admin", "dispatch", "dispatcher"):
            ui.navigate.to('/admin')
        else:
            ui.navigate.to('/')
        return
    render_login_page()


@ui.page('/admin')
def admin_page(request: Request):
    authenticated, role = get_current_user_from_request(request)
    if not authenticated:
        ui.navigate.to('/login')
        return
    if role not in ("admin", "dispatch", "dispatcher"):
        ui.navigate.to('/')
        return
    render_admin_dashboard()


@ui.page('/admin/routes')
def admin_routes_page(request: Request):
    authenticated, role = get_current_user_from_request(request)
    if not authenticated or role not in ("admin", "dispatch", "dispatcher"):
        ui.navigate.to('/login')
        return
    render_admin_routes_page()

@ui.page('/admin/users')
def admin_users_page():
    render_admin_users_page()

@ui.page('/admin/devices')
def admin_devices_page():
    render_admin_devices_page()

@ui.page('/device-setup')
def device_setup_page():
    render_device_setup_page()
    
@ui.page('/admin/settings')
def admin_settings_page(request: Request):
    authenticated, role = get_current_user_from_request(request)
    if not authenticated or role not in ("admin", "dispatch", "dispatcher"):
        ui.navigate.to('/login')
        return
    render_admin_settings_page()


# ⚠️ Catch-all 404 Handler
@ui.page('/{path:path}')
def fallback_404_page(path: str):
    with ui.column().classes("w-full h-screen items-center justify-center bg-slate-900 text-white p-8 gap-4"):
        ui.icon("error_outline", size="64px").classes("text-amber-400")
        ui.label("Page Not Found (404)").classes("text-3xl font-bold")
        ui.label(f"The path standard '{path}' does not exist.").classes("text-slate-400")
        ui.button("Return to Dashboard", on_click=lambda: ui.navigate.to('/')).props("color=primary icon=arrow_back")


static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

ui.run_with(
    app,
    title="Bulloch Transport",
    storage_secret=settings.SECRET_KEY,
    favicon="🚌"
)


if __name__ == "__main__":
    if multiprocessing.get_start_method(allow_none=True) is None:
        multiprocessing.set_start_method("spawn", force=False)

    # Render dynamically assigns PORT environment variable
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    debug = os.environ.get("ENVIRONMENT", "production").lower() == "development"

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug
    )