# app/ui/admin/header.py

from nicegui import ui


def render_admin_header(active_page: str = "map"):
    """
    Unified Mobile & Desktop Admin Navigation Component.
    
    :param active_page: Identifier for the active page ('map', 'routes', 'users', 'devices')
    """
    
    # ------------------------------------------------------------------
    # 1. MOBILE DRAWER (Rendered OUTSIDE the header element)
    # ------------------------------------------------------------------
    with ui.left_drawer(value=False).classes('bg-slate-900 text-white p-4 space-y-4 lt-md') as drawer:
        ui.label('ADMIN MENU').classes('text-xs font-bold text-slate-400 tracking-wider mb-2')
        
        nav_items = [
            ('map', 'Live Map', 'map', '/admin'),
            ('routes', 'Route Management', 'alt_route', '/admin/routes'),
            ('users', 'User Directory', 'people', '/admin/users'),
            ('devices', 'Device Management', 'devices', '/admin/devices'),
        ]
        
        with ui.column().classes('w-full gap-2'):
            for page_id, label, icon_name, path in nav_items:
                is_active = active_page == page_id
                bg_cls = 'bg-blue-600 text-white font-bold' if is_active else 'text-slate-300 hover:bg-slate-800'
                
                ui.button(
                    label, 
                    icon=icon_name, 
                    on_click=lambda p=path: ui.navigate.to(p)
                ).classes(f'w-full justify-start text-left rounded-lg py-2.5 px-3 {bg_cls}').props('flat')
            
            ui.element('div').classes('h-[1px] bg-slate-800 my-2 w-full')
            
            ui.button('🚌 Driver View', on_click=lambda: ui.navigate.to('/')).classes(
                'w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-2.5 px-3 rounded-lg text-center'
            ).props('flat')

    # ------------------------------------------------------------------
    # 2. TOP HEADER BAR
    # ------------------------------------------------------------------
    with ui.header().classes('bg-slate-900 text-white px-4 md:px-6 py-3 justify-between items-center shadow-md'):
        
        # Left Side: Hamburger Menu Button (Mobile) + Branding Title
        with ui.row().classes('items-center gap-2 md:gap-3'):
            # Hamburger Icon (Only visible on screens smaller than medium/tablet)
            ui.button(icon='menu', on_click=drawer.toggle) \
              .props('flat round color=white') \
              .classes('lt-md')

            # Branding Logo & Text
            with ui.row().classes('items-center gap-2 cursor-pointer').on('click', lambda: ui.navigate.to('/admin')):
                ui.icon('directions_bus', size='28px').classes('text-blue-400')
                # Desktop Title
                ui.label('Bulloch County Schools — Admin').classes('gt-xs text-xl font-bold tracking-wide')
                # Mobile Title (Shorter string for tiny phone viewports)
                ui.label('Bulloch Admin').classes('lt-sm text-lg font-bold tracking-wide')

        # Right Side: Desktop Navigation Links (Only visible on medium/large screens)
        with ui.row().classes('gt-sm gap-2 items-center'):
            
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

            # Quick Toggle to Driver App
            ui.button('🚌 Driver View', on_click=lambda: ui.navigate.to('/')).classes(
                'bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold py-2 px-3 rounded-lg shadow transition-all'
            )