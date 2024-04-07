from .components.build_search import build_search, rewrite_headline
from .components.place_search import place_search
from .components.web_search import web_search, image_search
from .components.knowledge import generate_knowledge_panel
from .components.summarise import summarise
from .components.follow_ups import generate_follow_ups
from .components.prompts import REVIEW_SUMMARY_PROMPT
from .models.search import Search, SearchLog, Thread, SearchType
from .models.geolocation import Geolocation
from .models.article import Article
from .models.source import Source

import asyncio
import json

async def quest_search(query: str, thread: Thread, ip: str):
  tasks = [
    build_search(query, thread),
    Geolocation.get(ip)
  ]
  
  search, geolocation = await asyncio.gather(*tasks, return_exceptions=True)
  
  search.geolocation = geolocation
  if search.search_type == SearchType.PLACE and (not geolocation or (geolocation and (geolocation.city is None or (geolocation.latitude is None and geolocation.longitude is None)))):
    # print('Unable to determine location. Falling back to web search.')
    search.search_type = SearchType.WEB
    search.warnings.append("Please enable location services to get more accurate results.")

  tasks = []

  if search.search_type is SearchType.WEB:
    tasks.append(web_search(search))
  elif search.search_type is SearchType.PLACE:
    tasks.append(place_search(search))

  if search.search_image and search.search_type is SearchType.WEB:
    tasks.append(image_search(search))
    
  if search.entity:
    tasks.append(generate_knowledge_panel(search.entity, "en"))

  results = await asyncio.gather(*tasks, return_exceptions=True)
  
  knowledge_panel = results.pop() if search.entity else None
  if knowledge_panel:
    if len(thread.searches) == 0:
      search.knowledge_panel = knowledge_panel
    elif len(thread.searches) > 0:
      if thread.searches[-1].knowledge_panel and thread.searches[-1].knowledge_panel['label'] != knowledge_panel['label']:
        search.knowledge_panel = knowledge_panel
      else:
        search.knowledge_panel = knowledge_panel
      
  yield search.clientJSON() + "\n"
  
  if search.search_type is SearchType.PLACE and len(search.places) == 0:
    search.search_type = SearchType.WEB
    await web_search(search)
    
  
  background_task = asyncio.create_task(generate_follow_ups(search))

  if search.search_type is SearchType.WEB:
    async for word in summarise(search):
      yield json.dumps({
        "delta": {
          "summary": word
        }
      }) + "\n"
  
  await background_task
  
  yield json.dumps({
    "follow_ups": search.follow_ups
  }) + "\n"
  
  thread.add(search)
  asyncio.create_task(thread.save())
  
async def summarise_article(article_id: str):
  article = await Article.get(article_id)
  
  if not article:
    return
  elif article.thread_id:
    thread = await Thread.get(article.thread_id)
    yield thread.searches[-1].clientJSON()
    return
  else:
    headline = await rewrite_headline(article)
    article.title = headline
    
    user_thread = Thread.create()
    article_thread = Thread.create()
    article_thread.user_id = "quest-bot"
    
    user_search = Search(
      thread_id=user_thread.id,
      query=headline,
      keywords=article.tags or [],
      featured_source=Source.fromArticle(article),
      logs=SearchLog()
    )
    article_search = Search(
      thread_id=article_thread.id,
      query=headline,
      keywords=article.tags or [],
      featured_source=Source.fromArticle(article),
      logs=SearchLog()
    )
        
    yield user_search.clientJSON() + "\n"
    
    background_task = asyncio.create_task(generate_follow_ups(user_search))

    async for word in summarise(
      user_search,
      user_prompt=f"Summarise the article '{article.title}' from the given context:\n{article.crawled_content}"
    ):
      yield json.dumps({
        "delta": {
          "summary": word
        }
      }) + "\n"
    
    await background_task
    
    yield json.dumps({
      "follow_ups": user_search.follow_ups
    }) + "\n"
    
    article_search.summary = user_search.summary
    article_search.follow_ups = user_search.follow_ups
    
    user_thread.add(user_search)
    article_thread.add(article_search)
    asyncio.create_task(user_thread.save())
    asyncio.create_task(article_thread.save())
    asyncio.create_task(article.link_to_thread(article_thread))