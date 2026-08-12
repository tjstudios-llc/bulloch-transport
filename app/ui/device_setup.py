# app/ui/device_setup.py

import logging
from nicegui import app, ui
from app.services.devices import verify_activation_code, register_activated_device

logger = logging.getLogger(__name__)


def render_device_setup_page():
    """
    Isolated Hardware Device Activation Screen.
    Publicly accessible, but contains NO navigation links to the admin console.
    """
    with ui.column().classes('w-full min-h-screen bg-slate-900 justify-center items-center p-4'):
        
        with ui.card().classes('w-full max-w-md p-8 bg-white rounded-2xl shadow-2xl flex flex-col gap-6 text-center'):
            
            # Header
            with ui.column().classes('items-center w-full gap-1'):
                ui.icon('sensors', size='48px').classes('text-emerald-600')
                ui.label('Hardware Device Activation').classes('text-2xl font-bold text-slate-800')
                ui.label('Enter the 6-digit code displayed on your Admin Dashboard.').classes('text-sm text-slate-500')

            ui.separator()

            # Input field for pairing code
            code_input = ui.input('Activation Code', placeholder='e.g., 482910').props(
                'outlined dense input-class="text-center text-2xl tracking-widest font-mono"'
            ).classes('w-full')

            def activate_device():
                code = code_input.value.strip()
                if not code or len(code) != 6 or not code.isdigit():
                    ui.notify('Please enter a valid 6-digit activation code.', type='warning')
                    return

                # 1. Verify code against Realtime Database
                code_data = verify_activation_code(code)

                if code_data:
                    assigned_bus = code_data.get('assigned_bus', 'Unassigned')
                    
                    # 2. Register hardware device in RTDB and mark activation code as claimed
                    success = register_activated_device(
                        activation_code=code,
                        device_info={
                            "model": "In-Vehicle Telematics Unit",
                            "serial_number": f"SN-BUS{assigned_bus}-GPS"
                        },
                        bus_assignment=assigned_bus,
                        permissions={"location": True, "serial": True, "telemetry": True}
                    )

                    if success:
                        # 3. Store assigned device identity in session storage
                        app.storage.user['device_id'] = f"bus_{assigned_bus}"
                        app.storage.user['bus_number'] = assigned_bus

                        ui.notify(f'Successfully activated for Bus #{assigned_bus}!', type='positive')
                        ui.navigate.to('/')
                    else:
                        ui.notify('Failed to save device activation. Please try again.', type='negative')
                else:
                    ui.notify('Invalid, expired, or already claimed code.', type='negative')

            ui.button('Verify & Connect Device', on_click=activate_device).classes(
                'w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3 rounded-xl shadow'
            )

            ui.button('Back to Login', on_click=lambda: ui.navigate.to('/login')).props('flat color=grey').classes('text-xs mt-2')