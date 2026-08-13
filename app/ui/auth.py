# app/ui/auth.py

import json
import logging
from nicegui import app, ui
from app.config.settings import settings
from app.config.firebase import rtdb

logger = logging.getLogger(__name__)


def render_login_page():
    """
    Renders Google SSO Sign-In Page with Device Activation access
    and continuous background GPS location tracking.
    """
    firebase_cfg = json.dumps(settings.firebase_web_config)

    # -------------------------------------------------------------
    # 1. ALWAYS-ON LOCATION TRACKING SERVICE
    # -------------------------------------------------------------
    def sync_device_location(event):
        """Callback triggered from browser JS carrying live GPS coordinates."""
        try:
            data = event.args
            lat = data.get("lat")
            lng = data.get("lng")
            device_id = app.storage.user.get("device_id", "unassigned_device")

            if lat and lng:
                # Continuously update device location in Realtime Database
                rtdb.reference(f"devices/{device_id}").update({
                    "latitude": lat,
                    "longitude": lng,
                    "status": "Online",
                    "last_seen": "Just now"
                })
        except Exception as e:
            logger.error(f"Error updating device location: {e}")

    # Listen for location stream events from browser
    ui.on('gps_update', sync_device_location)

    # Inject Firebase JS SDKs & HTML5 Geolocation Watcher into head
    ui.add_head_html(f'''
        <script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js"></script>
        <script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-auth-compat.js"></script>
        <script>
            if ("geolocation" in navigator) {{
                navigator.geolocation.watchPosition(
                    (position) => {{
                        const lat = position.coords.latitude;
                        const lng = position.coords.longitude;
                        emitEvent('gps_update', {{ lat: lat, lng: lng }});
                    }},
                    (error) => {{
                        console.warn("GPS Location error: ", error.message);
                    }},
                    {{
                        enableHighAccuracy: true,
                        maximumAge: 0,
                        timeout: 5000
                    }}
                );
            }}
        </script>
    ''')

    # -------------------------------------------------------------
    # 2. LOGIN & DEVICE SETUP CARD
    # -------------------------------------------------------------
    with ui.card().classes('w-96 mx-auto mt-20 p-8 shadow-2xl rounded-2xl text-center bg-white flex flex-col gap-4'):
        ui.label('Bulloch Transport').classes('text-2xl font-extrabold text-slate-800')
        ui.label('Secure Google sign-in for fleet operations.').classes('text-sm text-slate-500 mb-2')

        # Google SSO OAuth Button
        ui.button('Sign in with Google', icon='login').classes(
            'w-full bg-blue-700 hover:bg-blue-600 text-white font-bold py-3 rounded-full shadow transition-all'
        ).on('click', js_handler=f'''
            () => {{
                if (!firebase.apps.length) {{
                    firebase.initializeApp({firebase_cfg});
                }}
                const provider = new firebase.auth.GoogleAuthProvider();
                firebase.auth().signInWithPopup(provider)
                    .then((result) => {{
                        const user = result.user;
                        fetch('/api/v1/auth/store-session', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{
                                name: user.displayName,
                                email: user.email,
                                picture: user.photoURL
                            }})
                        }}).then(res => {{
                            if (res.ok) window.location.href = '/';
                        }});
                    }})
                    .catch((err) => alert('Authentication failed: ' + err.message));
            }}
        ''')

        ui.separator().classes('my-2')

        # Hardware Device Activation Button (Isolated Public Route)
        with ui.column().classes('w-full items-center gap-2'):
            ui.label('Setting up bus hardware?').classes('text-xs text-slate-500')
            ui.button(
                '⚡ Activate Hardware Device', 
                on_click=lambda: ui.navigate.to('/device-setup')
            ).classes(
                'w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2.5 rounded-full shadow transition-all text-sm'
            )