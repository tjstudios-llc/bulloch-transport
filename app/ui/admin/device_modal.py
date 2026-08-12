# app/ui/admin/device_modal.py

from nicegui import ui
from app.services.devices import generate_activation_code


def open_device_registration_dialog():
    """
    Opens a dialog modal allowing admins to create a new 6-digit activation key for a bus.
    """
    with ui.dialog() as dialog, ui.card().classes('w-96 p-6 flex flex-col gap-4 rounded-2xl shadow-2xl'):
        ui.label('Register Hardware Device').classes('text-xl font-bold text-slate-800')
        ui.label('Select or enter a bus number to generate an activation code for hardware setup.').classes('text-xs text-slate-500')

        bus_input = ui.input('Bus Number / ID', placeholder='e.g., 104').classes('w-full').props('outlined dense')

        # Container for the generated code display
        result_container = ui.column().classes('w-full items-center justify-center')

        def on_generate():
            bus_num = bus_input.value.strip()
            if not bus_num:
                ui.notify('Please enter a bus number.', type='warning')
                return

            code = generate_activation_code(bus_num)
            result_container.clear()

            if code:
                with result_container:
                    ui.label('ACTIVATION CODE').classes('text-xs font-bold text-slate-400 mt-2')
                    # Displays code large and monospaced for readability
                    ui.label(code).classes(
                        'text-4xl font-extrabold font-mono tracking-widest text-emerald-600 bg-emerald-50 px-6 py-3 rounded-xl border border-emerald-200 shadow-inner my-2'
                    )
                    ui.label(f'Assigned to Bus #{bus_num}').classes('text-xs font-medium text-slate-600')
                    ui.notify('Activation code created!', type='positive')
            else:
                ui.notify('Failed to generate code. Try again.', type='negative')

        with ui.row().classes('w-full justify-end gap-2 mt-4'):
            ui.button('Close', on_click=dialog.close).props('flat color=grey')
            ui.button('Generate Code', on_click=on_generate).classes('bg-emerald-600 hover:bg-emerald-500 text-white font-bold')

    dialog.open()