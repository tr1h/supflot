"""Сервис для работы с погодой"""
import logging
import requests
from typing import Optional, Dict, Any
from config import Config

logger = logging.getLogger(__name__)


class WeatherService:
    """Сервис для получения данных о погоде"""
    
    API_URL = "https://api.openweathermap.org/data/2.5/weather"
    
    @staticmethod
    async def get_weather(latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        """Получение погоды по координатам"""
        if not Config.OPENWEATHER_KEY:
            logger.warning("OpenWeatherMap API key not configured")
            return None
        
        try:
            params = {
                "lat": latitude,
                "lon": longitude,
                "appid": Config.OPENWEATHER_KEY,
                "units": "metric",
                "lang": "ru"
            }
            response = requests.get(WeatherService.API_URL, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            return {
                "temp": data.get("main", {}).get("temp"),
                "feels_like": data.get("main", {}).get("feels_like"),
                "description": data.get("weather", [{}])[0].get("description", ""),
                "wind_speed": data.get("wind", {}).get("speed"),
                "humidity": data.get("main", {}).get("humidity"),
            }
        except Exception as e:
            logger.error(f"Error fetching weather: {e}")
            return None



