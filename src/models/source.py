import asyncio
from typing import Optional
import httpx
from pydantic import BaseModel, HttpUrl
from bs4 import BeautifulSoup, Comment

from src.models.article import Article

class TimeoutException(Exception):
  pass

async def async_fetch_and_parse(url: str) -> Optional[str]:
  try:
    async with httpx.AsyncClient(timeout=1.5) as client:
      response = await client.get(url)
    response.raise_for_status()
    
    # Parse the HTML content
    soup = BeautifulSoup(response.text, 'html.parser')
    
    for tag in soup(['script', 'style', 'header', 'footer', 'nav', 'aside']):
      tag.decompose()

    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
      comment.extract()

    for tag in soup.find_all(['div', 'section'], {'class': ['advertisement', 'promo', 'ad-banner']}):
      tag.decompose()

    clean_text = soup.get_text(separator=' ', strip=True)
    return clean_text
  except Exception as e:
    print(f"An error occurred: {e}")
    return None

class Source(BaseModel):
  url: str
  result_type: str
  title: str
  hostname: str
  description: Optional[str] = None
  snippet: Optional[str] = None
  favicon: Optional[str] = None
  crawled_content: Optional[str] = None
  thumbnail: Optional[str] = None

  @classmethod
  def fromResult(cls, result: dict, result_type: str) -> "Source":
    snippet = None
    if result.get("extra_snippets"):
      snippet = ' '.join(result.get("extra_snippets"))
    return cls(
      url=result['url'],
      result_type=result_type,
      title=result['title'],
      hostname=result['meta_url']['hostname'],
      description=result.get('description'),
      snippet=snippet,
      favicon=result['meta_url']['favicon']
    )

  @classmethod
  def fromImageResult(cls, result: dict) -> "Source":
    return cls(
      url=result['url'],
      result_type="image",
      title=result['title'],
      hostname=result['meta_url']['hostname'],
      favicon=result['meta_url']['favicon'],
      thumbnail=result['thumbnail']['src']
    )
    
  @classmethod
  def fromArticle(cls, article: Article) -> "Source":
    return cls(
      url=article.url,
      result_type="article",
      title=article.title,
      hostname=article.hostname,
      favicon=article.favicon,
      thumbnail=article.thumbnail
    )

  async def crawl(self) -> Optional[str]:
    if self.result_type != "web" and self.result_type != "news":
      return None
    if self.crawled_content:
      return self.crawled_content
    
    try:
      self.crawled_content = await asyncio.wait_for(async_fetch_and_parse(self.url), timeout=1.5)
      return self.crawled_content
    except asyncio.TimeoutError:
      print("Operation timed out")
      return None
  
  def __str__(self) -> str:
    return f"{self.result_type} result from {self.url}"
  
async def crawl(sources: list[Source]) -> dict:
  result = {}

  async def crawl_source(source: Source):
    try:
      content = await source.crawl()  # Asynchronously get the content
      if content:
        result[source.url] = content
    except Exception as e:
        print(f"An error occurred while fetching content from {source.url}: {e}")

  # Create a list of tasks for each source
  tasks = [crawl_source(source) for source in sources]

  # Run and wait for all tasks to complete
  await asyncio.gather(*tasks)

  return result