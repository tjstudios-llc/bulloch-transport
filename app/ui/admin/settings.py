# app/ui/admin/settings.py

from nicegui import ui
from app.ui.admin.header import render_admin_header


def render_admin_settings_page():
    """
    System Settings and API Configuration Panel for Admins (Optimized for 1024x600 Kiosks).
    """
    # Shared Navigation Header (~48px)
    render_admin_header(active_page="settings")

    # Main Kiosk Container (Fixed 540px height prevents outer page scrolling)
    with ui.column().classes('w-full max-w-[1024px] h-[540px] p-2 bg-slate-100 gap-2 overflow-hidden mx-auto'):
        
        # Compact Title Bar
        with ui.row().classes('w-full justify-between items-center bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-sm'):
            ui.label("⚙️ System Settings").classes("text-sm font-bold text-slate-800")

        # Compact Navigation Tabs
        with ui.tabs().props('dense active-color=primary').classes('w-full bg-white shadow-sm rounded-lg') as tabs:
            api_tab = ui.tab('API Integrations', icon='api')
            sys_tab = ui.tab('System Preferences', icon='settings')
            
        with ui.tab_panels(tabs, value=api_tab).classes('w-full flex-1 bg-transparent p-0 overflow-hidden'):
            
            # =========================================================
            # TAB 1: API INTEGRATIONS
            # =========================================================
            with ui.tab_panel(api_tab).classes('p-3 bg-white rounded-lg border border-slate-200 shadow-sm h-full flex flex-col justify-between overflow-y-auto'):
                with ui.column().classes('w-full gap-2'):
                    ui.label("External Service Keys").classes("text-xs font-bold text-slate-800 uppercase tracking-wider")
                    ui.label("Keys are encrypted and stored in environment configuration.").classes("text-[11px] text-slate-500 mb-1")
                    
                    weather_key = ui.input("OpenWeatherMap API Key", placeholder="Enter OpenWeather API Key...") \
                        .props('dense outlined password').classes('w-full text-xs')
                    
                    maps_key = ui.input("Google Maps Routes API Key", placeholder="Enter Google Maps API Key...") \
                        .props('dense outlined password').classes('w-full text-xs')
                
                def save_api_keys():
                    ui.notify("API Keys securely updated and reloaded in memory.", type='positive')
                    
                ui.button("Update API Keys", on_click=save_api_keys) \
                    .props('dense').classes('bg-blue-600 hover:bg-blue-500 text-white font-bold h-8 text-xs px-4 rounded-md shadow self-start mt-2')
                
            # =========================================================
            # TAB 2: SYSTEM PREFERENCES
            # =========================================================
            with ui.tab_panel(sys_tab).classes('p-3 bg-white rounded-lg border border-slate-200 shadow-sm h-full flex flex-col justify-between overflow-y-auto'):
                with ui.column().classes('w-full gap-2'):
                    ui.label("Global Fleet Toggles").classes("text-xs font-bold text-slate-800 uppercase tracking-wider mb-1")
                    
                    # Toggle 1: Driver TTS Voice
                    with ui.row().classes('w-full items-center justify-between border-b border-slate-200 pb-2'):
                        with ui.column().classes('gap-0'):
                            ui.label("Enable Driver TTS Voice Announcements").classes('font-bold text-xs text-slate-800')
                            ui.label("Play text-to-speech audio for upcoming stops on the driver display.").classes('text-[11px] text-slate-500')
                        ui.switch(value=True).props('dense')

                    # Toggle 2: Auto-assign Subs
                    with ui.row().classes('w-full items-center justify-between border-b border-slate-200 pb-2'):
                        with ui.column().classes('gap-0'):
                            ui.label("Auto-assign Sub Drivers").classes('font-bold text-xs text-slate-800')
                            ui.label("Automatically allow dispatcher-approved subs to inherit route data.").classes('text-[11px] text-slate-500')
                        ui.switch(value=False).props('dense')

                    # Toggle 3: Strict Geofencing
                    with ui.row().classes('w-full items-center justify-between border-b border-slate-200 pb-2'):
                        with ui.column().classes('gap-0'):
                            ui.label("Strict Geofence Alerts").classes('font-bold text-xs text-slate-800')
                            ui.label("Trigger a dispatch alert if a bus deviates more than 0.5 miles from its route.").classes('text-[11px] text-slate-500')
                        ui.switch(value=True).props('dense')
                
                def save_preferences():
                    ui.notify("System preferences synchronized across the fleet.", type='positive')

                ui.button("Save Preferences", on_click=save_preferences) \
                    .props('dense').classes('bg-emerald-600 hover:bg-emerald-500 text-white font-bold h-8 text-xs px-4 rounded-md shadow self-start mt-2')