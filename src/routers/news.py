import asyncio
import time
from fastapi import APIRouter, Request
import pymongo

from src.models.geolocation import Geolocation
from src.services.weather import get_weather

from ..services.database import mongo_client
from ..models.article import Article
from ..services.gnews.utils.constants import TOPICS

router = APIRouter()

async def get_articles(topic: str):
  '''
  Gets latest news articles by topic
  '''
  docs = await mongo_client.quest.articles.find({"topic": topic}).sort("publish_date", pymongo.DESCENDING).to_list(10)
  
  articles = []
  
  for doc in docs:
    doc.pop("_id")
    articles.append(Article(**doc))
    
  return articles

async def build_weather_data(request: Request):
  client_ip = request.client.host
  
  x_forwarded_for = request.headers.get("x-forwarded-for")
  if x_forwarded_for:
    client_ip = x_forwarded_for.split(",")[0]
    
  geolocation = await Geolocation.get(client_ip)
  weather = await get_weather(geolocation=geolocation)
  
  return weather

@router.get("/feed")
async def get_news(request: Request):
  response = {
    "news": {}
  }
  
  weather_task = asyncio.create_task(build_weather_data(request))
  
  tasks = []
  for topic in TOPICS + ["LATEST"]:
    response[topic] = None
    tasks.append(get_articles(topic))
    
  results = await asyncio.gather(*tasks)
  
  for topic, articles in zip((TOPICS + ["LATEST"]), results):
    response["news"][topic] = articles
    
  response["weather"] = await weather_task
    
  return response

@router.get("/topics")
async def get_topics():
  return TOPICS + ["LATEST"]

@router.get("/{topic}")
async def get_news_by_topic(topic: str):
  topic = topic.upper()
  return await get_articles(topic)