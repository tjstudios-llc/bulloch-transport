# app/ui/driver/dashboard.py

import math
from datetime import datetime, timedelta
from nicegui import ui
from app.services.tts import announce_route_status
from app.ui.driver.weather_widget import render_driver_weather_widget
from app.services.routes import (
    fetch_active_route_for_bus,
    send_emergency_sos,
)
from app.services.firebase import get_db_reference

# CartoDB Dark Matter Config for Waze-like Dark Navigation Mode
CARTO_DARK_URL = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
CARTO_DARK_OPTIONS = {
    'maxZoom': 19,
    'attribution': '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
    'subdomains': 'abcd',
}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates distance in miles between two coordinate points."""
    R = 3958.8  # Earth radius in miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def render_driver_dashboard(user_role: str = "driver", bus_number: str = "", driver_name: str = "Driver"):
    """
    1024x600 Touchscreen CarPlay/Waze HUD for Bus Drivers & Driving Admins.
    Features 5-second animated splash screen, real-time GPS speed, live turn-by-turn HUD, 
    and full map expansion.
    """
    ui.colors(primary='#103f73', secondary='#2f73c7', positive='#148560')

    is_admin = user_role in ("admin", "dispatch", "dispatcher")

    # Fetch active route data from Firestore
    active_route = fetch_active_route_for_bus(bus_number=bus_number)

    # Extract dynamic properties with fallbacks
    route_id = active_route["id"] if active_route else None
    route_name = active_route.get("name", "No Active Route Assigned") if active_route else "No Active Route Assigned"
    assigned_bus = active_route.get("assigned_bus", bus_number) if active_route else bus_number
    stops = active_route.get("stops", []) if active_route else []

    current_stop_idx = 0
    current_lat = stops[0]["lat"] if stops else 32.4487
    current_lng = stops[0]["lng"] if stops else -81.7831

    # =========================================================
    # 1. 5-SECOND WELCOME ANIMATION OVERLAY
    # =========================================================
    welcome_overlay = ui.column().classes(
        'fixed inset-0 z-[2000] bg-slate-950 text-white flex flex-col items-center justify-center '
        'transition-opacity duration-1000 ease-out p-6 text-center'
    )

    with welcome_overlay:
        ui.icon('directions_bus', size='72px').classes('text-blue-400 animate-bounce mb-2')
        ui.label(f"Welcome, {driver_name}!").classes('text-3xl font-black tracking-wide text-white')
        ui.label(f"Bus #{assigned_bus or 'N/A'} • Route Navigation Ready").classes('text-sm text-blue-400 font-semibold tracking-wider mt-1')
        
        with ui.row().classes('items-center gap-2 mt-6 bg-slate-900/80 px-4 py-2 rounded-full border border-slate-800'):
            ui.spinner('dots', size='md', color='blue')
            ui.label('Calibrating Real-Time GPS & Navigation...').classes('text-xs text-slate-400 italic')

    def dismiss_welcome():
        welcome_overlay.classes(remove='opacity-100', add='opacity-0 pointer-events-none')
        ui.timer(1.0, lambda: welcome_overlay.set_visibility(False), once=True)

    ui.timer(5.0, dismiss_welcome, once=True)

    # =========================================================
    # DIALOGS: FULLSCREEN MAP & ROUTE REQUEST
    # =========================================================
    with ui.dialog().classes('w-full h-full') as map_dialog, ui.card().classes('w-full h-full max-w-none max-h-none p-0 bg-slate-900 flex flex-col rounded-none relative'):
        
        # Expanded Map Top Overlay
        with ui.row().classes('absolute top-3 left-3 right-3 z-[1000] justify-between items-center bg-slate-900/90 p-2.5 rounded-xl border border-slate-700 shadow-2xl backdrop-blur-md'):
            with ui.row().classes('items-center gap-3'):
                ui.label('🗺️ FULLSCREEN WAZE NAV').classes('text-sm font-extrabold text-blue-400 tracking-wide')
                with ui.row().classes('bg-slate-800 px-3 py-1 rounded-lg border border-slate-700 items-center'):
                    render_driver_weather_widget(lat=current_lat, lon=current_lng)

            ui.button('❌ CLOSE MAP', on_click=map_dialog.close).classes('bg-red-600 hover:bg-red-500 text-white font-bold py-1 px-3 rounded-lg text-xs shadow')

        expanded_map = ui.leaflet(
            center=(current_lat, current_lng), 
            zoom=16, 
            options={'zoomControl': True}
        ).classes('w-full flex-grow rounded-none')
        
        expanded_map.tile_layer(url_template=CARTO_DARK_URL, options=CARTO_DARK_OPTIONS)
        bus_marker_fullscreen = expanded_map.marker(latlng=(current_lat, current_lng))
        
        for i, stop in enumerate(stops):
            expanded_map.marker(
                latlng=(stop["lat"], stop["lng"]), 
                options={'title': f"Stop {i+1}: {stop.get('name', 'Bus Stop')}"}
            )

    # Route Request Form Dialog
    with ui.dialog() as request_dialog, ui.card().classes('bg-slate-900 text-white p-5 border border-slate-700 w-80 rounded-xl gap-4 shadow-2xl'):
        ui.label('🚌 Request Route Assignment').classes('text-base font-extrabold text-blue-400')
        ui.label('Enter your bus number to request route dispatch from admin.').classes('text-xs text-slate-400')
        
        bus_input = ui.input(
            label='Bus Number', 
            value=assigned_bus or '',
            placeholder='e.g. 104'
        ).classes('w-full text-white').props('dark color=blue outlined density=compact')

        async def submit_route_request():
            target_bus = bus_input.value.strip() if bus_input.value else ""
            if not target_bus:
                ui.notify('Please specify a valid bus number.', type='warning', position='top')
                return
            
            try:
                request_payload = {
                    'bus_number': target_bus,
                    'timestamp': {'.sv': 'timestamp'},
                    'status': 'pending',
                    'message': f"Bus {target_bus} driver requested route assignment."
                }
                get_db_reference("route_requests").push(request_payload)
                ui.notify(f"Route requested for Bus {target_bus}!", type='positive', position='top')
                request_dialog.close()
            except Exception:
                ui.notify("Failed to request route.", type='negative', position='top')

        with ui.row().classes('w-full justify-end gap-2 mt-2'):
            ui.button('Cancel', on_click=request_dialog.close).classes('bg-slate-700 hover:bg-slate-600 text-white font-bold py-1.5 px-3 rounded-lg text-xs')
            ui.button('Submit Request', on_click=submit_route_request).classes('bg-blue-600 hover:bg-blue-500 text-white font-bold py-1.5 px-3 rounded-lg text-xs shadow')

    # =========================================================
    # 2. MAIN DASHBOARD HUD
    # =========================================================
    with ui.column().classes('w-full h-screen p-3 bg-slate-900 text-white justify-between overflow-hidden'):
        
        # --- Top Header Bar ---
        with ui.row().classes('w-full justify-between items-center bg-slate-800 p-2.5 rounded-xl border border-slate-700 shadow-md'):
            with ui.row().classes('items-center gap-3'):
                ui.label('🚌 Bulloch Transport').classes('text-xl font-extrabold text-blue-400 tracking-wide')
                ui.badge(f"Bus {assigned_bus}", color='blue').classes('text-xs font-bold px-2.5 py-1 rounded-md')

                if is_admin:
                    ui.badge('DRIVER MODE (ADMIN)', color='amber').classes('text-xs font-bold px-2 py-0.5 rounded-md')

            with ui.row().classes('items-center gap-2.5'):
                clock_label = ui.label('00:00:00').classes('text-xl font-mono font-bold text-slate-200 tracking-wider')
                
                if is_admin:
                    ui.button('🖥️ Admin Console', on_click=lambda: ui.navigate.to('/admin')).classes('bg-slate-700 hover:bg-slate-600 text-white font-bold rounded-lg py-1.5 px-2.5 text-xs shadow')

                ui.button('Logout', on_click=lambda: ui.run_javascript("fetch('/api/v1/auth/logout', {method: 'POST'}).then(()=>{window.location.href='/login'})")).classes('bg-red-600 hover:bg-red-700 text-white font-bold rounded-lg py-1.5 px-2.5 text-xs shadow')

            ui.timer(1.0, lambda: clock_label.set_text(datetime.now().strftime('%H:%M:%S')))

        # --- Main Layout Grid ---
        with ui.grid(columns=12).classes('w-full flex-grow gap-3 my-1 overflow-hidden'):
            
            # LEFT SIDE (7/12 cols): Live Waze Map Navigation HUD
            with ui.column().classes('col-span-7 h-full relative rounded-xl overflow-hidden border border-slate-700 shadow-2xl'):
                
                # 1. WAZE TOP MANEUVER BANNER OVERLAY
                with ui.row().classes('absolute top-2 left-2 right-2 z-[500] bg-cyan-950/90 border border-cyan-500/50 p-2.5 rounded-xl items-center justify-between shadow-2xl backdrop-blur-md'):
                    with ui.row().classes('items-center gap-3'):
                        ui.icon('turn_left', size='32px').classes('text-cyan-400 animate-pulse')
                        with ui.column().classes('gap-0'):
                            maneuver_dist_label = ui.label('GPS INITIALIZING').classes('text-[10px] font-black text-cyan-300 tracking-widest uppercase')
                            maneuver_street_label = ui.label('Follow Assigned Route').classes('text-sm font-extrabold text-white leading-tight')
                    
                    ui.button('🔍 EXPAND', on_click=map_dialog.open).classes('bg-cyan-600 hover:bg-cyan-500 text-white font-bold py-1 px-2 rounded-lg text-[10px] shadow')

                # 2. LEAFLET MAP INSTANCE
                nav_map = ui.leaflet(
                    center=(current_lat, current_lng), 
                    zoom=15, 
                    options={'zoomControl': False}
                ).classes('w-full h-full')
                
                nav_map.tile_layer(url_template=CARTO_DARK_URL, options=CARTO_DARK_OPTIONS)
                bus_marker_hud = nav_map.marker(latlng=(current_lat, current_lng))

                for i, stop in enumerate(stops):
                    nav_map.marker(latlng=(stop["lat"], stop["lng"]))

                # 3. WAZE BOTTOM DRIVING HUD OVERLAY (Real-time Speed, ETA, Distance)
                with ui.row().classes('absolute bottom-2 left-2 right-2 z-[500] bg-slate-900/90 border border-slate-700 p-2 rounded-xl justify-between items-center shadow-2xl backdrop-blur-md'):
                    
                    # Live Speedometer Badge
                    with ui.row().classes('items-center gap-1.5 bg-slate-800 px-3 py-1 rounded-lg border border-slate-600'):
                        speed_label = ui.label('0.0').classes('text-lg font-black text-green-400 font-mono')
                        ui.label('MPH').classes('text-[9px] font-bold text-slate-400')

                    # Next Stop & Distance
                    with ui.column().classes('items-center gap-0'):
                        next_stop_name = stops[0]['name'].upper() if stops else "NO STOPS ASSIGNED"
                        next_stop_label = ui.label(f"NEXT STOP: {next_stop_name}").classes('text-[9px] font-bold text-slate-400 tracking-wider truncate max-w-[200px]')
                        next_stop_dist_label = ui.label('Calculating distance...').classes('text-xs font-black text-amber-400')

                    # Dynamic Calculated ETA
                    with ui.row().classes('items-center gap-1 bg-blue-950/80 px-2.5 py-1 rounded-lg border border-blue-600/50'):
                        ui.icon('schedule', size='16px').classes('text-blue-400')
                        eta_label = ui.label("ETA Calculating...").classes('text-xs font-bold text-blue-200')

            # RIGHT SIDE (5/12 cols): Weather & Compact Route Box
            with ui.column().classes('col-span-5 h-full gap-2 overflow-y-auto justify-start'):
                
                # Weather Forecast Widget
                with ui.row().classes('w-full justify-between items-center bg-slate-800 p-2.5 rounded-xl border border-slate-700 shadow'):
                    render_driver_weather_widget(lat=current_lat, lon=current_lng)

                # Compact Route Assignment Box
                with ui.column().classes('w-full bg-slate-800 p-3 rounded-xl border border-slate-700 gap-2 shadow-lg'):
                    
                    with ui.column().classes('w-full gap-0.5'):
                        ui.label('CURRENT ROUTE ASSIGNMENT').classes('text-slate-400 text-[9px] font-bold uppercase tracking-wider')
                        ui.label(route_name).classes('text-base font-black text-white leading-tight truncate')
                        
                        initial_status = 'ACTIVE' if (stops and any(s.get('status') == 'current' for s in stops)) else 'IDLE'
                        
                        with ui.row().classes('items-center gap-2 mt-1'):
                            status_badge = ui.badge(
                                initial_status, 
                                color='positive' if initial_status == 'ACTIVE' else 'warning'
                            ).classes('text-[10px] font-black px-2 py-0.5 rounded-md')
                            
                            status_label = ui.label(
                                'In Progress' if initial_status == 'ACTIVE' else 'Ready'
                            ).classes(f"text-xs font-semibold {'text-green-400' if initial_status == 'ACTIVE' else 'text-slate-300'}")

                    # OPEN ROUTE REQUEST FORM DIALOG BUTTON
                    ui.button('📥 REQUEST ROUTE FROM ADMIN', on_click=request_dialog.open).classes('w-full bg-blue-600 hover:bg-blue-500 text-white font-extrabold py-2 rounded-lg text-xs shadow active:scale-95 transition-transform')

                    # Start / End Route Actions
                    with ui.row().classes('gap-2 w-full'):
                        def start_route():
                            if not active_route:
                                ui.notify('No active route found to start.', type='negative', position='top')
                                return
                            status_badge.set_text('ACTIVE')
                            status_badge.props('color=positive')
                            status_label.set_text('Route in Progress')
                            status_label.classes(replace='text-green-400')
                            announce_route_status("Route started. Drive safely.")
                            ui.notify('Route Started', type='positive', position='top')

                        def stop_route():
                            if not active_route:
                                return
                            status_badge.set_text('IDLE')
                            status_badge.props('color=warning')
                            status_label.set_text('Route Paused')
                            status_label.classes(replace='text-amber-400')
                            announce_route_status("Route paused.")
                            ui.notify('Route Stopped', type='warning', position='top')

                        ui.button('▶ START', on_click=start_route).classes('bg-green-600 hover:bg-green-500 text-white font-black py-2 px-3 rounded-lg text-xs flex-1 shadow active:scale-95')
                        ui.button('⏸ END', on_click=stop_route).classes('bg-red-600 hover:bg-red-500 text-white font-black py-2 px-3 rounded-lg text-xs flex-1 shadow active:scale-95')

                    # SOS / Incident Dispatch
                    def dispatch_incident_alert():
                        location = {"lat": current_lat, "lng": current_lng}
                        send_emergency_sos(assigned_bus, route_id or "UNASSIGNED", location)
                        ui.notify('Incident alert dispatched to admin!', type='warning', position='top')

                    ui.button('⚠️ DISPATCH INCIDENT ALERT', on_click=dispatch_incident_alert).classes('w-full bg-amber-600 hover:bg-amber-500 text-white font-bold py-1.5 rounded-lg text-xs shadow')

    # =========================================================
    # 3. REAL-TIME HTML5 GEOLOCATION JS TELEMETRY
    # =========================================================
    def handle_gps_update(e):
        nonlocal current_lat, current_lng, current_stop_idx
        data = e.args
        lat = data.get('lat')
        lng = data.get('lng')
        speed_mph = data.get('speed_mph', 0.0)

        # Update Real-time Speed
        speed_label.set_text(f"{speed_mph:.1f}")

        if lat and lng:
            current_lat, current_lng = lat, lng
            
            # Re-center Leaflet maps & move markers
            nav_map.set_center((lat, lng))
            expanded_map.set_center((lat, lng))

            # Dynamic Distance to Next Stop Calculation
            if stops and current_stop_idx < len(stops):
                target = stops[current_stop_idx]
                target_name = target.get('name', f"Stop #{current_stop_idx + 1}")
                target_street = target.get('street_name') or target.get('street', 'Assigned Stop')
                
                dist_miles = haversine_distance(lat, lng, target['lat'], target['lng'])
                
                # Approximate ETA assuming 20 MPH average speed
                est_minutes = max(1, math.ceil((dist_miles / 20.0) * 60))
                eta_time_str = (datetime.now() + timedelta(minutes=est_minutes)).strftime('%I:%M %p')

                next_stop_label.set_text(f"NEXT STOP: {target_name.upper()}")
                eta_label.set_text(f"ETA {eta_time_str}")

                if dist_miles < 0.1:
                    next_stop_dist_label.set_text("ARRIVING NOW")
                    maneuver_dist_label.set_text("ARRIVING")
                    maneuver_street_label.set_text(f"Approaching {target_name}")
                else:
                    dist_ft = int(dist_miles * 5280)
                    dist_str = f"{dist_ft} FT" if dist_ft < 1000 else f"{dist_miles:.1f} MI"
                    
                    next_stop_dist_label.set_text(f"{dist_miles:.2f} mi • {est_minutes} mins remaining")
                    maneuver_dist_label.set_text(f"IN {dist_str}")
                    maneuver_street_label.set_text(f"Head toward {target_street}")

    # Bind JavaScript GPS bridge to Python handler
    ui.on('driver_gps_telemetry', handle_gps_update)

    # Inject client-side Geolocation API listener
    ui.run_javascript('''
        if ("geolocation" in navigator) {
            navigator.geolocation.watchPosition(
                (pos) => {
                    const speedMps = pos.coords.speed || 0;
                    const speedMph = speedMps * 2.23694; // m/s to MPH
                    
                    emitEvent('driver_gps_telemetry', {
                        lat: pos.coords.latitude,
                        lng: pos.coords.longitude,
                        speed_mph: speedMph,
                        heading: pos.coords.heading || 0
                    });
                },
                (err) => {
                    console.warn("GPS Tracking Warning: ", err.message);
                },
                {
                    enableHighAccuracy: true,
                    maximumAge: 1000,
                    timeout: 5000
                }
            );
        }
    ''')