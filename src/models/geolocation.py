from fastapi import WebSocket
from pydantic import BaseModel
import httpx
from typing import Optional

from ..components.keys import IPGEO_API_KEY

def get_client_ip_websocket(websocket: WebSocket, trust_x_forwarded_for: bool = False) -> Optional[str]:
  """
  Extracts the client's IP address from a WebSocket connection.
  
  Args:
  - websocket: The WebSocket connection object.
  - trust_x_forwarded_for: Whether to trust the 'X-Forwarded-For' header to extract the real IP address.
  
  Returns:
  - The IP address of the client.
  """
  # Attempt to get the 'X-Forwarded-For' header if it's trusted
  if trust_x_forwarded_for:
    for header in websocket.scope['headers']:
      if header[0].decode('utf-8').lower() == 'x-forwarded-for':
        # Return the first IP in the list (the original client IP)
        return header[1].decode('utf-8').split(',')[0].strip()

  # Fallback to the client host IP if 'X-Forwarded-For' isn't trusted or available
  return websocket.client.host
class Geolocation(BaseModel):
  country: Optional[str] = None
  city: Optional[str] = None
  latitude: Optional[str] = None
  longitude: Optional[str] = None
  zipcode: Optional[str] = None
  
  @staticmethod
  async def get(ip) -> Optional['Geolocation']:
    url = 'https://api.ipgeolocation.io/ipgeo'
    headers = {'Content-Type': 'application/json'}
    params = {
      "ip": ip,
      "apiKey": IPGEO_API_KEY
    }

    async with httpx.AsyncClient() as client:
      response = await client.get(url, params=params, headers=headers)
      
      json = response.json()

      if response.status_code == 200:
        return Geolocation(
          country=json.get('country_name'),
          city=json.get('city'),
          latitude=json.get('latitude'),
          longitude=json.get('longitude'),
          zipcode=json.get('zipcode')
        )
      else:
        print(f"Failed to get geolocation for IP {ip}: {json}")
        return None