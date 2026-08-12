# app/ui/driver/weather_widget.py

from nicegui import ui
from app.services.weather import fetch_current_weather


def render_driver_weather_widget(lat: float = 32.4488, lon: float = -81.7832):
    """
    Renders a compact, high-contrast live weather widget for driver navigation HUDs.
    """
    with ui.card().classes(
        "bg-slate-800 text-white p-4 rounded-2xl shadow-md border border-slate-700 flex flex-col justify-between"
    ):
        with ui.row().classes("w-full justify-between items-center mb-1"):
            location_label = ui.label("Statesboro, GA").classes("text-sm font-semibold text-slate-300")
            status_chip = ui.label("LIVE").classes("text-[10px] bg-green-900/80 text-green-300 font-bold px-2 py-0.5 rounded-full")

        with ui.row().classes("items-center gap-2"):
            # Weather Icon Image
            icon_img = ui.image("https://openweathermap.org/img/wn/01d@2x.png").classes("w-14 h-14")
            
            with ui.column().classes("gap-0"):
                temp_label = ui.label("--°F").classes("text-4xl font-extrabold tracking-tight text-white")
                condition_label = ui.label("Loading...").classes("text-xs font-medium text-amber-400")

        ui.separator().classes("bg-slate-700 my-2")

        with ui.row().classes("w-full justify-between text-xs text-slate-400 font-medium"):
            feels_label = ui.label("Feels Like: --°F")
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