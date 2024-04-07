import httpx
import asyncio
from typing import List
import os
import time

from ..models.search import Search, Source
from .keys import BRAVE_API_KEY

async def fetch_search_results(client: httpx.AsyncClient, query: str, search_type: str, search: Search) -> List[dict]:
  """
  Asynchronously fetch search results for a given query and search type using Brave's search API.
  
  Parameters:
  - client (httpx.AsyncClient): The HTTP client for making requests.
  - query (str): The search query.
  - search_type (str): The type of search ("web" or "news").
  - brave_api_key (str): The API key for Brave search.

  Returns:
  List[dict]: A list of search results.
  """
  url = f"https://api.search.brave.com/res/v1/{search_type}/search"
  
  headers = {
    "X-Subscription-Token": BRAVE_API_KEY,
  }
  
  if search.geolocation:
    headers["X-Loc-Lat"] = search.geolocation.latitude
    headers["X-Loc-Long"] = search.geolocation.longitude
  
  response = await client.get(url, params={
    "q": query,
    "text_decorations": False,
  }, headers=headers)

  response.raise_for_status()  # Ensure the request was successful
  return response.json()

async def web_search(search: Search):
  """
  Perform parallel API calls to Brave for each query in the list and return a combined list of sources.
  
  Parameters:
  - queries (List[str]): A list of search queries.
  - brave_api_key (str): The API key for Brave search.

  Returns:
  List[Source]: A combined list of sources from all queries.
  """
  sources = []
  search_type = "web"

  start_time = time.time()

  async with httpx.AsyncClient() as client:
    tasks = [fetch_search_results(client, keyword, search_type if "news" not in keyword.split(' ') else "news", search) for keyword in search.keywords]
    results = await asyncio.gather(*tasks, return_exceptions=True)

  try:
    for result in results:
      if result['type'] == "search":
        for index in result['mixed']['main']:
          if index['all']:
            for r in result[index['type']]['results']:
              source = Source.fromResult(r, index['type'])
              sources.append(source)
          else:
            source = Source.fromResult(result[index['type']]['results'][index['index']], index['type'])
            sources.append(source)
      else:
        for news in result.get('results', []):
          sources.append(Source.fromResult(news, 'news'))
  except Exception as e:
    print(f"Error during Web Search: {e}")
    
  if not search.location_used and result.get('query') and result['query'].get('is_geolocal', False):
    search.location_used = result['query'].get('city') or search.geolocation.city

  search.sources = sources
  search.logs.web_search_time = time.time() - start_time

async def image_search(search: Search):
  url = "https://api.search.brave.com/res/v1/images/search"

  start_time = time.time()
  
  headers = {
    "X-Subscription-Token": BRAVE_API_KEY,
  }
  
  if search.geolocation:
    headers["X-Loc-Lat"] = search.geolocation.latitude
    headers["X-Loc-Long"] = search.geolocation.longitude

  async with httpx.AsyncClient() as client:
    response = await client.get(url, params={
      "q": search.keywords[0]
    }, headers=headers)

  result = response.json()

  images = []

  for r in result['results']:
    images.append(Source.fromImageResult(r))

  search.images = images
  search.logs.image_search_time = time.time() - start_time