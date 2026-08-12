# app/ui/driver/routes.py

from nicegui import app, ui
from app.services.routes import fetch_active_route_for_bus, update_stop_status


def render_driver_page():
    """
    Driver Route Execution Interface.
    Designed for touch devices and quick stop progression.
    """
    active_bus = app.storage.user.get('bus_number', '104')
    active_route = fetch_active_route_for_bus(active_bus)

    # --- Header Bar ---
    with ui.header().classes('bg-blue-900 text-white p-4 justify-between items-center shadow-md'):
        ui.label('🚌 Bulloch Schools — Driver Navigation').classes('text-lg font-bold')
        
        with ui.row().classes('items-center gap-3'):
            # Show Admin switch button for administrative or dispatch roles
            user_role = app.storage.user.get('role', '')
            if user_role in ('admin', 'dispatch', 'dispatcher'):
                ui.button('⚙️ Admin Console', on_click=lambda: ui.navigate.to('/admin/routes')).props('flat color=white text-color=white')
            
            ui.label(f"Bus #{active_bus}").classes('bg-blue-700 px-3 py-1 rounded-full text-xs font-bold')

    # --- Main Container ---
    with ui.column().classes('w-full p-4 bg-slate-100 min-h-screen gap-4'):
        
        # Bus Selector bar (if route isn't loaded)
        with ui.row().classes('w-full bg-white p-3 rounded-xl shadow border border-slate-200 items-center justify-between'):
            bus_input = ui.input('Assigned Bus #', value=active_bus).classes('w-36')
            
            def load_bus_route():
                app.storage.user['bus_number'] = bus_input.value.strip()
                ui.navigate.reload()

            ui.button('Load Route', on_click=load_bus_route).classes('bg-blue-600 text-white font-bold px-4 py-2 rounded-lg')

        if not active_route:
            with ui.card().classes('w-full p-8 text-center bg-amber-50 border border-amber-200 rounded-xl mt-4'):
                ui.label(f"No active route assigned to Bus #{active_bus}.").classes('text-lg font-bold text-amber-800')
                ui.label("Please verify the bus number or contact dispatch.").classes('text-sm text-amber-600')
            return

        route_id = active_route['id']
        stops = active_route.get('stops', [])
        polyline = active_route.get('path_polyline', [])

        ui.label(f"{active_route.get('name')} ({active_route.get('shift')} Shift)").classes('text-xl font-bold text-slate-800')

        # --- 2-Column Responsive Layout (Map + Manifest) ---
        with ui.row().classes('w-full gap-4 items-start'):
            
            # Left Column: Stops Progression List
            with ui.card().classes('w-full md:w-96 bg-white p-4 rounded-xl shadow border border-slate-200 flex flex-col gap-3'):
                ui.label('Route Manifest & Progress').classes('text-md font-bold text-slate-800')
                
                manifest_container = ui.column().classes('w-full gap-2')

                def render_manifest():
                    manifest_container.clear()
                    for idx, stop in enumerate(stops):
                        status = stop.get('status', 'pending')
                        
                        bg_color = 'bg-slate-50 border-slate-200'
                        badge_color = 'bg-slate-200 text-slate-700'
                        
                        if status == 'completed':
                            bg_color = 'bg-green-50 border-green-200'
                            badge_color = 'bg-green-600 text-white'
                        elif status == 'next':
                            bg_color = 'bg-blue-50 border-blue-300 ring-2 ring-blue-400'
                            badge_color = 'bg-blue-600 text-white'

                        with manifest_container:
                            with ui.row().classes(f'w-full justify-between items-center p-3 rounded-lg border {bg_color}'):
                                with ui.column().classes('gap-0'):
                                    ui.label(f"{idx + 1}. {stop['name']}").classes('text-sm font-bold text-slate-800')
                                    ui.label(stop.get('street_name', '')).classes('text-xs text-slate-500')
                                
                                async def mark_done(s_idx=idx):
                                    update_stop_status(route_id, s_idx, 'completed')
                                    stops[s_idx]['status'] = 'completed'
                                    
                                    # Set the next stop as active
                                    if s_idx + 1 < len(stops):
                                        update_stop_status(route_id, s_idx + 1, 'next')
                                        stops[s_idx + 1]['status'] = 'next'
                                        
                                    render_manifest()
                                    render_driver_map()

                                if status == 'completed':
                                    ui.label('✓ Done').classes('text-xs font-bold text-green-700')
                                else:
                                    ui.button('ARRIVED', on_click=mark_done).classes(
                                        'bg-green-600 hover:bg-green-500 text-white text-xs font-bold py-1 px-3 rounded-lg shadow'
                                    )

                render_manifest()

            # Right Column: Driver Route Map
            with ui.card().classes('flex-1 bg-white p-3 rounded-xl shadow border border-slate-200 flex flex-col'):
                driver_map = ui.leaflet(center=(32.4488, -81.7832), zoom=13).classes('w-full h-[550px] rounded-lg')

                def render_driver_map():
                    driver_map.clear_layers()
                    # OpenStreetMap tile layer URL template
                    driver_map.tile_layer(url_template='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png')

                    # 1. Draw Route Polyline
                    if polyline:
                        driver_map.generic_layer(
                            name='polyline',
                            args=[polyline, {'color': '#2563eb', 'weight': 6, 'opacity': 0.85}]
                        )
                        driver_map.set_center(polyline[0])
                    elif stops:
                        driver_map.set_center((stops[0]['lat'], stops[0]['lng']))

                    # 2. Draw Stop Markers
                    for stop in stops:
                        driver_map.marker(latlng=(stop['lat'], stop['lng']))

                render_driver_map()