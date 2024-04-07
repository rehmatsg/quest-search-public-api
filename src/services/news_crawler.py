import asyncio
import traceback
from typing import Optional
from .gnews.gnews import GNews

from src.models.article import Article

# Define the synchronous function to generate and parse an article
def generate_article(news, topic: str):
  try:
    return Article.generate(news, topic=topic)
  except:
    return None

# Define the asynchronous wrapper function
async def generate_article_async(news, topic: str):
  # Run the synchronous function in a separate thread
  article_info = await asyncio.to_thread(generate_article, news, topic=topic)
  return article_info

# Main function to generate multiple articles
async def generate_articles(news, topic: Optional[str] = "LATEST"):
  # Schedule generateing all articles concurrently
  tasks = [generate_article_async(news_source, topic=topic) for news_source in news]
  articles = await asyncio.gather(*tasks)
  return articles

# Example usage
async def get_latest_news():
  google_news = GNews()
  news = await asyncio.to_thread(google_news.get_top_news)
  news = await Article.filter_gnews_articles(news)
  return await generate_articles(news)

async def get_news_by_topic(topic: str):
  google_news = GNews()
  news = await asyncio.to_thread(google_news.get_news_by_topic, topic)
  news = await Article.filter_gnews_articles(news)
  return await generate_articles(news, topic=topic)

async def save_all(articles: list[Article]):
  '''
  Parallelize saving all articles
  '''
  tasks = [article.save() for article in articles if article]
  await asyncio.gather(*tasks)
  
async def begin_crawling_news(topics: list[str] = None):
  try:
    articles = []
    if topics:
      for topic in topics:
        articles += await get_news_by_topic(topic)
    else:
      articles = await get_latest_news()
    print(f'Got {len(articles)} articles. Saving...')
    await save_all(articles)
    print('Saved all articles.')
  except Exception:
    print(traceback.format_exc())