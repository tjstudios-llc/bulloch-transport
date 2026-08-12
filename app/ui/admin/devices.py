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


def render_admin_devices_page():
    """
    Admin Management Console for GPS / Telematics hardware units and activation codes.
    """
    
    # Shared Header Navigation
    render_admin_header(active_page="devices")

    # Main Container
    with ui.column().classes('w-full p-6 bg-slate-100 min-h-screen gap-6'):
        
        with ui.card().classes('w-full bg-white p-6 rounded-xl shadow border border-slate-200 flex flex-col gap-4'):
            
            # Title Bar & Action Buttons
            with ui.row().classes('w-full justify-between items-center'):
                with ui.column().classes('gap-0'):
                    ui.label('Hardware Device Management').classes('text-2xl font-bold text-slate-800')
                    ui.label('Manage telematics units and generate 6-digit activation codes').classes('text-xs text-slate-500')

                with ui.row().classes('gap-3'):
                    ui.button('+ Generate Code / Add Device', on_click=lambda: open_add_dialog()).classes(
                        'bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-4 py-2 rounded-lg shadow transition-all'
                    )
                    ui.button('↻ Refresh Directory', on_click=lambda: refresh_list(search_input.value)).classes(
                        'bg-blue-600 hover:bg-blue-500 text-white font-bold px-4 py-2 rounded-lg transition-all'
                    )

            # Search Bar
            with ui.row().classes('w-full gap-4 items-center'):
                search_input = ui.input(
                    placeholder='Search by Serial Number, Bus #, Code, or Model...'
                ).props('outlined dense icon=search').classes('flex-1')
                
                ui.button('Clear', on_click=lambda: clear_search()).props('outline color=grey')

            # List Container
            devices_container = ui.column().classes('w-full gap-2 mt-4')

            def refresh_list(query: str = ""):
                devices_container.clear()
                records = search_devices(query) if query else fetch_all_devices()

                if not records:
                    with devices_container:
                        with ui.card().classes('w-full p-8 text-center bg-slate-50 border border-slate-200 rounded-lg'):
                            ui.icon('developer_board_off', size='48px').classes('text-slate-300 mb-2')
                            ui.label('No registered hardware devices found.').classes('text-slate-500 font-medium')
                    return

                # Table Header
                with devices_container:
                    with ui.row().classes('w-full p-3 bg-slate-800 text-white font-bold text-xs rounded-lg justify-between items-center shadow-sm'):
                        ui.label('SERIAL NUMBER / MODEL').classes('w-1/4')
                        ui.label('STATUS').classes('w-1/12')
                        ui.label('ASSIGNED BUS').classes('w-1/6')
                        ui.label('ACTIVATION CODE').classes('w-1/6')
                        ui.label('LOCATION / BASE').classes('w-1/4')
                        ui.label('ACTIONS').classes('w-1/12 text-right')

                    # Table Data Rows
                    for device in records:
                        d_id = device.get('id', '')
                        d_serial = device.get('serial_number', 'N/A')
                        d_model = device.get('model', 'Standard Telematics Unit')
                        d_status = str(device.get('status', 'Active')).capitalize()
                        d_bus = device.get('assigned_bus') or device.get('bus_number', 'Unassigned')
                        d_code = device.get('activation_code', 'N/A')
                        d_loc = device.get('formatted_location', 'Location Unavailable')

                        with ui.row().classes('w-full p-3 bg-slate-50 border-b border-slate-200 text-sm text-slate-700 justify-between items-center hover:bg-slate-100 transition-colors rounded-lg'):
                            
                            # Serial & Model
                            with ui.column().classes('w-1/4 gap-0'):
                                ui.label(d_serial).classes('font-mono font-bold text-slate-900')
                                ui.label(d_model).classes('text-xs text-slate-500')

                            # Status Tag
                            status_bg = 'bg-green-100 text-green-800' if d_status == 'Active' else 'bg-amber-100 text-amber-800'
                            ui.label(d_status).classes(f'w-1/12 text-xs font-bold px-2 py-1 rounded-full text-center {status_bg}')

                            # Assigned Bus
                            bus_str = f"Bus #{d_bus}" if str(d_bus).isdigit() else str(d_bus)
                            ui.label(bus_str).classes('w-1/6 font-semibold text-slate-700')

                            # Activation Code
                            ui.label(d_code).classes('w-1/6 font-mono font-semibold text-emerald-600')

                            # Location
                            with ui.row().classes('w-1/4 items-center gap-1 text-slate-600'):
                                ui.icon('router', size='18px').classes('text-blue-500')
                                ui.label(d_loc).classes('text-xs truncate font-medium')

                            # Action Buttons
                            with ui.row().classes('w-1/12 justify-end items-center gap-1'):
                                ui.button(on_click=lambda d=device: open_edit_dialog(d)).props('dense flat color=blue icon=edit')
                                ui.button(on_click=lambda did=d_id, sn=d_serial: open_delete_dialog(did, sn)).props('dense flat color=red icon=delete')

            # --- DIALOG: REGISTER DEVICE OR GENERATE 6-DIGIT CODE ---
            def open_add_dialog():
                with ui.dialog() as dialog, ui.card().classes('w-full max-w-md p-6 flex flex-col gap-4 rounded-xl shadow-xl'):
                    ui.label('Hardware Registration Options').classes('text-lg font-bold text-slate-800')

                    with ui.tabs().classes('w-full') as tabs:
                        tab_code = ui.tab('1. Generate Activation Code')
                        tab_manual = ui.tab('2. Manual Registration')

                    with ui.tab_panels(tabs, value=tab_code).classes('w-full'):
                        
                        # Panel 1: Generate 6-digit Code for Bus Tablet
                        with ui.tab_panel(tab_code).classes('flex flex-col gap-4'):
                            ui.label('Create a 1-year, single-use activation code for tablet setup on the vehicle.').classes('text-xs text-slate-500')
                            
                            code_bus_input = ui.input('Assigned Bus Number *', placeholder='e.g., 104').classes('w-full')
                            generated_code_display = ui.label('').classes('text-3xl font-mono font-bold text-center text-emerald-600 my-2 hidden')

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

                            ui.button('Generate 6-Digit Code', on_click=handle_generate_code).classes('w-full bg-emerald-600 text-white font-bold py-2 rounded-lg')

                        # Panel 2: Manual Device Entry
                        with ui.tab_panel(tab_manual).classes('flex flex-col gap-3'):
                            serial_input = ui.input('Serial Number *', placeholder='e.g., GPS-8820-GA').classes('w-full')
                            bus_input = ui.input('Assigned Bus #', placeholder='e.g., 104').classes('w-full')
                            model_input = ui.input('Device Model', value='In-Vehicle Telematics Unit').classes('w-full')
                            location_input = ui.input('Initial Depot / Location', value='Bulloch County Bus Garage, Statesboro, GA').classes('w-full')
                            status_select = ui.select(['Active', 'Maintenance', 'Inactive'], value='Active', label='Status').classes('w-full')

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

                            ui.button('Register Device Directly', on_click=save_manual_device).classes('w-full bg-blue-600 text-white font-bold py-2 rounded-lg')

                    with ui.row().classes('w-full justify-end mt-2'):
                        ui.button('Close', on_click=dialog.close).props('flat text-color=grey')

                dialog.open()

            # --- DIALOG: EDIT DEVICE ---
            def open_edit_dialog(device: dict):
                with ui.dialog() as dialog, ui.card().classes('w-96 p-6 flex flex-col gap-4 rounded-xl shadow-xl'):
                    ui.label('Edit Device Record').classes('text-lg font-bold text-slate-800')

                    edit_serial = ui.input('Serial Number', value=device.get('serial_number', '')).classes('w-full')
                    edit_bus = ui.input('Assigned Bus #', value=str(device.get('assigned_bus') or device.get('bus_number', ''))).classes('w-full')
                    edit_model = ui.input('Device Model', value=device.get('model', '')).classes('w-full')
                    edit_location = ui.input('Current Location / Depot', value=device.get('formatted_location', '')).classes('w-full')
                    edit_status = ui.select(['Active', 'Maintenance', 'Inactive'], value=device.get('status', 'Active').capitalize(), label='Status').classes('w-full')

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

                    with ui.row().classes('w-full justify-end gap-2 mt-4'):
                        ui.button('Cancel', on_click=dialog.close).props('flat text-color=grey')
                        ui.button('Save Changes', on_click=save_device_changes).classes('bg-blue-600 text-white font-bold')

                dialog.open()

            # --- DIALOG: DELETE CONFIRMATION ---
            def open_delete_dialog(device_id: str, serial_num: str):
                with ui.dialog() as dialog, ui.card().classes('w-96 p-6 flex flex-col gap-4 rounded-xl shadow-xl'):
                    ui.label('Delete Device Record').classes('text-lg font-bold text-red-600')
                    ui.label(f"Are you sure you want to remove device '{serial_num}'?").classes('text-sm text-slate-600')

                    def confirm_delete():
                        if delete_device(device_id):
                            ui.notify(f"Device '{serial_num}' deleted.", type='info')
                            dialog.close()
                            refresh_list(search_input.value)
                        else:
                            ui.notify('Failed to delete device.', type='negative')

                    with ui.row().classes('w-full justify-end gap-2 mt-4'):
                        ui.button('Cancel', on_click=dialog.close).props('flat text-color=grey')
                        ui.button('Delete Device', on_click=confirm_delete).classes('bg-red-600 text-white font-bold')

                dialog.open()

            def on_search_change(e):
                refresh_list(e.value)

            def clear_search():
                search_input.set_value('')
                refresh_list('')

            search_input.on('update:model-value', on_search_change)
            refresh_list()