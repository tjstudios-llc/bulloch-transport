# app/ui/admin/routes.py

from datetime import datetime
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
from app.services.firebase import get_db_reference
from app.services.settings import get_auto_approve_setting, set_auto_approve_setting


def render_admin_routes_page():
    """
    Admin Route Management Console: Refactored for 1024x600 Kiosk Displays.
    Includes Auto-Approval controls, Pending Requests, and Historical Request Logs.
    """
    current_stops = []
    loaded_polyline = []

    # Shared Navigation Header (~48px)
    render_admin_header(active_page="routes")

    # Main Kiosk Container (Fixed 540px height prevents outer page scrolling)
    with ui.column().classes('w-full max-w-[1024px] h-[540px] p-2 bg-slate-100 gap-2 overflow-hidden mx-auto'):
        
        # Compact Tabs Bar + Auto-Approve Toggle Switch
        with ui.row().classes('w-full justify-between items-center bg-white shadow-sm rounded-lg px-2'):
            with ui.tabs().props('dense active-color=primary').classes('bg-transparent') as tabs:
                manage_tab = ui.tab('Route Directory', icon='list_alt')
                builder_tab = ui.tab('Create / Import Route', icon='add_location_alt')
                requests_tab = ui.tab('Route Requests', icon='pending_actions')
                logs_tab = ui.tab('Request Logs', icon='history')

            # Embedded Settings Toggle
            with ui.row().classes('items-center gap-2 py-1 pr-2'):
                ui.label('Auto-Approve Requests').classes('text-xs font-bold text-slate-700')
                initial_toggle = get_auto_approve_setting()
                
                def on_toggle_change(e):
                    set_auto_approve_setting(e.value)
                    status_str = "ENABLED" if e.value else "DISABLED"
                    ui.notify(f"Auto-approval {status_str}", type='positive' if e.value else 'warning')

                ui.switch(value=initial_toggle, on_change=on_toggle_change).props('dense color=green')

        with ui.tab_panels(tabs, value=manage_tab).classes('w-full flex-1 bg-transparent p-0 overflow-hidden'):
            
            # =========================================================
            # TAB 1: ROUTE DIRECTORY
            # =========================================================
            with ui.tab_panel(manage_tab).classes('p-0 h-full flex flex-col gap-2 overflow-hidden'):
                
                # Top Action Bar
                with ui.row().classes('w-full justify-between items-center bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-sm'):
                    ui.label('Active & Saved Routes').classes('text-sm font-bold text-slate-800')
                    ui.button('↻ Refresh', on_click=lambda: refresh_routes_list()) \
                        .props('dense flat color=primary icon=refresh') \
                        .classes('text-xs font-semibold')

                # Scrollable Directory Container
                directory_container = ui.column().classes('w-full flex-1 gap-2 overflow-y-auto pr-1')

                def refresh_routes_list():
                    directory_container.clear()
                    routes = fetch_all_routes()

                    if not routes:
                        with directory_container:
                            with ui.card().classes('w-full p-6 text-center bg-white rounded-lg shadow-sm border border-slate-200'):
                                ui.icon('map', size='36px').classes('text-slate-300 mb-1 mx-auto')
                                ui.label('No routes found in database. Create one in the next tab.').classes('text-xs text-slate-500 font-medium')
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

                            with ui.card().classes('w-full bg-white p-2.5 rounded-lg shadow-sm border border-slate-200 hover:border-blue-300 transition-all'):
                                with ui.row().classes('w-full justify-between items-center gap-2'):
                                    
                                    # Route Metadata
                                    with ui.column().classes('gap-0.5'):
                                        with ui.row().classes('items-center gap-2'):
                                            ui.label(r_name).classes('text-sm font-bold text-slate-900')
                                            status_bg = 'bg-green-100 text-green-800' if r_active else 'bg-slate-100 text-slate-600'
                                            ui.label('Active' if r_active else 'Inactive').classes(f'text-[10px] px-1.5 py-0.2 rounded-full font-bold {status_bg}')

                                        with ui.row().classes('items-center gap-3 text-[11px] text-slate-500 font-medium'):
                                            ui.label(f"🚌 Bus #{r_bus}")
                                            ui.label(f"⏰ Shift: {r_shift}")
                                            ui.label(f"👤 Driver: {r_driver}")
                                            ui.label(f"📍 Stops: {len(r_stops)}")

                                    # Action Buttons
                                    with ui.row().classes('items-center gap-1'):
                                        ui.button('Stops', on_click=lambda r=route: open_view_dialog(r)).props('dense outline color=primary icon=visibility').classes('text-xs')
                                        ui.button('Edit', on_click=lambda r=route: open_edit_dialog(r)).props('dense color=blue icon=edit').classes('text-xs')
                                        ui.button('Delete', on_click=lambda r_id=r_id, r_name=r_name: open_delete_dialog(r_id, r_name)).props('dense color=red icon=delete').classes('text-xs')

                # --- DIALOGS ---
                def open_view_dialog(route: dict):
                    stops = route.get('stops', [])
                    polyline = route.get('path_polyline', [])
                    
                    with ui.dialog() as dialog, ui.card().classes('w-[500px] max-w-full p-3 flex flex-col gap-2 rounded-xl'):
                        ui.label(f"Route Preview: {route.get('name')}").classes('text-sm font-bold text-slate-800')
                        
                        preview_map = ui.leaflet(center=(32.4488, -81.7832), zoom=12).classes('w-full h-[200px] rounded-lg')
                        preview_map.tile_layer(url_template='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png')
                        
                        if polyline:
                            preview_map.generic_layer(name='polyline', args=[polyline, {'color': '#2563eb', 'weight': 4}])
                            preview_map.set_center(polyline[0])
                        elif stops:
                            preview_map.set_center((stops[0]['lat'], stops[0]['lng']))

                        for s in stops:
                            preview_map.marker(latlng=(s['lat'], s['lng']))

                        ui.label('Stop Manifest:').classes('font-bold text-xs text-slate-700 mt-1')
                        with ui.scroll_area().classes('w-full h-24 border p-1.5 rounded bg-slate-50'):
                            for idx, s in enumerate(stops, start=1):
                                ui.label(f"{idx}. {s.get('name')} — {s.get('street_name', 'N/A')}").classes('text-[11px] text-slate-600')

                        ui.button('Close', on_click=dialog.close).props('dense flat color=primary').classes('self-end text-xs')
                    
                    dialog.open()

                def open_edit_dialog(route: dict):
                    with ui.dialog() as dialog, ui.card().classes('w-80 p-4 flex flex-col gap-2 rounded-xl'):
                        ui.label('Edit Route Details').classes('text-sm font-bold text-slate-800')
                        
                        name_input = ui.input('Route Name', value=route.get('name', '')).props('dense outlined').classes('w-full')
                        bus_input = ui.input('Assigned Bus #', value=route.get('assigned_bus') or route.get('bus_number', '')).props('dense outlined').classes('w-full')
                        driver_input = ui.input('Assigned Driver', value=route.get('assigned_driver', 'Unassigned')).props('dense outlined').classes('w-full')
                        shift_select = ui.select(['Morning', 'Afternoon', 'Special Event'], value=route.get('shift', 'Morning'), label='Shift').props('dense outlined').classes('w-full')
                        active_checkbox = ui.checkbox('Active Route', value=route.get('active', True)).classes('text-xs')

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
                                ui.notify('Route updated!', type='positive')
                                dialog.close()
                                refresh_routes_list()
                            else:
                                ui.notify('Failed to update route.', type='negative')

                        with ui.row().classes('w-full justify-end gap-2 mt-2'):
                            ui.button('Cancel', on_click=dialog.close).props('dense flat').classes('text-xs')
                            ui.button('Save', on_click=save_changes).classes('bg-blue-600 text-white text-xs h-8 px-3 rounded-md')

                    dialog.open()

                def open_delete_dialog(route_id: str, route_name: str):
                    with ui.dialog() as dialog, ui.card().classes('w-80 p-4 flex flex-col gap-3 rounded-xl'):
                        ui.label('Delete Route').classes('text-sm font-bold text-red-600')
                        ui.label(f"Permanently delete '{route_name}'?").classes('text-xs text-slate-600')

                        def confirm_delete():
                            if delete_route(route_id):
                                ui.notify(f"Deleted '{route_name}'.", type='info')
                                dialog.close()
                                refresh_routes_list()
                            else:
                                ui.notify('Failed to delete route.', type='negative')

                        with ui.row().classes('w-full justify-end gap-2 mt-1'):
                            ui.button('Cancel', on_click=dialog.close).props('dense flat').classes('text-xs')
                            ui.button('Delete', on_click=confirm_delete).classes('bg-red-600 text-white text-xs h-8 px-3 rounded-md')

                    dialog.open()

                refresh_routes_list()

            # =========================================================
            # TAB 2: ROUTE BUILDER & KML IMPORT
            # =========================================================
            with ui.tab_panel(builder_tab).classes('p-0 h-full overflow-hidden'):
                with ui.row().classes('w-full h-full gap-2 items-stretch overflow-hidden'):
                    
                    # Form Sidebar
                    with ui.card().classes('w-[320px] bg-white p-3 rounded-lg shadow-sm border border-slate-200 flex flex-col h-full overflow-hidden'):
                        with ui.column().classes('w-full flex-1 overflow-y-auto gap-2 pr-1'):
                            ui.label('Route Details').classes('text-xs font-bold text-slate-800 uppercase tracking-wider')
                            
                            route_name_input = ui.input('Route Name', placeholder='e.g., Route 14A').props('dense outlined').classes('w-full text-xs')
                            
                            with ui.row().classes('w-full gap-2'):
                                bus_number_input = ui.input('Bus #', placeholder='104').props('dense outlined').classes('flex-1')
                                shift_select = ui.select(['Morning', 'Afternoon', 'Special Event'], value='Morning', label='Shift').props('dense outlined').classes('flex-1')
                            
                            driver_name_input = ui.input('Driver Name', placeholder='John Doe').props('dense outlined').classes('w-full')

                            ui.label('Import KML Path').classes('text-[11px] font-bold text-slate-700 mt-1')
                            
                            async def handle_kml_upload(e: events.UploadEventArguments):
                                nonlocal loaded_polyline, current_stops
                                try:
                                    content_stream = getattr(e, 'content', None) or getattr(e, 'file', None)
                                    if hasattr(content_stream, 'read'):
                                        read_result = content_stream.read()
                                        content = await read_result if hasattr(read_result, '__await__') else read_result
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
                                    ui.notify(f"Imported {len(current_stops)} stops!", type='positive')
                                except Exception as err:
                                    ui.notify(f"KML Upload Failed: {err}", type='negative')

                            ui.upload(
                                label="Choose .kml file",
                                auto_upload=True,
                                on_upload=handle_kml_upload
                            ).props('accept=.kml,.kmz dense outlined flat').classes('w-full text-xs max-h-28 overflow-hidden')

                            ui.label('Stops Manifest').classes('text-[11px] font-bold text-slate-700 mt-1')
                            stops_container = ui.column().classes('w-full flex-1 overflow-y-auto gap-1 border rounded p-1 bg-slate-50 min-h-[60px]')

                            def render_stops_list():
                                stops_container.clear()
                                if not current_stops:
                                    with stops_container:
                                        ui.label('Click map or upload KML').classes('text-[10px] text-slate-400 italic p-1')
                                    return

                                for idx, stop in enumerate(current_stops, start=1):
                                    street = stop.get('street_name') or f"{stop['lat']:.4f}, {stop['lng']:.4f}"
                                    with stops_container:
                                        with ui.row().classes('w-full justify-between items-center p-1 bg-white rounded border border-slate-200'):
                                            ui.label(f"{idx}. {stop['name']}").classes('text-[10px] font-bold text-slate-700')
                                            ui.label(street).classes('text-[9px] text-slate-500 truncate max-w-[120px]')

                            render_stops_list()

                        def save_route_click():
                            r_name = route_name_input.value.strip() if route_name_input.value else ""
                            b_num = bus_number_input.value.strip() if bus_number_input.value else ""
                            d_driver = driver_name_input.value.strip() if driver_name_input.value else "Unassigned"
                            s_shift = shift_select.value

                            if not r_name or not b_num:
                                ui.notify('Provide route name and bus number.', type='warning')
                                return

                            if not current_stops:
                                ui.notify('Add at least one stop.', type='warning')
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
                                ui.notify(f"Route '{r_name}' created!", type='positive')
                                route_name_input.set_value('')
                                bus_number_input.set_value('')
                                driver_name_input.set_value('')
                                current_stops.clear()
                                loaded_polyline.clear()
                                refresh_builder_map()
                                refresh_routes_list()
                            else:
                                ui.notify('Failed to save route.', type='negative')

                        with ui.row().classes('w-full pt-2 border-t border-slate-200 mt-auto bg-white'):
                            ui.button('SAVE ROUTE', on_click=save_route_click).classes(
                                'w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold h-9 text-xs rounded-md shadow'
                            )

                    # Map View
                    with ui.card().classes('flex-1 bg-white p-2 rounded-lg shadow-sm border border-slate-200 flex flex-col h-full overflow-hidden'):
                        ui.label('Interactive Stop & Path Map').classes('text-xs font-bold text-slate-700 mb-1')
                        
                        builder_map = ui.leaflet(center=(32.4488, -81.7832), zoom=13).classes('w-full flex-1 rounded-md')

                        def refresh_builder_map():
                            builder_map.clear_layers()
                            builder_map.tile_layer(url_template='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png')

                            for stop in current_stops:
                                builder_map.marker(latlng=(stop['lat'], stop['lng']))

                            if loaded_polyline:
                                builder_map.generic_layer(
                                    name='polyline',
                                    args=[loaded_polyline, {'color': '#2563eb', 'weight': 4, 'opacity': 0.8}]
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

            # =========================================================
            # TAB 3: PENDING ROUTE REQUESTS
            # =========================================================
            with ui.tab_panel(requests_tab).classes('p-0 h-full overflow-hidden flex flex-col gap-2'):
                render_route_requests_panel()

            # =========================================================
            # TAB 4: REQUEST LOGS (HISTORICAL ARCHIVE)
            # =========================================================
            with ui.tab_panel(logs_tab).classes('p-0 h-full overflow-hidden flex flex-col gap-2'):
                render_request_logs_panel()


def render_route_requests_panel():
    """Renders active (pending) driver route requests."""
    requests_container = ui.column().classes('w-full flex-1 gap-2 overflow-y-auto pr-1')

    def process_request(request_id: str, new_status: str, req_data: dict):
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            payload = {
                **req_data,
                'status': new_status,
                'processed_at': timestamp,
                'action_by': 'Admin'
            }
            # Update main status
            get_db_reference(f"route_requests/{request_id}").update(payload)
            # Log record
            get_db_reference(f"request_logs/{request_id}").set(payload)
            
            ui.notify(f"Request marked as {new_status.upper()} and logged.", type='positive')
            load_pending_requests()
        except Exception as err:
            ui.notify(f"Failed to process request: {err}", type='negative')

    def load_pending_requests():
        requests_container.clear()
        
        try:
            raw_data = get_db_reference("route_requests").get() or {}
        except Exception:
            raw_data = {}

        # Filter only pending requests
        pending_requests = {k: v for k, v in raw_data.items() if v.get('status', 'pending') == 'pending'}

        # Auto-Approve Check
        if get_auto_approve_setting() and pending_requests:
            for req_id, req in list(pending_requests.items()):
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                payload = {
                    **req,
                    'status': 'approved',
                    'processed_at': timestamp,
                    'action_by': 'Auto-Approve System'
                }
                get_db_reference(f"route_requests/{req_id}").update(payload)
                get_db_reference(f"request_logs/{req_id}").set(payload)
            pending_requests.clear()
            ui.notify("Pending requests auto-approved and logged!", type='info')

        if not pending_requests:
            with requests_container:
                with ui.card().classes('w-full p-6 text-center bg-white rounded-lg shadow-sm border border-slate-200 mt-2'):
                    ui.icon('inbox', size='36px').classes('text-slate-300 mb-1 mx-auto')
                    ui.label('No pending route requests found.').classes('text-xs text-slate-500 font-medium')
            return

        with requests_container:
            with ui.row().classes('w-full bg-slate-200 px-3 py-1.5 rounded-lg font-bold text-[11px] text-slate-700 uppercase items-center'):
                ui.label('Bus #').classes('w-20')
                ui.label('Message / Request Info').classes('flex-1')
                ui.label('Status').classes('w-24 text-center')
                ui.label('Actions').classes('w-36 text-right')

            for req_id, req in reversed(list(pending_requests.items())):
                bus_num = req.get('bus_number', 'N/A')
                message = req.get('message', 'No details provided.')

                with ui.card().classes('w-full bg-white p-2 rounded-lg shadow-sm border border-slate-200 hover:border-blue-300 transition-all'):
                    with ui.row().classes('w-full justify-between items-center gap-2'):
                        ui.label(f"Bus #{bus_num}").classes('w-20 font-bold text-xs text-blue-900')
                        ui.label(message).classes('flex-1 text-xs text-slate-700 truncate')
                        
                        with ui.row().classes('w-24 justify-center'):
                            ui.label('PENDING').classes('text-[10px] px-2 py-0.5 rounded-full font-bold bg-amber-100 text-amber-800')

                        with ui.row().classes('w-36 justify-end gap-1'):
                            ui.button(
                                'Approve', 
                                on_click=lambda r_id=req_id, r=req: process_request(r_id, 'approved', r)
                            ).props('dense color=positive icon=check').classes('text-xs')

                            ui.button(
                                'Reject', 
                                on_click=lambda r_id=req_id, r=req: process_request(r_id, 'rejected', r)
                            ).props('dense color=negative icon=close').classes('text-xs')

    load_pending_requests()


def render_request_logs_panel():
    """Renders processed historical route request logs."""
    logs_container = ui.column().classes('w-full flex-1 gap-2 overflow-y-auto pr-1')

    def load_logs():
        logs_container.clear()
        
        try:
            raw_data = get_db_reference("request_logs").get() or {}
        except Exception:
            raw_data = {}

        if not raw_data:
            with logs_container:
                with ui.card().classes('w-full p-6 text-center bg-white rounded-lg shadow-sm border border-slate-200 mt-2'):
                    ui.icon('history', size='36px').classes('text-slate-300 mb-1 mx-auto')
                    ui.label('No processed request logs found.').classes('text-xs text-slate-500 font-medium')
            return

        with logs_container:
            # Table Header
            with ui.row().classes('w-full bg-slate-200 px-3 py-1.5 rounded-lg font-bold text-[11px] text-slate-700 uppercase items-center'):
                ui.label('Processed Time').classes('w-36')
                ui.label('Bus #').classes('w-16')
                ui.label('Message / Request Info').classes('flex-1')
                ui.label('Processed By').classes('w-32')
                ui.label('Status').classes('w-24 text-center')

            # Log Items
            for log_id, log in reversed(list(raw_data.items())):
                bus_num = log.get('bus_number', 'N/A')
                message = log.get('message', 'No details provided.')
                status = log.get('status', 'approved')
                processed_at = log.get('processed_at', 'N/A')
                action_by = log.get('action_by', 'System')

                status_bg = 'bg-green-100 text-green-800' if status == 'approved' else 'bg-red-100 text-red-800'

                with ui.card().classes('w-full bg-white p-2 rounded-lg shadow-sm border border-slate-200'):
                    with ui.row().classes('w-full justify-between items-center gap-2'):
                        ui.label(processed_at).classes('w-36 text-[10px] text-slate-500 font-mono')
                        ui.label(f"Bus #{bus_num}").classes('w-16 font-bold text-xs text-slate-800')
                        ui.label(message).classes('flex-1 text-xs text-slate-600 truncate')
                        ui.label(action_by).classes('w-32 text-xs text-slate-500 italic')
                        
                        with ui.row().classes('w-24 justify-center'):
                            ui.label(status.upper()).classes(f'text-[10px] px-2 py-0.5 rounded-full font-bold {status_bg}')

    load_logs()