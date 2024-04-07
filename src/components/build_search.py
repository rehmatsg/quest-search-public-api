import json

from openai import AsyncOpenAI

from src.models.article import Article
from .prompts import SEARCH_BUILDER_MESSAGES
from ..models.search import Search, Thread
from .keys import GROQ_API_KEY, OPENAI_API_KEY

from groq import AsyncGroq
from typing import Optional
import time
import os

async def build_search(query: str, thread: Thread, attempt: int = 1) -> Optional[Search]:
  try:
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    messages = []

    context = ""

    if len(thread.searches) >= 1:
      context = "Context from previous searches:\n"
      for search in thread.searches:
        context += search.get_context() + "\n"
        
    if context != "":
      print('Found context:')
      print(context)

    for role, content in SEARCH_BUILDER_MESSAGES:
      messages.append({
        "role": role,
        "content": content
      })

    user_message = f'{context}User Query: "{query}"'

    messages.append({
      "role": "user",
      "content": user_message
    })

    start_time = time.time()

    chat_completion = await client.chat.completions.create(
      messages=messages,
      model="gpt-3.5-turbo-0125",
      stop=["</s>", "[/INST]"],
      temperature=0.2,
      response_format={"type": "json_object"},
    )

    info = chat_completion.choices[0].message.content
    
    print(f"Search: {info}")

    first_p = info.find("{")
    last_p = info.rfind("}") + 1

    search = Search.create(query, thread.id, info[first_p:last_p])

    search.logs.raw_keywords = info
    search.logs.keyword_generation_time = time.time() - start_time

    return search

  except Exception as e:
    print(f"Exception {e}")
    if attempt < 5:
      return await build_search(query, thread, attempt + 1)
    else:
      print('Falling back to basic search')
      return Search.create(query, json.dumps({
        "keywords": [query],
        "search_type": "web",
        "search_image": True,
        "entity": None
      }))
      
async def rewrite_headline(article: Article, attempt: int = 1) -> str:
  try:
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    
    REWRITE_HEADLINE_PROMPT = """
You are a neutral news writer. You have been given the following article and asked to rewrite it in a more neutral tone that is suitable for a general audience. You should not include any opinions or biases in your rewrite. The headline should be concise and informative.

Return Format:
You will be returning a JSON object with keys "headline". The "headline" key should contain the new headline you have written.
You will ONLY be rewriting the headline of the article. You should not rewrite the body of the article.
ONLY return the JSON object with the new headline. Do not include any other information in the response.

Here's an example of the expected return format:

Headline: OpenAI unveils voice cloning tool Voice Engine: All you need to know
OpenAI has recently unveiled a new voice cloning technology called "Voice Engine," which has garnered significant attention due to its capabilities and the ethical considerations surrounding its use. This technology can generate natural-sounding speech that closely resembles a specific individual's voice from just a 15-second audio sample. Despite its potential for various beneficial applications, OpenAI has decided not to release it widely to the public at this time, citing concerns over potential misuse and the risks associated with generating speech that closely mimics real people's voices, especially in sensitive contexts such as elections

{
  "headline": "OpenAI Introduces Voice Engine, a Voice Cloning Technology"
}
"""

    messages = [
      {
        "role": "system",
        "content": REWRITE_HEADLINE_PROMPT
      },
      {
        "role": "user",
        "content": f"Headline: f{article.title}\n{article.crawled_content}"
      }
    ]

    chat_completion = await client.chat.completions.create(
      messages=messages,
      model="gpt-3.5-turbo-0125",
      temperature=0.2,
      response_format={"type": "json_object"},
    )
    
    response = chat_completion.choices[0].message.content

    first_p = response.find("{")
    last_p = response.rfind("}") + 1

    rewritten_headline = response[first_p:last_p]

    return json.loads(rewritten_headline)["headline"]
  except Exception as e:
    print(f"Exception {e}")
    if attempt < 5:
      return await rewrite_headline(article, attempt + 1)
    else:
      print('Falling back to basic search')
      return article.title