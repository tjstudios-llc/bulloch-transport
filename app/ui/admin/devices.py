# app/ui/admin/devices.py

import logging
from nicegui import ui
from app.ui.admin.header import render_admin_header

from app.services.devices import (
    fetch_all_devices,
    search_devices,
    create_device,
    update_device,
    delete_device,
    generate_activation_code
)

logger = logging.getLogger(__name__)

# Allowed status options across device management
STATUS_OPTIONS = ['Active', 'Online', 'Offline', 'Maintenance', 'Inactive']


def render_admin_devices_page():
    """
    Admin Management Console optimized for mobile phones, touch tablets, and desktops.
    """
    # Shared Header Navigation
    render_admin_header(active_page="devices")

    # Responsive Outer Container (Fluid width and auto-height for phones)
    with ui.column().classes('w-full max-w-6xl min-h-[calc(100vh-80px)] p-2 md:p-4 bg-slate-100 gap-3 mx-auto'):
        
        with ui.card().classes('w-full bg-white p-3 md:p-5 rounded-xl shadow border border-slate-200 flex flex-col gap-3'):
            
            # -------------------------------------------------------------
            # 1. COMPACT ACTION HEADER
            # -------------------------------------------------------------
            with ui.row().classes('w-full justify-between items-center gap-2'):
                with ui.column().classes('gap-0'):
                    ui.label('Hardware Device Management').classes('text-base md:text-lg font-bold text-slate-800 leading-tight')
                    ui.label('Manage telematics units and generate activation codes').classes('text-[11px] text-slate-500')

                with ui.row().classes('gap-2 items-center'):
                    ui.button('+ Code / Device', on_click=lambda: open_add_dialog()).classes(
                        'bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-3 py-1.5 text-xs rounded-lg shadow'
                    )
                    ui.button('↻ Refresh', on_click=lambda: refresh_list(search_input.value)).classes(
                        'bg-blue-600 hover:bg-blue-500 text-white font-bold px-3 py-1.5 text-xs rounded-lg shadow'
                    )

            # -------------------------------------------------------------
            # 2. COMPACT SEARCH BAR
            # -------------------------------------------------------------
            with ui.row().classes('w-full gap-2 items-center'):
                search_input = ui.input(
                    placeholder='Search Serial, Bus #, Code, Model...'
                ).props('outlined dense icon=search').classes('flex-1 text-xs')
                
                ui.button('Clear', on_click=lambda: clear_search()).props('outline color=grey dense').classes('text-xs')

            # -------------------------------------------------------------
            # 3. DIRECTORY CONTAINER (Card Stack on Mobile / Table on Desktop)
            # -------------------------------------------------------------
            devices_container = ui.column().classes('w-full flex-1 gap-2 overflow-y-auto pr-1')

            def refresh_list(query: str = ""):
                devices_container.clear()
                records = search_devices(query) if query else fetch_all_devices()

                if not records:
                    with devices_container:
                        with ui.card().classes('w-full p-6 text-center bg-slate-50 border border-slate-200 rounded-lg'):
                            ui.icon('developer_board_off', size='36px').classes('text-slate-300 mb-1')
                            ui.label('No registered hardware devices found.').classes('text-slate-500 text-xs font-medium')
                    return

                # Desktop Table Header (Hidden on Mobile)
                with devices_container:
                    with ui.row().classes('w-full px-3 py-2 bg-slate-800 text-white font-bold text-[11px] rounded-md justify-between items-center shadow-sm gt-sm'):
                        ui.label('SERIAL NUMBER / MODEL').classes('w-1/4')
                        ui.label('STATUS').classes('w-1/12 text-center')
                        ui.label('ASSIGNED BUS').classes('w-1/6 text-center')
                        ui.label('ACTIVATION CODE').classes('w-1/6 text-center')
                        ui.label('LOCATION / BASE').classes('w-1/4')
                        ui.label('ACTIONS').classes('w-1/12 text-right')

                    # Device List Renderer
                    for device in records:
                        d_id = device.get('id', '')
                        d_serial = device.get('serial_number', 'N/A')
                        d_model = device.get('model', 'Standard Telematics Unit')
                        d_status = str(device.get('status', 'Active')).capitalize()
                        d_bus = device.get('assigned_bus') or device.get('bus_number', 'Unassigned')
                        d_code = device.get('activation_code', 'N/A')
                        d_loc = device.get('formatted_location', 'Location Unavailable')
                        
                        bus_str = f"Bus #{d_bus}" if str(d_bus).isdigit() else str(d_bus)
                        
                        # Dynamic badge styling based on status
                        if d_status in ['Active', 'Online']:
                            status_bg = 'bg-green-100 text-green-800'
                        elif d_status == 'Maintenance':
                            status_bg = 'bg-amber-100 text-amber-800'
                        else:
                            status_bg = 'bg-slate-200 text-slate-700'

                        # -------------------------------------------------
                        # A. MOBILE VIEW: Touch-Friendly Cards (Phone screens)
                        # -------------------------------------------------
                        with ui.card().classes('w-full p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-2 lt-md shadow-sm'):
                            with ui.row().classes('justify-between items-start w-full'):
                                with ui.column().classes('gap-0'):
                                    ui.label(d_serial).classes('font-mono font-bold text-slate-900 text-sm')
                                    ui.label(d_model).classes('text-xs text-slate-500')
                                
                                ui.label(d_status).classes(f'text-[10px] font-bold px-2 py-0.5 rounded-full {status_bg}')

                            with ui.row().classes('w-full justify-between items-center bg-white p-2 rounded-lg border border-slate-200/60 text-xs'):
                                ui.label(f"Bus: {bus_str}").classes('font-semibold text-slate-700')
                                ui.label(f"Code: {d_code}").classes('font-mono font-bold text-emerald-600')

                            with ui.row().classes('items-center gap-1 text-slate-600 text-xs'):
                                ui.icon('router', size='16px').classes('text-blue-500')
                                ui.label(d_loc).classes('truncate font-medium')

                            with ui.row().classes('w-full justify-end gap-2 pt-1 border-t border-slate-200'):
                                ui.button('Edit', icon='edit', on_click=lambda d=device: open_edit_dialog(d)).props('dense flat color=blue size=sm')
                                ui.button('Delete', icon='delete', on_click=lambda did=d_id, sn=d_serial: open_delete_dialog(did, sn)).props('dense flat color=red size=sm')

                        # -------------------------------------------------
                        # B. DESKTOP VIEW: Structured Table Row (Medium+ screens)
                        # -------------------------------------------------
                        with ui.row().classes('w-full px-3 py-2 bg-slate-50 border-b border-slate-200 text-xs text-slate-700 justify-between items-center hover:bg-slate-100 rounded-md transition-colors gt-sm'):
                            
                            # Serial & Model
                            with ui.column().classes('w-1/4 gap-0'):
                                ui.label(d_serial).classes('font-mono font-bold text-slate-900 leading-tight')
                                ui.label(d_model).classes('text-[10px] text-slate-500 truncate')

                            # Status Tag
                            ui.label(d_status).classes(f'w-1/12 text-[10px] font-bold px-1 py-0.5 rounded-full text-center {status_bg}')

                            # Assigned Bus
                            ui.label(bus_str).classes('w-1/6 font-semibold text-slate-700 text-center')

                            # Activation Code
                            ui.label(d_code).classes('w-1/6 font-mono font-bold text-emerald-600 text-center')

                            # Location
                            with ui.row().classes('w-1/4 items-center gap-1 text-slate-600'):
                                ui.icon('router', size='16px').classes('text-blue-500')
                                ui.label(d_loc).classes('text-[11px] truncate font-medium')

                            # Action Buttons
                            with ui.row().classes('w-1/12 justify-end items-center gap-1'):
                                ui.button(on_click=lambda d=device: open_edit_dialog(d)).props('dense flat color=blue icon=edit size=sm')
                                ui.button(on_click=lambda did=d_id, sn=d_serial: open_delete_dialog(did, sn)).props('dense flat color=red icon=delete size=sm')

            # -------------------------------------------------------------
            # DIALOG: REGISTER DEVICE OR GENERATE 6-DIGIT CODE
            # -------------------------------------------------------------
            def open_add_dialog():
                with ui.dialog() as dialog, ui.card().classes('w-full max-w-[420px] max-h-[85vh] p-4 flex flex-col gap-3 rounded-xl shadow-xl overflow-y-auto mx-2'):
                    ui.label('Hardware Registration Options').classes('text-base font-bold text-slate-800')

                    with ui.tabs().classes('w-full dense') as tabs:
                        tab_code = ui.tab('1. Activation Code')
                        tab_manual = ui.tab('2. Manual Entry')

                    with ui.tab_panels(tabs, value=tab_code).classes('w-full'):
                        
                        # Panel 1: Code Generator
                        with ui.tab_panel(tab_code).classes('flex flex-col gap-2 p-1'):
                            ui.label('Create an activation code for bus tablet.').classes('text-[11px] text-slate-500')
                            
                            code_bus_input = ui.input('Assigned Bus Number *', placeholder='e.g., 104').props('dense outlined').classes('w-full text-xs')
                            generated_code_display = ui.label('').classes('text-2xl font-mono font-bold text-center text-emerald-600 my-1 hidden')

                            def handle_generate_code():
                                bus_num = code_bus_input.value.strip()
                                if not bus_num:
                                    ui.notify('Please enter a bus number.', type='warning')
                                    return

                                code = generate_activation_code(bus_num)
                                if code:
                                    generated_code_display.set_text(f"Code: {code}")
                                    generated_code_display.classes(remove='hidden')
                                    ui.notify(f"Generated Code {code} for Bus #{bus_num}!", type='positive')
                                    refresh_list(search_input.value)
                                else:
                                    ui.notify('Failed to generate code.', type='negative')

                            ui.button('Generate 6-Digit Code', on_click=handle_generate_code).classes('w-full bg-emerald-600 text-white font-bold py-2 text-xs rounded-lg mt-1')

                        # Panel 2: Manual Device Entry
                        with ui.tab_panel(tab_manual).classes('flex flex-col gap-2 p-1'):
                            serial_input = ui.input('Serial Number *', placeholder='e.g., GPS-8820-GA').props('dense outlined').classes('w-full text-xs')
                            bus_input = ui.input('Assigned Bus #', placeholder='e.g., 104').props('dense outlined').classes('w-full text-xs')
                            model_input = ui.input('Device Model', value='In-Vehicle Telematics Unit').props('dense outlined').classes('w-full text-xs')
                            location_input = ui.input('Initial Depot / Location', value='Bulloch County Bus Garage, Statesboro, GA').props('dense outlined').classes('w-full text-xs')
                            status_select = ui.select(STATUS_OPTIONS, value='Active', label='Status').props('dense outlined').classes('w-full text-xs')

                            def save_manual_device():
                                sn = serial_input.value.strip()
                                if not sn:
                                    ui.notify('Serial Number is required.', type='warning')
                                    return

                                payload = {
                                    "serial_number": sn,
                                    "assigned_bus": bus_input.value.strip(),
                                    "bus_number": bus_input.value.strip(),
                                    "model": model_input.value.strip(),
                                    "address": location_input.value.strip(),
                                    "status": status_select.value
                                }
                                if create_device(payload):
                                    ui.notify(f"Device '{sn}' registered successfully!", type='positive')
                                    dialog.close()
                                    refresh_list(search_input.value)
                                else:
                                    ui.notify('Failed to create device.', type='negative')

                            ui.button('Register Device Directly', on_click=save_manual_device).classes('w-full bg-blue-600 text-white font-bold py-2 text-xs rounded-lg mt-1')

                    with ui.row().classes('w-full justify-end mt-1'):
                        ui.button('Close', on_click=dialog.close).props('flat text-color=grey dense')

                dialog.open()

            # -------------------------------------------------------------
            # DIALOG: EDIT DEVICE
            # -------------------------------------------------------------
            def open_edit_dialog(device: dict):
                with ui.dialog() as dialog, ui.card().classes('w-full max-w-[380px] max-h-[85vh] p-4 flex flex-col gap-2 rounded-xl shadow-xl overflow-y-auto mx-2'):
                    ui.label('Edit Device Record').classes('text-base font-bold text-slate-800')

                    edit_serial = ui.input('Serial Number', value=device.get('serial_number', '')).props('dense outlined').classes('w-full text-xs')
                    edit_bus = ui.input('Assigned Bus #', value=str(device.get('assigned_bus') or device.get('bus_number', ''))).props('dense outlined').classes('w-full text-xs')
                    edit_model = ui.input('Device Model', value=device.get('model', '')).props('dense outlined').classes('w-full text-xs')
                    edit_location = ui.input('Current Location / Depot', value=device.get('formatted_location', '')).props('dense outlined').classes('w-full text-xs')
                    
                    # Safe fallback logic to prevent NiceGUI ValueError
                    raw_status = str(device.get('status', 'Active')).capitalize()
                    initial_status = raw_status if raw_status in STATUS_OPTIONS else 'Active'
                    edit_status = ui.select(STATUS_OPTIONS, value=initial_status, label='Status').props('dense outlined').classes('w-full text-xs')

                    def save_device_changes():
                        payload = {
                            "serial_number": edit_serial.value.strip(),
                            "assigned_bus": edit_bus.value.strip(),
                            "bus_number": edit_bus.value.strip(),
                            "model": edit_model.value.strip(),
                            "address": edit_location.value.strip(),
                            "status": edit_status.value
                        }
                        if update_device(device['id'], payload):
                            ui.notify(f"Updated device '{edit_serial.value}'!", type='positive')
                            dialog.close()
                            refresh_list(search_input.value)
                        else:
                            ui.notify('Failed to update device.', type='negative')

                    with ui.row().classes('w-full justify-end gap-2 mt-2'):
                        ui.button('Cancel', on_click=dialog.close).props('flat text-color=grey dense')
                        ui.button('Save Changes', on_click=save_device_changes).classes('bg-blue-600 text-white font-bold text-xs px-3 py-1.5 rounded-lg')

                dialog.open()

            # -------------------------------------------------------------
            # DIALOG: DELETE CONFIRMATION
            # -------------------------------------------------------------
            def open_delete_dialog(device_id: str, serial_num: str):
                with ui.dialog() as dialog, ui.card().classes('w-full max-w-[320px] p-4 flex flex-col gap-3 rounded-xl shadow-xl mx-2'):
                    ui.label('Delete Device Record').classes('text-base font-bold text-red-600')
                    ui.label(f"Are you sure you want to remove device '{serial_num}'?").classes('text-xs text-slate-600')

                    def confirm_delete():
                        if delete_device(device_id):
                            ui.notify(f"Device '{serial_num}' deleted.", type='info')
                            dialog.close()
                            refresh_list(search_input.value)
                        else:
                            ui.notify('Failed to delete device.', type='negative')

                    with ui.row().classes('w-full justify-end gap-2 mt-2'):
                        ui.button('Cancel', on_click=dialog.close).props('flat text-color=grey dense')
                        ui.button('Delete Device', on_click=confirm_delete).classes('bg-red-600 text-white font-bold text-xs px-3 py-1.5 rounded-lg')

                dialog.open()

            def on_search_change(e):
                refresh_list(e.value)

            def clear_search():
                search_input.set_value('')
                refresh_list('')

            search_input.on('update:model-value', on_search_change)
            refresh_list()