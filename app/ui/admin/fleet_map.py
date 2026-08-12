# app/ui/admin/fleet_map.py

import logging
from nicegui import ui
from app.ui.admin.header import render_admin_header
from app.services.fleet import fetch_live_bus_locations

logger = logging.getLogger(__name__)


def render_admin_dashboard():
    """
    Central Fleet Oversight Console for Dispatchers with Live Firestore Sync.
    """
    # Unified Header Navigation Bar
    render_admin_header(active_page="map")

    with ui.column().classes('w-full p-6 bg-slate-100 min-h-screen gap-6'):
        
        # -------------------------------------------------------------
        # 1. PAGE HEADER
        # -------------------------------------------------------------
        with ui.column().classes('gap-0'):
            ui.label('Active Fleet Overview').classes('text-2xl font-bold text-slate-800')
            ui.label('Realtime GPS vehicle tracking and fleet statistics').classes('text-xs text-slate-500')

        # -------------------------------------------------------------
        # 2. FLEET STATISTICS CARDS
        # -------------------------------------------------------------
        with ui.row().classes('w-full gap-4'):
            with ui.card().classes('p-4 bg-white rounded-xl shadow border-l-4 border-blue-600 flex-1'):
                ui.label('Total Active Buses').classes('text-slate-500 text-sm')
                total_buses_label = ui.label('0').classes('text-3xl font-bold text-slate-800')

            with ui.card().classes('p-4 bg-white rounded-xl shadow border-l-4 border-green-600 flex-1'):
                ui.label('On-Time Routes').classes('text-slate-500 text-sm')
                on_time_label = ui.label('0').classes('text-3xl font-bold text-slate-800')

            with ui.card().classes('p-4 bg-white rounded-xl shadow border-l-4 border-red-600 flex-1'):
                ui.label('Alerts / Requests').classes('text-slate-500 text-sm')
                alerts_label = ui.label('0').classes('text-3xl font-bold text-slate-800')

        # -------------------------------------------------------------
        # 3. LIVE LEAFLET MAP TRACKER
        # -------------------------------------------------------------
        with ui.column().classes('w-full gap-2'):
            ui.label('Live GPS Fleet Tracker').classes('text-lg font-bold text-slate-700')
            leaflet_map = ui.leaflet(center=(32.4488, -81.7832), zoom=12).classes('w-full h-96 rounded-xl shadow')

        # Internal dictionary tracking active map markers by bus ID
        markers = {}

        def refresh_fleet_data():
            """
            Fetches live bus documents from Firestore, updates summary metrics,
            and syncs GPS marker positions on the Leaflet map.
            """
            buses = fetch_live_bus_locations()

            # Calculate live summary statistics
            total_active = len(buses)
            on_time = sum(
                1 for b in buses 
                if str(b.get('status', '')).lower() in ('on-time', 'active', 'on schedule')
            )
            alerts = sum(
                1 for b in buses 
                if b.get('has_alert', False) or str(b.get('status', '')).lower() in ('delayed', 'alert', 'emergency')
            )

            # Update Card Labels dynamically
            total_buses_label.set_text(str(total_active))
            on_time_label.set_text(str(on_time))
            alerts_label.set_text(str(alerts))

            # Sync Leaflet map markers with live coordinates
            for bus in buses:
                bus_id = str(bus.get('id', ''))
                lat = bus.get('latitude')
                lng = bus.get('longitude')

                if not bus_id or lat is None or lng is None:
                    continue

                if bus_id in markers:
                    markers[bus_id].move(lat, lng)
                else:
                    markers[bus_id] = leaflet_map.marker(latlng=(lat, lng))

        # Initial render data load
        refresh_fleet_data()

        # Poll non-blockingly every 3 seconds
        ui.timer(3.0, refresh_fleet_data)