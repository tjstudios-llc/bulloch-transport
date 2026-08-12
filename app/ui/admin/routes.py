# app/ui/admin/routes.py

import inspect
from nicegui import ui, events
from app.ui.admin.header import render_admin_header
from app.services.routes import (
    create_route,
    fetch_all_routes,
    update_route,
    delete_route
)
from app.services.kml_parser import parse_kml_content
from app.services.geocoding import get_street_name_from_coords


def render_admin_routes_page():
    """
    Admin Route Management Console: View, Edit, Delete, and Create Routes.
    """
    current_stops = []
    loaded_polyline = []

    # Shared Navigation Header
    render_admin_header(active_page="routes")

    # Main Container
    with ui.column().classes('w-full p-6 bg-slate-100 min-h-screen gap-6'):
        
        # Tabs Bar
        with ui.tabs().classes('w-full bg-white shadow rounded-xl') as tabs:
            manage_tab = ui.tab('Route Directory', icon='list_alt')
            builder_tab = ui.tab('Create / Import Route', icon='add_location_alt')

        with ui.tab_panels(tabs, value=manage_tab).classes('w-full bg-transparent mt-2'):
            
            # =========================================================
            # TAB 1: ROUTE DIRECTORY (VIEW, EDIT, DELETE)
            # =========================================================
            with ui.tab_panel(manage_tab):
                with ui.row().classes('w-full justify-between items-center mb-4'):
                    ui.label('Active & Saved Routes').classes('text-xl font-bold text-slate-800')
                    ui.button('↻ Refresh Directory', on_click=lambda: refresh_routes_list()).classes(
                        'bg-blue-600 text-white font-bold px-4 py-2 rounded-lg'
                    )

                directory_container = ui.column().classes('w-full gap-4')

                def refresh_routes_list():
                    directory_container.clear()
                    routes = fetch_all_routes()

                    if not routes:
                        with directory_container:
                            with ui.card().classes('w-full p-8 text-center bg-white rounded-xl shadow border border-slate-200'):
                                ui.icon('map', size='48px').classes('text-slate-300 mb-2')
                                ui.label('No routes found in database. Create a route in the next tab to get started.').classes('text-slate-500 font-medium')
                        return

                    with directory_container:
                        for route in routes:
                            r_id = route.get('id')
                            r_name = route.get('name', 'Unnamed Route')
                            r_bus = route.get('assigned_bus') or route.get('bus_number', 'N/A')
                            r_shift = route.get('shift', 'Morning')
                            r_driver = route.get('assigned_driver', 'Unassigned')
                            r_stops = route.get('stops', [])
                            r_active = route.get('active', True)

                            with ui.card().classes('w-full bg-white p-5 rounded-xl shadow border border-slate-200 hover:border-blue-300 transition-all'):
                                with ui.row().classes('w-full justify-between items-center gap-4'):
                                    
                                    # Route Metadata
                                    with ui.column().classes('gap-1'):
                                        with ui.row().classes('items-center gap-2'):
                                            ui.label(r_name).classes('text-lg font-bold text-slate-900')
                                            
                                            status_bg = 'bg-green-100 text-green-800' if r_active else 'bg-slate-100 text-slate-600'
                                            ui.label('Active' if r_active else 'Inactive').classes(f'text-xs px-2 py-0.5 rounded-full font-bold {status_bg}')

                                        with ui.row().classes('items-center gap-4 text-xs text-slate-500 font-medium'):
                                            ui.label(f"🚌 Bus #{r_bus}")
                                            ui.label(f"⏰ Shift: {r_shift}")
                                            ui.label(f"👤 Driver: {r_driver}")
                                            ui.label(f"📍 Stops: {len(r_stops)}")

                                    # Action Buttons
                                    with ui.row().classes('items-center gap-2'):
                                        ui.button('View Stops', on_click=lambda r=route: open_view_dialog(r)).props('dense outline color=primary icon=visibility')
                                        ui.button('Edit', on_click=lambda r=route: open_edit_dialog(r)).props('dense color=blue icon=edit')
                                        ui.button('Delete', on_click=lambda r_id=r_id, r_name=r_name: open_delete_dialog(r_id, r_name)).props('dense color=red icon=delete')

                # --- DIALOG: VIEW ROUTE STOPS & MAP ---
                def open_view_dialog(route: dict):
                    stops = route.get('stops', [])
                    polyline = route.get('path_polyline', [])
                    
                    with ui.dialog() as dialog, ui.card().classes('w-[600px] max-w-full p-6 flex flex-col gap-4'):
                        ui.label(f"Route Preview: {route.get('name')}").classes('text-lg font-bold text-slate-800')
                        
                        preview_map = ui.leaflet(center=(32.4488, -81.7832), zoom=12).classes('w-full h-[300px] rounded-lg')
                        preview_map.tile_layer(url_template='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png')
                        
                        if polyline:
                            preview_map.generic_layer(name='polyline', args=[polyline, {'color': '#2563eb', 'weight': 5}])
                            preview_map.set_center(polyline[0])
                        elif stops:
                            preview_map.set_center((stops[0]['lat'], stops[0]['lng']))

                        for s in stops:
                            preview_map.marker(latlng=(s['lat'], s['lng']))

                        ui.label('Stop Manifest:').classes('font-bold text-sm text-slate-700 mt-2')
                        with ui.scroll_area().classes('w-full h-36 border p-2 rounded bg-slate-50'):
                            for idx, s in enumerate(stops, start=1):
                                ui.label(f"{idx}. {s.get('name')} — {s.get('street_name', 'N/A')}").classes('text-xs text-slate-600')

                        ui.button('Close', on_click=dialog.close).props('flat color=primary').classes('self-end')
                    
                    dialog.open()

                # --- DIALOG: EDIT ROUTE DETAILS ---
                def open_edit_dialog(route: dict):
                    with ui.dialog() as dialog, ui.card().classes('w-96 p-6 flex flex-col gap-4'):
                        ui.label('Edit Route Details').classes('text-lg font-bold text-slate-800')
                        
                        name_input = ui.input('Route Name', value=route.get('name', '')).classes('w-full')
                        bus_input = ui.input('Assigned Bus #', value=route.get('assigned_bus') or route.get('bus_number', '')).classes('w-full')
                        driver_input = ui.input('Assigned Driver', value=route.get('assigned_driver', 'Unassigned')).classes('w-full')
                        shift_select = ui.select(['Morning', 'Afternoon', 'Special Event'], value=route.get('shift', 'Morning'), label='Shift').classes('w-full')
                        active_checkbox = ui.checkbox('Active Route', value=route.get('active', True))

                        def save_changes():
                            payload = {
                                "name": name_input.value.strip(),
                                "assigned_bus": bus_input.value.strip(),
                                "bus_number": bus_input.value.strip(),
                                "assigned_driver": driver_input.value.strip(),
                                "shift": shift_select.value,
                                "active": active_checkbox.value
                            }
                            if update_route(route['id'], payload):
                                ui.notify('Route updated successfully!', type='positive')
                                dialog.close()
                                refresh_routes_list()
                            else:
                                ui.notify('Failed to update route.', type='negative')

                        with ui.row().classes('w-full justify-end gap-2 mt-4'):
                            ui.button('Cancel', on_click=dialog.close).props('flat')
                            ui.button('Save Changes', on_click=save_changes).classes('bg-blue-600 text-white')

                    dialog.open()

                # --- DIALOG: DELETE ROUTE CONFIRMATION ---
                def open_delete_dialog(route_id: str, route_name: str):
                    with ui.dialog() as dialog, ui.card().classes('w-96 p-6 flex flex-col gap-4'):
                        ui.label('Delete Route').classes('text-lg font-bold text-red-600')
                        ui.label(f"Are you sure you want to permanently delete '{route_name}'?").classes('text-sm text-slate-600')

                        def confirm_delete():
                            if delete_route(route_id):
                                ui.notify(f"Route '{route_name}' deleted.", type='info')
                                dialog.close()
                                refresh_routes_list()
                            else:
                                ui.notify('Failed to delete route.', type='negative')

                        with ui.row().classes('w-full justify-end gap-2 mt-4'):
                            ui.button('Cancel', on_click=dialog.close).props('flat')
                            ui.button('Delete', on_click=confirm_delete).classes('bg-red-600 text-white')

                    dialog.open()

                # Initial render of directory
                refresh_routes_list()

            # =========================================================
            # TAB 2: ROUTE BUILDER & KML IMPORT
            # =========================================================
            with ui.tab_panel(builder_tab):
                with ui.row().classes('w-full gap-6 items-start'):
                    
                    # Left Column: Inputs & Upload
                    with ui.card().classes('w-96 bg-white p-6 rounded-xl shadow border border-slate-200 flex flex-col gap-4'):
                        ui.label('Create New Route').classes('text-lg font-bold text-slate-800')
                        
                        route_name_input = ui.input('Route Name', placeholder='e.g., Route 14A Morning').classes('w-full')
                        bus_number_input = ui.input('Bus #', placeholder='e.g., 104').classes('w-full')
                        driver_name_input = ui.input('Driver Name', placeholder='e.g., John Doe').classes('w-full')
                        shift_select = ui.select(['Morning', 'Afternoon', 'Special Event'], value='Morning', label='Shift').classes('w-full')

                        ui.separator()

                        ui.label('Import Route Path from Google Maps (.kml)').classes('text-sm font-bold text-slate-700')
                        
                        async def handle_kml_upload(e: events.UploadEventArguments):
                            nonlocal loaded_polyline, current_stops
                            try:
                                content_stream = getattr(e, 'content', None) or getattr(e, 'file', None)
                                
                                if hasattr(content_stream, 'read'):
                                    read_result = content_stream.read()
                                    if hasattr(read_result, '__await__'):
                                        content = await read_result
                                    else:
                                        content = read_result
                                else:
                                    content = content_stream

                                parsed = parse_kml_content(content)
                                
                                if parsed.get("name"):
                                    route_name_input.set_value(parsed["name"])

                                current_stops.clear()
                                current_stops.extend(parsed.get("stops", []))
                                
                                loaded_polyline.clear()
                                loaded_polyline.extend(parsed.get("path_polyline", []))

                                refresh_builder_map()
                                ui.notify(f"Imported {len(current_stops)} stops and polyline path!", type='positive')
                            except Exception as err:
                                ui.notify(f"KML Upload Failed: {err}", type='negative')

                        ui.upload(
                            label="Choose .kml file",
                            auto_upload=True,
                            on_upload=handle_kml_upload
                        ).props('accept=.kml,.kmz').classes('w-full')

                        ui.separator()

                        ui.label('Added Stops Manifest').classes('text-sm font-bold text-slate-600')
                        stops_container = ui.column().classes('w-full gap-2 min-h-[100px]')

                        def render_stops_list():
                            stops_container.clear()
                            if not current_stops:
                                with stops_container:
                                    ui.label('Click map or upload KML to place stops').classes('text-xs text-slate-400 italic')
                                return

                            for idx, stop in enumerate(current_stops, start=1):
                                street = stop.get('street_name') or f"{stop['lat']:.4f}, {stop['lng']:.4f}"
                                with stops_container:
                                    with ui.row().classes('w-full justify-between items-center p-2 bg-slate-50 rounded border border-slate-200'):
                                        ui.label(f"{idx}. {stop['name']}").classes('text-xs font-bold text-slate-700')
                                        ui.label(street).classes('text-[11px] text-slate-500 truncate max-w-[160px]')

                        render_stops_list()

                        def save_route_click():
                            r_name = route_name_input.value.strip() if route_name_input.value else ""
                            b_num = bus_number_input.value.strip() if bus_number_input.value else ""
                            d_driver = driver_name_input.value.strip() if driver_name_input.value else "Unassigned"
                            s_shift = shift_select.value

                            if not r_name or not b_num:
                                ui.notify('Please provide a route name and bus number.', type='warning')
                                return

                            if not current_stops:
                                ui.notify('Please add at least one stop on the map or import a KML file.', type='warning')
                                return

                            success = create_route(
                                route_name=r_name, 
                                bus_number=b_num, 
                                shift=s_shift, 
                                stops=current_stops, 
                                path_polyline=loaded_polyline,
                                assigned_driver=d_driver
                            )
                            
                            if success:
                                ui.notify(f"Route '{r_name}' successfully created!", type='positive')
                                route_name_input.set_value('')
                                bus_number_input.set_value('')
                                driver_name_input.set_value('')
                                current_stops.clear()
                                loaded_polyline.clear()
                                refresh_builder_map()
                                refresh_routes_list()
                            else:
                                ui.notify('Failed to save route to Firestore.', type='negative')

                        ui.button('SAVE ROUTE', on_click=save_route_click).classes(
                            'w-full bg-green-600 hover:bg-green-500 text-white font-bold py-3 rounded-lg shadow'
                        )

                    # Right Column: Map
                    with ui.card().classes('flex-1 bg-white p-4 rounded-xl shadow border border-slate-200 flex flex-col'):
                        ui.label('Interactive Stop & Path Map').classes('text-md font-bold text-slate-700 mb-2')
                        
                        builder_map = ui.leaflet(center=(32.4488, -81.7832), zoom=13).classes('w-full h-[500px] rounded-lg')

                        def refresh_builder_map():
                            builder_map.clear_layers()
                            builder_map.tile_layer(url_template='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png')

                            for stop in current_stops:
                                builder_map.marker(latlng=(stop['lat'], stop['lng']))

                            if loaded_polyline:
                                builder_map.generic_layer(
                                    name='polyline',
                                    args=[loaded_polyline, {'color': '#2563eb', 'weight': 5, 'opacity': 0.8}]
                                )
                                builder_map.set_center(loaded_polyline[0])

                            render_stops_list()

                        async def on_map_click(e):
                            lat = e.args['latlng']['lat']
                            lng = e.args['latlng']['lng']
                            
                            stop_num = len(current_stops) + 1
                            stop_name = f"Stop #{stop_num}"
                            
                            if inspect.iscoroutinefunction(get_street_name_from_coords):
                                street_name = await get_street_name_from_coords(lat, lng)
                            else:
                                street_name = get_street_name_from_coords(lat, lng)
                            
                            current_stops.append({
                                "name": stop_name,
                                "street_name": street_name,
                                "lat": lat,
                                "lng": lng,
                                "status": "pending"
                            })
                            refresh_builder_map()

                        builder_map.on('click', on_map_click)