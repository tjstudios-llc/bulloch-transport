# app/ui/driver/dashboard.py

from datetime import datetime
from nicegui import ui
from app.services.tts import announce_route_status
from app.ui.driver.weather_widget import render_driver_weather_widget
from app.services.routes import (
    fetch_active_route_for_bus,
    send_emergency_sos,
)


def render_driver_dashboard(user_role: str = "driver", bus_number: str = "Bus 104"):
    """
    1024x600 Touchscreen CarPlay-Style HUD for Bus Drivers & Driving Admins.
    Connected to live Firestore route data.
    """
    ui.colors(primary='#103f73', secondary='#2f73c7', positive='#148560')

    is_admin = user_role in ("admin", "dispatch", "dispatcher")

    # Fetch real active route data from Firestore
    active_route = fetch_active_route_for_bus(bus_number=bus_number)

    # Extract dynamic properties with fallbacks
    route_id = active_route["id"] if active_route else None
    route_name = active_route.get("name", "No Active Route Assigned") if active_route else "No Active Route Assigned"
    assigned_bus = active_route.get("assigned_bus", bus_number) if active_route else bus_number
    stops = active_route.get("stops", []) if active_route else []

    with ui.column().classes('w-full h-screen p-4 bg-slate-900 text-white justify-between overflow-hidden'):
        
        # --- CarPlay Top Header Bar ---
        with ui.row().classes('w-full justify-between items-center bg-slate-800 p-3 rounded-xl border border-slate-700 shadow-md'):
            with ui.row().classes('items-center gap-3'):
                ui.label('🚌 Bulloch Transport').classes('text-2xl font-extrabold text-blue-400 tracking-wide')
                
                # Active Vehicle Badge
                ui.badge(assigned_bus, color='blue').classes('text-sm font-bold px-3 py-1 rounded-md')

                if is_admin:
                    ui.badge('DRIVER MODE (ADMIN)', color='amber').classes('text-xs font-bold px-2.5 py-1 rounded-md')

            # Right Header Controls (Clock, Admin Switcher, Logout)
            with ui.row().classes('items-center gap-3'):
                clock_label = ui.label('00:00:00').classes('text-2xl font-mono font-bold text-slate-200 tracking-wider')
                
                if is_admin:
                    ui.button(
                        '🖥️ Admin Console', 
                        on_click=lambda: ui.navigate.to('/admin')
                    ).classes('bg-slate-700 hover:bg-slate-600 text-white font-bold rounded-lg py-2 px-3 text-xs shadow')

                ui.button(
                    'Logout', 
                    on_click=lambda: ui.run_javascript("fetch('/api/v1/auth/logout', {method: 'POST'}).then(()=>{window.location.href='/login'})")
                ).classes('bg-red-600 hover:bg-red-700 text-white font-bold rounded-lg py-2 px-3 text-xs shadow')

            def update_clock() -> None:
                clock_label.set_text(datetime.now().strftime('%H:%M:%S'))

            ui.timer(1.0, update_clock)

        # --- Main CarPlay HUD Layout ---
        with ui.row().classes('w-full grid grid-cols-3 gap-4 flex-grow my-3'):
            
            # Left Section (2 Cols): Active Route Operating Center
            with ui.card().classes('col-span-2 bg-slate-800 p-6 rounded-xl border border-slate-700 flex flex-col justify-between shadow-lg'):
                
                with ui.row().classes('w-full justify-between items-start'):
                    with ui.column().classes('gap-1'):
                        ui.label('Current Route Assignment').classes('text-slate-400 text-xs font-bold uppercase tracking-wider')
                        ui.label(route_name).classes('text-3xl font-black text-white')
                    
                    # Compute initial status from Firestore stop states
                    initial_status = 'ACTIVE' if (stops and any(s.get('status') == 'current' for s in stops)) else 'IDLE'
                    status_badge = ui.badge(initial_status, color='positive' if initial_status == 'ACTIVE' else 'warning').classes('text-base font-black px-4 py-1.5 rounded-lg')

                # Status Indicator Text & Manifest Count
                with ui.column().classes('my-2 gap-1'):
                    status_label = ui.label(
                        'Route in Progress — Drive Safely' if initial_status == 'ACTIVE' else 'Ready to Start'
                    ).classes(f"text-xl font-semibold {'text-green-400' if initial_status == 'ACTIVE' else 'text-slate-300'}")

                    if active_route:
                        ui.label(f"📍 {len(stops)} stops loaded on manifest from Firestore").classes("text-slate-400 text-xs font-medium")
                    else:
                        ui.label("⚠️ No active route configured for this vehicle in database.").classes("text-amber-400 text-xs italic")

                # Tactile Touchscreen Action Buttons
                with ui.row().classes('gap-4 w-full'):
                    def start_route():
                        if not active_route:
                            ui.notify('No active route found in Firestore.', type='negative', position='top')
                            return
                        status_badge.set_text('ACTIVE')
                        status_badge.props('color=positive')
                        status_label.set_text('Route in Progress — Drive Safely')
                        status_label.classes(replace='text-green-400')
                        announce_route_status("Route started. Drive safely.")
                        ui.notify('Route Started', type='positive', position='top')

                    def stop_route():
                        if not active_route:
                            return
                        status_badge.set_text('IDLE')
                        status_badge.props('color=warning')
                        status_label.set_text('Route Paused / Ended')
                        status_label.classes(replace='text-amber-400')
                        announce_route_status("Route paused.")
                        ui.notify('Route Stopped', type='warning', position='top')

                    ui.button('▶ START ROUTE', on_click=start_route).classes(
                        'bg-green-600 hover:bg-green-500 text-white font-black py-4 px-8 rounded-xl text-xl flex-1 shadow-lg active:scale-95 transition-transform'
                    )
                    ui.button('⏸ END ROUTE', on_click=stop_route).classes(
                        'bg-red-600 hover:bg-red-500 text-white font-black py-4 px-8 rounded-xl text-xl flex-1 shadow-lg active:scale-95 transition-transform'
                    )

            # Right Section (1 Col): Live Weather & Quick Driver Actions
            with ui.column().classes('col-span-1 gap-3 h-full justify-between'):
                
                # Top Right: Real-time Weather Widget
                render_driver_weather_widget(lat=32.4488, lon=-81.7832)

                # Bottom Right: Driver Touch Controls
                with ui.card().classes('w-full bg-slate-800 p-4 rounded-xl border border-slate-700 flex-1 flex flex-col justify-between shadow-lg'):
                    ui.label('Driver Actions').classes('text-slate-400 text-xs font-bold uppercase tracking-wider mb-2')
                    
                    with ui.column().classes('w-full gap-2.5 flex-1 justify-center'):
                        ui.button(
                            '🗺️ Turn-By-Turn Map', 
                            on_click=lambda: ui.navigate.to('/driver/map')
                        ).classes('w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3.5 rounded-xl text-sm shadow')
                        
                        def dispatch_incident_alert():
                            location = {"lat": stops[0]["lat"], "lng": stops[0]["lng"]} if stops else {"lat": 32.4488, "lng": -81.7832}
                            send_emergency_sos(assigned_bus, route_id or "UNASSIGNED", location)
                            ui.notify('Incident report logged to Firestore and dispatched to admin team!', type='warning', position='top')

                        ui.button(
                            '⚠️ Dispatch Alert / Incident', 
                            on_click=dispatch_incident_alert
                        ).classes('w-full bg-amber-600 hover:bg-amber-500 text-white font-bold py-3.5 rounded-xl text-sm shadow')