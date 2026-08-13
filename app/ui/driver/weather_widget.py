# app/ui/driver/weather_widget.py

from nicegui import ui
from app.services.weather import fetch_current_weather


def render_driver_weather_widget(lat: float = 32.4488, lon: float = -81.7832):
    """
    Renders a compact, high-contrast live weather widget optimized for 1024x600 driver HUDs.
    """
    with ui.card().classes(
        "w-full bg-slate-800 text-white p-3 rounded-xl shadow-lg border border-slate-700 flex flex-col justify-between shrink-0 overflow-hidden"
    ):
        # Header: Location & Live Tag
        with ui.row().classes("w-full justify-between items-center mb-0.5"):
            location_label = ui.label("Statesboro, GA").classes("text-xs font-bold text-slate-300 truncate")
            ui.label("LIVE").classes("text-[9px] bg-emerald-900/80 text-emerald-300 font-bold px-1.5 py-0.5 rounded-md shrink-0")

        # Main Section: Icon + Temperature
        with ui.row().classes("items-center justify-start gap-2 my-0.5"):
            # Weather Icon Image
            icon_img = ui.image("https://openweathermap.org/img/wn/01d@2x.png").classes("w-10 h-10 shrink-0")
            
            with ui.column().classes("gap-0 leading-tight flex-1 min-w-0"):
                temp_label = ui.label("--°F").classes("text-2xl font-black tracking-tight text-white leading-none")
                condition_label = ui.label("Loading...").classes("text-[11px] font-semibold text-amber-400 truncate")

        ui.separator().classes("bg-slate-700/80 my-1")

        # Footer Metrics: Feels Like & Wind Speed
        with ui.row().classes("w-full justify-between text-[11px] text-slate-400 font-medium tracking-tight"):
            feels_label = ui.label("Feels: --°F")
            wind_label = ui.label("Wind: -- mph")

    async def update_weather_ui():
        weather = await fetch_current_weather(lat, lon)
        if weather:
            location_label.set_text(f"{weather['city']}, GA")
            temp_label.set_text(f"{weather['temp']}°F")
            condition_label.set_text(f"{weather['description']}")
            feels_label.set_text(f"Feels: {weather['feels_like']}°F")
            wind_label.set_text(f"Wind: {weather['wind_speed']} mph")
            icon_img.set_source(weather["icon_url"])

    # Initial async load
    ui.timer(0.1, update_weather_ui, once=True)

    # Refresh weather automatically every 10 minutes (600s)
    ui.timer(600.0, update_weather_ui)