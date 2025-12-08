import aiohttp, asyncio, logging

logger = logging.getLogger(__name__)

async def get_weather(lat: float, lon: float, api_key: str) -> str:
    url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units=metric&lang=ru&appid={api_key}"
    timeout = aiohttp.ClientTimeout(total=5)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            res = await sess.get(url)
            if res.status != 200:
                return "🌡 Погода недоступна"
            data = await res.json()
    except asyncio.TimeoutError:
        return "⏱️ Сервис погоды не ответил вовремя"
    except Exception as e:
        logger.warning(f"Ошибка погоды: {e!r}")
        return "❌ Не удалось получить погоду"

    if m := data.get("main"):
        t = m["temp"]
        desc = data["weather"][0]["description"].capitalize()
        wind = data.get("wind", {}).get("speed", "?")
        return f"🌡 {t:.1f}°C, {desc}\n💨 {wind} м/с"
    return "🌡 Данных о погоде нет"
