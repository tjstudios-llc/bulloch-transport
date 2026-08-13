# app/ui/admin/header.py

from nicegui import ui


def render_admin_header(active_page: str = "map"):
    """
    Unified Admin Navigation Header Component.
    
    :param active_page: Identifier for the active page ('map', 'routes', 'users', 'devices')
    """
    with ui.header().classes('bg-slate-900 text-white px-6 py-4 justify-between items-center shadow-md'):
        
        # Branding / Logo Title
        with ui.row().classes('items-center gap-3 cursor-pointer').on('click', lambda: ui.navigate.to('/admin')):
            ui.icon('directions_bus', size='28px').classes('text-blue-400')
            ui.label('Bulloch County Schools — Admin Console').classes('text-xl font-bold tracking-wide')

        # Navigation Links
        with ui.row().classes('gap-2 items-center'):
            
            def nav_props(page_id: str):
                is_active = active_page == page_id
                color = "color=blue-400 font-bold" if is_active else "color=white opacity-80"
                return f"flat {color}"

            ui.button('Live Map', on_click=lambda: ui.navigate.to('/admin')).props(nav_props('map'))
            ui.button('Route Management', on_click=lambda: ui.navigate.to('/admin/routes')).props(nav_props('routes'))
            ui.button('User Directory', on_click=lambda: ui.navigate.to('/admin/users')).props(nav_props('users'))
            ui.button('Device Management', on_click=lambda: ui.navigate.to('/admin/devices')).props(nav_props('devices'))

            # Divider
            ui.element('div').classes('h-6 w-[1px] bg-slate-700 mx-2')

            # Driver App Quick Toggle
            ui.button('🚌 Driver View', on_click=lambda: ui.navigate.to('/')).classes(
                'bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold py-2 px-3 rounded-lg shadow transition-all'
            )