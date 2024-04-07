from enum import Enum
import time
from typing import Optional, List
from pydantic import BaseModel
import json

from src.models.place import Place

from .source import Source
from .geolocation import Geolocation
from ..components.helpers import generate_id
from ..services.database import mongo_client

class SearchType(Enum):
  WEB = "web"
  PLACE = "place"

class SearchMode(Enum):
  BASIC = "basic"
  PRO = "pro"

class SearchLog(BaseModel):
  keyword_generation_time: Optional[float] = 0
  web_search_time: Optional[float] = 0
  image_search_time: Optional[float] = 0
  knowledge_panel_time: Optional[float] = 0
  place_search_time: Optional[float] = 0

  raw_keywords: Optional[str] = None
  
class Search(BaseModel):
  thread_id: str
  query: str
  keywords: list[str]
  search_type: Optional[SearchType] = SearchType.WEB
  search_image: Optional[bool] = True
  entity: Optional[str] = None
  sources: Optional[List[Source]] = []
  featured_source: Optional[Source] = None
  images: Optional[List[Source]] = []
  places: Optional[List[Place]] = []
  knowledge_panel: Optional[dict] = None
  summary: Optional[str] = None
  logs: SearchLog
  follow_ups: list[str] = []
  search_mode: Optional[SearchMode] = SearchMode.BASIC
  geolocation: Optional[Geolocation] = None
  location_used: Optional[str] = None
  warnings: Optional[List[str]] = []

  @classmethod
  def create(cls, query: str, thread_id: str, data: str) -> "Search":
    json_obj = json.loads(data)
    return cls(
      thread_id=thread_id,
      query=query,
      keywords=json_obj['keywords'],
      search_type=SearchType.WEB if json_obj.get('search_type', "web") == "web" else SearchType.PLACE,
      search_image=json_obj.get('search_image', True),
      entity=json_obj.get('entity'),
      logs=SearchLog()
    )

  def get_context(self) -> str:
    context = f"{self.query}\n"
    if self.search_type == SearchType.WEB:
      if self.summary and self.summary != "":
        context += self.summary
      else:
        for source in self.sources[:10]:
          context += f"{source.title}\n{source.snippet}\n"
    elif self.search_type == SearchType.PLACE:
      for place in self.places[:5]:
        context += place.generate_context() + "---\n"
    return context
  
  def clientJSON(self) -> str:
    return json.dumps({
      'thread_id': self.thread_id,
      'featured_source': dict(self.featured_source) if self.featured_source else None,
      'sources': [source.dict() for source in self.sources],
      'images': [image.dict() for image in self.images],
      'places': [place.dict() for place in self.places],
      'knowledge_panel': self.knowledge_panel,
      'query': self.query,
      'search_type': self.search_type.value,
      'location': self.location_used,
      'warnings': self.warnings,
      'summary': self.summary,
      'follow_ups': self.follow_ups,
    })
    
  def dict(self):
    return {
      'thread_id': self.thread_id,
      'query': self.query,
      'keywords': self.keywords,
      'search_type': self.search_type.value,
      'search_image': self.search_image,
      'entity': self.entity,
      'featured_source': dict(self.featured_source) if self.featured_source else None,
      'sources': [dict(source) for source in self.sources],
      'images': [dict(image) for image in self.images],
      'places': [dict(place) for place in self.places],
      'knowledge_panel': self.knowledge_panel,
      'summary': self.summary,
      'logs': dict(self.logs),
      'follow_ups': self.follow_ups,
      'search_mode': self.search_mode.value,
      'geolocation': dict(self.geolocation) if self.geolocation else None,
      'location_used': self.location_used,
      'warnings': self.warnings,
    }

class Thread(BaseModel):
  id: str
  user_id: Optional[str] = None
  created_at: float # Seconds since epoch
  searches: List[Search] = []
  is_new: Optional[bool] = True
  
  @classmethod
  def create(cls) -> "Thread":
    id = generate_id(6)
    return cls(
      id=id,
      user_id=None,
      created_at=time.time(),
      searches=[]
    )

  def add(self, search: Search):
    self.searches.append(search)
    
  def dict(self):
    return {
      '_id': self.id,
      'id': self.id,
      'user_id': self.user_id,
      'created_at': self.created_at,
      'searches': [search.dict() for search in self.searches]
    }
    
  async def save(self):
    if self.is_new:
      try:
        await mongo_client.quest.threads.insert_one(self.dict())
      except Exception as e:
        print(f"Error saving thread: {e}")
    else:
      try:
        await mongo_client.quest.threads.update_one({"id": self.id}, {"$set": self.dict()})
      except Exception as e:
        print(f"Error updating thread: {e}")
    
  @staticmethod
  async def get(thread_id: str, user_id: Optional[str] = None):
    try:
      data = await mongo_client.quest.threads.find_one({"id": thread_id})
      thread = Thread(**data)
      thread.is_new = False
      
      if user_id != thread.user_id:
        thread.user_id = user_id
        thread.id = generate_id(6)
        thread.is_new = True
      
      return thread
    except Exception as e:
      print(f"Error getting thread: {e}")
      return Thread.create()
    
  @staticmethod
  async def fork(thread_id: str):
    thread = await Thread.get(thread_id)
    thread.id = generate_id(6)
    thread.is_new = True
    return thread