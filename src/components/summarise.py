from ..models.search import Source, Search
from .prompts import SUMMARY_PROMPT
from .keys import OPENAI_API_KEY

import os
from openai import AsyncOpenAI

def generate_citations(sources: list[Source]):
  content = ""
  for i, source in enumerate(sources):
    c = source.crawled_content or source.snippet
    if c is None:
      continue
    if i > 0:
      content += "\n\n----\n\n"
    content += f"[citation:{i}] {c}"
  return content

stop_words = [
  # "<|im_end|>",
  "<end>"
  "[End]",
  "[end]",
  # "\nReferences\n",
  # "\nReferences:\n",
  # "\n*References*\n",
  # "\n**References**\n",
  # "\nSources\n",
  # "\nSources:\n",
  # "\n*Sources*\n",
  # "\n**Sources**\n",
  "End.",
  # "\n\n[citation:",
]

async def summarise(search: Search, system_prompt: str = SUMMARY_PROMPT, user_prompt: str = None):
  content = generate_citations(search.sources)
  
  if not user_prompt:
    user_prompt = f"Anwer the question '{search.query}' from the given context:\n{content}"
  
  messages = [
    {
      "role": "system",
      "content": system_prompt
    },
    {
      "role": "user",
      "content": user_prompt
    },
  ]

  client = AsyncOpenAI(api_key=OPENAI_API_KEY)

  chat_completion = await client.chat.completions.create(
    model="gpt-3.5-turbo-0125",
    messages=messages,
    stream=True,
    stop=stop_words,
    temperature=0.5
  )

  summary = ""

  async for chunk in chat_completion:
    text = chunk.choices[0].delta.content
    # print(text, end="")
    if text:
      summary += text
      yield text

  search.summary = summary