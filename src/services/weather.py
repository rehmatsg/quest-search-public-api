from typing import Optional
import httpx

from src.models.geolocation import Geolocation
from ..components.keys import OPENWEATHER_API_KEY

async def get_weather(geolocation: Geolocation) -> Optional[dict]:
  base_url = f"https://api.openweathermap.org/data/2.5/weather?lat={geolocation.latitude}&lon={geolocation.longitude}&cnt=7&appid={OPENWEATHER_API_KEY}"

  async with httpx.AsyncClient() as client:
    response = await client.get(base_url)
    
  data = response.json()
  return data