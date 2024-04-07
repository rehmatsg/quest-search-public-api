from typing import Optional
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi_utils.tasks import repeat_every

from src.models.search import Thread
from src.search import quest_search, summarise_article
from src.services.news_crawler import begin_crawling_news
from src.services.gnews.utils.constants import TOPICS as NEWS_TOPICS
from src.routers.news import router as news_router

app = FastAPI()

app.include_router(news_router, prefix="/news")

@app.get("/")
async def index():
  return "Welcome to Quest!"
    
@app.get("/search")
async def search_endpoint(
  request: Request,
  q: Optional[str] = None,
  thread_id: Optional[str] = None,
  article_id: Optional[str] = None
):
  assert q or article_id, "Please provide a query or article ID."
  
  if q:
    thread = None
    if thread_id:
      thread = await Thread.get(thread_id)
    else:
      thread = Thread.create()
      
    # client_ip = request.client.host
    # 
    # x_forwarded_for = request.headers.get("x-forwarded-for")
    # if x_forwarded_for:
    #   client_ip = x_forwarded_for.split(",")[0]
    
    client_ip = "130.212.93.147"
    
    return StreamingResponse(quest_search(q, thread, client_ip), media_type="application/json")
  
  elif article_id:
    return StreamingResponse(summarise_article(article_id=article_id), media_type="application/json")

# @app.on_event("startup")
@repeat_every(seconds=60 * 30)
async def crawl_top_news():
  print("Crawling news...")
  await begin_crawling_news()
  print("Done.")

# @app.on_event("startup")
@repeat_every(seconds=60 * 30)
async def crawl_topic_news():
  print("Running scheduled news crawl for topics...")
  await begin_crawling_news(topics=NEWS_TOPICS)