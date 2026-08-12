# app/ui/admin/users.py

from nicegui import ui
from app.ui.admin.header import render_admin_header
from app.services.users import (
    fetch_all_users,
    search_users,
    update_user,
    delete_user
)


def render_admin_users_page():
    """
    Admin Directory for viewing, searching, editing, and deleting system users and drivers.
    """
    
    # Header Bar
    render_admin_header(active_page="users")

    # Main Body Container
    with ui.column().classes('w-full p-6 bg-slate-100 min-h-screen gap-6'):
        
        with ui.card().classes('w-full bg-white p-6 rounded-xl shadow border border-slate-200 flex flex-col gap-4'):
            
            # Title & Action Row
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('User & Driver Directory').classes('text-2xl font-bold text-slate-800')
                ui.button('↻ Refresh Directory', on_click=lambda: refresh_list()).classes(
                    'bg-blue-600 hover:bg-blue-500 text-white font-bold px-4 py-2 rounded-lg'
                )

            # Search Bar
            with ui.row().classes('w-full gap-4 items-center'):
                search_input = ui.input(
                    placeholder='Search by name, email, or bus number...'
                ).props('outlined dense icon=search').classes('flex-1')
                
                ui.button('Clear', on_click=lambda: clear_search()).props('outline color=grey')

            # Table Container
            users_container = ui.column().classes('w-full gap-2 mt-4')

            def refresh_list(query: str = ""):
                users_container.clear()
                user_records = search_users(query) if query else fetch_all_users()

                if not user_records:
                    with users_container:
                        with ui.card().classes('w-full p-8 text-center bg-slate-50 border border-slate-200 rounded-lg'):
                            ui.icon('group_off', size='48px').classes('text-slate-300 mb-2')
                            ui.label('No users or drivers found.').classes('text-slate-500 font-medium')
                    return

                # Header Row
                with users_container:
                    with ui.row().classes('w-full p-3 bg-slate-800 text-white font-bold text-xs rounded-lg justify-between items-center shadow-sm'):
                        ui.label('NAME & EMAIL').classes('w-1/4')
                        ui.label('ROLE').classes('w-1/12')
                        ui.label('ASSIGNED BUS').classes('w-1/6')
                        ui.label('CURRENT LOCATION (STREET, CITY, STATE)').classes('w-1/3')
                        ui.label('ACTIONS').classes('w-1/6 text-right')

                    # Data Rows
                    for user in user_records:
                        u_id = user.get('id')
                        u_name = user.get('name', 'N/A')
                        u_email = user.get('email', 'No Email')
                        u_role = user.get('role', 'driver').capitalize()
                        u_bus = user.get('assigned_bus') or user.get('bus_number', 'Unassigned')
                        u_loc = user.get('formatted_location', 'Location Unavailable')

                        with ui.row().classes('w-full p-3 bg-slate-50 border-b border-slate-200 text-sm text-slate-700 justify-between items-center hover:bg-slate-100 transition-colors rounded-lg'):
                            
                            # Name / Email Column
                            with ui.column().classes('w-1/4 gap-0'):
                                ui.label(u_name).classes('font-bold text-slate-900')
                                ui.label(u_email).classes('text-xs text-slate-500 truncate')

                            # Role
                            role_color = 'bg-purple-100 text-purple-800' if u_role == 'Admin' else 'bg-blue-100 text-blue-800'
                            ui.label(u_role).classes(f'w-1/12 text-xs font-bold px-2 py-1 rounded-full text-center {role_color}')

                            # Bus
                            bus_str = f"Bus #{u_bus}" if str(u_bus).isdigit() else str(u_bus)
                            ui.label(bus_str).classes('w-1/6 font-semibold text-slate-700')

                            # Clean Street Address (No Lat/Lng display)
                            with ui.row().classes('w-1/3 items-center gap-1 text-slate-600'):
                                ui.icon('place', size='18px').classes('text-red-500')
                                ui.label(u_loc).classes('text-xs truncate font-medium')

                            # Edit & Delete Buttons
                            with ui.row().classes('w-1/6 justify-end items-center gap-2'):
                                ui.button('Edit', on_click=lambda u=user: open_edit_dialog(u)).props('dense color=blue icon=edit')
                                ui.button('Delete', on_click=lambda uid=u_id, name=u_name: open_delete_dialog(uid, name)).props('dense color=red icon=delete')

            # --- DIALOG: EDIT USER INFO ---
            def open_edit_dialog(user: dict):
                with ui.dialog() as dialog, ui.card().classes('w-96 p-6 flex flex-col gap-4 rounded-xl shadow-xl'):
                    ui.label('Edit User Info').classes('text-lg font-bold text-slate-800')

                    edit_name = ui.input('Full Name', value=user.get('name', '')).classes('w-full')
                    edit_email = ui.input('Email Address', value=user.get('email', '')).classes('w-full')
                    edit_bus = ui.input('Assigned Bus #', value=str(user.get('assigned_bus') or user.get('bus_number', ''))).classes('w-full')
                    edit_role = ui.select(['driver', 'admin', 'dispatcher'], value=user.get('role', 'driver'), label='Role').classes('w-full')
                    edit_location = ui.input('Custom Address / Location', value=user.get('formatted_location', '')).classes('w-full')

                    def save_user_changes():
                        payload = {
                            "name": edit_name.value.strip(),
                            "email": edit_email.value.strip(),
                            "assigned_bus": edit_bus.value.strip(),
                            "bus_number": edit_bus.value.strip(),
                            "role": edit_role.value,
                            "address": edit_location.value.strip()
                        }
                        if update_user(user['id'], payload):
                            ui.notify(f"Updated profile for '{edit_name.value}'!", type='positive')
                            dialog.close()
                            refresh_list(search_input.value)
                        else:
                            ui.notify('Failed to update user profile.', type='negative')

                    with ui.row().classes('w-full justify-end gap-2 mt-4'):
                        ui.button('Cancel', on_click=dialog.close).props('flat text-color=grey')
                        ui.button('Save Changes', on_click=save_user_changes).classes('bg-blue-600 text-white font-bold')

                dialog.open()

            # --- DIALOG: DELETE CONFIRMATION ---
            def open_delete_dialog(user_id: str, user_name: str):
                with ui.dialog() as dialog, ui.card().classes('w-96 p-6 flex flex-col gap-4 rounded-xl shadow-xl'):
                    ui.label('Delete User Profile').classes('text-lg font-bold text-red-600')
                    ui.label(f"Are you sure you want to delete profile '{user_name}'? This action cannot be undone.").classes('text-sm text-slate-600')

                    def confirm_delete():
                        if delete_user(user_id):
                            ui.notify(f"User '{user_name}' deleted.", type='info')
                            dialog.close()
                            refresh_list(search_input.value)
                        else:
                            ui.notify('Failed to delete user.', type='negative')

                    with ui.row().classes('w-full justify-end gap-2 mt-4'):
                        ui.button('Cancel', on_click=dialog.close).props('flat text-color=grey')
                        ui.button('Delete Profile', on_click=confirm_delete).classes('bg-red-600 text-white font-bold')

                dialog.open()

            def on_search_change(e):
                refresh_list(e.value)

            def clear_search():
                search_input.set_value('')
                refresh_list('')

            search_input.on('update:model-value', on_search_change)
            refresh_list()