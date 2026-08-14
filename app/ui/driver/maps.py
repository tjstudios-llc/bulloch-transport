# app/ui/driver/maps.py

import logging
from nicegui import app, ui
from app.services.routes import fetch_active_route_for_bus, update_stop_status_in_firestore
from app.services.firebase import get_db_reference

logger = logging.getLogger(__name__)


def render_driver_maps_page():
    """
    Renders the driver navigation and live route map interface (Optimized for 1024x600 Kiosks).
    """
    active_bus = app.storage.user.get('bus_number', '104')
    active_route = fetch_active_route_for_bus(active_bus)
    user_role = app.storage.user.get('role', '')

    # --- Header Navigation Bar ---
    with ui.header().classes('bg-blue-900 text-white px-3 py-1.5 justify-between items-center shadow-md h-11 shrink-0'):
        with ui.row().classes('items-center gap-2'):
            ui.label('🚌 Bulloch Schools — Driver Navigation Map').classes('text-sm font-bold tracking-wide')
            ui.label(f"Bus #{active_bus}").classes('bg-blue-700 px-2 py-0.5 rounded-full text-[11px] font-bold')

        with ui.row().classes('items-center gap-2'):
            ui.button('🏠 Dashboard', on_click=lambda: ui.navigate.to('/driver')).props('dense flat color=white text-color=white').classes('text-xs font-bold')
            if user_role in ('admin', 'dispatch', 'dispatcher'):
                ui.button('⚙️ Admin Console', on_click=lambda: ui.navigate.to('/admin/routes')).props('dense flat color=white text-color=white').classes('text-xs')

    # --- Viewport Container ---
    with ui.column().classes('w-full max-w-[1024px] h-[556px] p-2 bg-slate-100 justify-between overflow-hidden mx-auto gap-2'):
        
        with ui.row().classes('w-full bg-white px-3 py-1.5 rounded-lg shadow-sm border border-slate-200 items-center justify-between shrink-0'):
            with ui.row().classes('items-center gap-2'):
                bus_input = ui.input(value=active_bus).props('dense outlined').classes('w-24 text-xs')
                
                def load_new_bus_route():
                    app.storage.user['bus_number'] = bus_input.value.strip()
                    ui.navigate.reload()

                ui.button('Load Bus', on_click=load_new_bus_route).props('dense').classes('bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs px-3 py-1 rounded-md')

            if active_route:
                ui.label(f"{active_route.get('name')} ({active_route.get('shift', 'Daily')} Shift)").classes('text-xs font-bold text-slate-800')

        # --- Fallback: No Route Assigned ---
        if not active_route:
            with ui.card().classes('w-full flex-1 p-6 text-center bg-amber-50 border border-amber-200 rounded-xl justify-center items-center gap-3 shadow-sm'):
                ui.label(f"⚠️ No active route assigned to Bus #{active_bus}.").classes('text-lg font-bold text-amber-900')
                ui.label("Verify the bus number above or request dispatch to assign a route.").classes('text-xs text-amber-700')
                
                async def request_route_from_dispatch():
                    btn_req.props('loading')
                    try:
                        request_payload = {
                            'bus_number': active_bus,
                            'timestamp': {'.sv': 'timestamp'},
                            'status': 'pending',
                            'message': f"Bus #{active_bus} driver requested route dispatch from Map view."
                        }
                        get_db_reference("route_requests").push(request_payload)
                        ui.notify(f"Route requested for Bus #{active_bus}! Dispatch notified.", type='positive', position='top')
                    except Exception as e:
                        logger.error(f"Failed to submit route request: {e}")
                        ui.notify("Failed to send request. Check network connection.", type='warning', position='top')
                    finally:
                        btn_req.props(remove='loading')

                btn_req = ui.button(
                    '📥 REQUEST ROUTE FROM ADMIN', 
                    on_click=request_route_from_dispatch
                ).classes('bg-blue-600 hover:bg-blue-500 text-white font-black text-xs py-2 px-5 rounded-lg shadow active:scale-95')

            return

        route_id = active_route['id']
        stops = active_route.get('stops', [])
        polyline = active_route.get('path_polyline', [])

        # --- Split View (Manifest + Map) ---
        with ui.row().classes('w-full flex-1 gap-2 items-stretch overflow-hidden min-h-0'):
            with ui.card().classes('w-80 bg-white p-2.5 rounded-xl shadow-sm border border-slate-200 flex flex-col h-full overflow-hidden shrink-0 gap-2'):
                with ui.row().classes('w-full justify-between items-center border-b pb-1.5 shrink-0'):
                    ui.label('Route Manifest').classes('text-xs font-bold text-slate-800 uppercase tracking-wider')
                    ui.label(f"{len(stops)} Stops").classes('text-[10px] text-slate-500 font-semibold')

                manifest_container = ui.column().classes('w-full flex-1 overflow-y-auto gap-1.5 pr-1')

                def render_manifest():
                    manifest_container.clear()
                    for idx, stop in enumerate(stops):
                        status = stop.get('status', 'pending')
                        
                        bg_color = 'bg-slate-50 border-slate-200'
                        if status == 'completed':
                            bg_color = 'bg-green-50 border-green-200'
                        elif status == 'next':
                            bg_color = 'bg-blue-50 border-blue-300 ring-1 ring-blue-400'

                        with manifest_container:
                            with ui.row().classes(f'w-full justify-between items-center p-2 rounded-lg border {bg_color} text-xs'):
                                with ui.column().classes('gap-0 flex-1 overflow-hidden mr-1'):
                                    ui.label(f"{idx + 1}. {stop['name']}").classes('font-bold text-slate-800 truncate')
                                    if stop.get('street_name'):
                                        ui.label(stop.get('street_name')).classes('text-[10px] text-slate-500 truncate')

                                async def mark_arrived(s_idx=idx):
                                    stops[s_idx]['status'] = 'completed'
                                    if s_idx + 1 < len(stops):
                                        stops[s_idx + 1]['status'] = 'next'
                                    
                                    update_stop_status_in_firestore(route_id, stops)
                                    render_manifest()
                                    render_driver_map()

                                if status == 'completed':
                                    ui.label('✓ Done').classes('text-[11px] font-bold text-green-700 shrink-0')
                                else:
                                    ui.button('ARRIVED', on_click=mark_arrived).props('dense').classes(
                                        'bg-green-600 hover:bg-green-500 text-white text-[10px] font-bold py-1 px-2.5 rounded-md shadow shrink-0 active:scale-95'
                                    )

                render_manifest()

            with ui.card().classes('flex-1 bg-white p-1.5 rounded-xl shadow-sm border border-slate-200 flex flex-col h-full overflow-hidden min-w-0'):
                driver_map = ui.leaflet(center=(32.4488, -81.7832), zoom=13).classes('w-full h-full rounded-lg')
                driver_map.options['zoomControl'] = False

                def render_driver_map():
                    driver_map.tile_layer(url_template='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png')

                    if polyline:
                        driver_map.generic_layer(
                            name='polyline',
                            args=[polyline, {'color': '#2563eb', 'weight': 6, 'opacity': 0.85}]
                        )
                        driver_map.set_center(polyline[0])
                    elif stops:
                        driver_map.set_center((stops[0]['lat'], stops[0]['lng']))

                    for stop in stops:
                        driver_map.marker(latlng=(stop['lat'], stop['lng']))

                render_driver_map()