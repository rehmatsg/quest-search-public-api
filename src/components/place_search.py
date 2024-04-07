import httpx
import os
import time

from src.models.place import Place

from ..models.search import Search
from .keys import YELP_API_KEY

async def place_search(search: Search):
  yelp_api = "https://api.yelp.com/v3/businesses/search?sort_by=best_match&limit=20"

  headers = {
    "accept": "application/json",
    "Authorization": f"BEARER {YELP_API_KEY}"
  }

  parameters = {
    "term": search.query,
    "longitude": search.geolocation.longitude,
    "latitude": search.geolocation.latitude,
    "location": search.geolocation.city
  }

  start_time = time.time()

  async with httpx.AsyncClient() as client:
    response = await client.get(yelp_api, headers=headers, params=parameters)
    
  places_data = response.json()['businesses']
  
  places = [Place(**place) for place in places_data]

  search.places = places
  search.location_used = search.geolocation.city
  search.logs.place_search_time = time.time() - start_time