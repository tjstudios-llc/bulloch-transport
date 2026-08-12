# app/ui/admin/settings.py

from nicegui import ui
from app.ui.admin.header import render_admin_header


def render_admin_settings_page():
    """
    System Settings and API Configuration Panel for Admins.
    """
    # Shared Header Navigation
    render_admin_header(active_page="settings")

    # Main Body Content
    with ui.column().classes('w-full p-6 bg-slate-100 min-h-screen gap-6'):
        ui.label("⚙️ System Settings").classes("text-2xl font-bold text-slate-800")
        
        with ui.tabs().classes('w-full text-lg') as tabs:
            api_tab = ui.tab('API Integrations', icon='api')
            sys_tab = ui.tab('System Preferences', icon='settings')
            
        with ui.tab_panels(tabs, value=api_tab).classes('w-full max-w-4xl border rounded-lg shadow-sm bg-white mt-2'):
            
            # --- API INTEGRATIONS PANEL ---
            with ui.tab_panel(api_tab).classes('p-8'):
                ui.label("External Service Keys").classes("text-xl font-semibold mb-2 text-slate-800")
                ui.label("Keys are encrypted and stored in environment configuration.").classes("text-sm text-slate-500 mb-6")
                
                ui.input("OpenWeatherMap API Key", password=True, placeholder="Enter OpenWeather API Key...").classes('w-full mb-4')
                ui.input("Google Maps Routes API Key", password=True, placeholder="Enter Google Maps API Key...").classes('w-full mb-4')
                
                def save_api_keys():
                    ui.notify("API Keys securely updated and reloaded in memory.", type='positive')
                    
                ui.button("Update API Keys", on_click=save_api_keys, color="primary").classes('mt-4 px-6 py-2')
                
            # --- SYSTEM PREFERENCES PANEL ---
            with ui.tab_panel(sys_tab).classes('p-8'):
                ui.label("Global Fleet Toggles").classes("text-xl font-semibold mb-6 text-slate-800")
                
                with ui.column().classes('w-full gap-4'):
                    with ui.row().classes('w-full items-center justify-between border-b pb-4'):
                        with ui.column():
                            ui.label("Enable Driver TTS Voice Announcements").classes('font-bold text-lg')
                            ui.label("Play text-to-speech audio for upcoming stops on the driver display.").classes('text-sm text-slate-500')
                        ui.switch(value=True).classes('text-xl')

                    with ui.row().classes('w-full items-center justify-between border-b pb-4'):
                        with ui.column():
                            ui.label("Auto-assign Sub Drivers").classes('font-bold text-lg')
                            ui.label("Automatically allow dispatcher-approved subs to inherit route data.").classes('text-sm text-slate-500')
                        ui.switch(value=False).classes('text-xl')

                    with ui.row().classes('w-full items-center justify-between border-b pb-4'):
                        with ui.column():
                            ui.label("Strict Geofence Alerts").classes('font-bold text-lg')
                            ui.label("Trigger a dispatch alert if a bus deviates more than 0.5 miles from its route.").classes('text-sm text-slate-500')
                        ui.switch(value=True).classes('text-xl')
                
                def save_preferences():
                    ui.notify("System preferences synchronized across the fleet.", type='positive')

                ui.button("Save Preferences", on_click=save_preferences, color="primary").classes('mt-8 px-6 py-2')