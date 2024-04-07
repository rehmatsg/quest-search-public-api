import asyncio
from datetime import datetime, timezone
import time
from pydantic import BaseModel
from urllib.parse import urljoin, urlparse
from typing import Optional, List
from newspaper import Article as NewspaperArticle
from newspaper import Config as NewspaperConfig

from src.components.helpers import extract_gnews_article_id, generate_id, parse_date_to_milliseconds
from ..services.database import mongo_client

class Article(BaseModel):
  id: str
  topic: Optional[str] = None
  url: str
  og_url: str
  title: str
  description: str
  thumbnail: str
  authors: Optional[list[str]] = None
  hostname: str
  site_name: str
  favicon: Optional[str] = None
  crawled_content: str
  publish_date: Optional[int] = None
  tags: Optional[List[str]] = []
  thread_id: Optional[str] = None
  crawl_time: Optional[int] = round(time.time() * 1000)

  @staticmethod
  def generate(gnews: dict, topic: Optional[str] = None) -> Optional["Article"]:
    try:
      config = NewspaperConfig()
      config.browser_user_agent = "Googlebot-News"
      
      site_name = gnews.get('publisher', {}).get('title')

      news_article = NewspaperArticle(gnews['url'], config=config)
      news_article.download()
      news_article.parse()

      base_url = news_article.meta_data.get('og', {}).get('url')
      parsed_url = urlparse(base_url)

      thumbnail = news_article.meta_img or news_article.top_image
      hostname = parsed_url.hostname.replace('www.', '')

      if not base_url or not news_article.title or not thumbnail or not hostname or not site_name or not news_article.text:
        return None

      publish_date = None

      if news_article.publish_date:
        if type(news_article.publish_date) is str:
          publish_date = parse_date_to_milliseconds(news_article.publish_date)
        elif type(news_article.publish_date) is datetime:
          dt_utc = news_article.publish_date.astimezone(timezone.utc)
          publish_date = int(dt_utc.timestamp() * 1000)
          
      favicon = news_article.meta_favicon
      if favicon and not favicon.startswith(('http://', 'https://')):
        favicon = urljoin(f"{parsed_url.scheme}://{parsed_url.netloc}", favicon)

      return Article(
        id=generate_id(10),
        topic=topic,
        url=base_url,
        og_url=gnews['url'],
        title=news_article.title,
        description=news_article.meta_description,
        thumbnail=thumbnail,
        authors=news_article.authors,
        hostname=hostname,
        site_name=site_name,
        favicon=favicon,
        crawled_content=news_article.text,
        publish_date=publish_date,
        tags=news_article.tags
      )
    except Exception as e:
      print(e)
      return None
    
  @staticmethod
  async def get(article_id: str) -> Optional["Article"]:
    try:
      data = await mongo_client.quest.articles.find_one({"id": article_id})
      return Article(**data)
    except Exception as e:
      print(f"An error occurred: {e}")
      return None
    
  async def save(self):
    try:
      await mongo_client.quest.articles.insert_one({
        '_id': self.id,
        **dict(self)
      })
      print(f"Saved article {self.id}")
    except Exception as e:
      print(f"Error saving article: {e}")
      
  async def link_to_thread(self, thread):
    try:
      await mongo_client.quest.articles.update_one({"id": self.id}, {"$set": {
        "thread_id": thread.id,
        "title": thread.searches[-1].query,
        "summary": thread.searches[-1].summary,
      }})
    except Exception as e:
      print(f"Error linking article to thread: {e}")
    
  @staticmethod
  async def gnews_exists(url: str) -> bool:
    try:
      exists = (await mongo_client.quest.articles.find_one({"og_url": url})) is not None
      return exists
    except Exception as e:
      print(f"An error occurred: {e}")
      return False
    
  @staticmethod
  async def filter_gnews_articles(articles: list) -> list:
    '''
    Filters out articles that already exist in the database
    '''
    tasks = [Article.gnews_exists(article['url']) for article in articles]
    results = await asyncio.gather(*tasks)
    
    return [article for article, exists in zip(articles, results) if not exists]