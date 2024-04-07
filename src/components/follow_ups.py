import ast
from ..models.search import Search
from groq import AsyncGroq
from typing import Optional
from .prompts import FOLLOW_UP_PROMPT
from .keys import GROQ_API_KEY

def parse_list_from_string(list_string: str):
  try:
    # Use ast.literal_eval to safely evaluate the string
    result = ast.literal_eval(list_string)
    # Check if the result is indeed a list
    if isinstance(result, list):
      return result
    else:
      raise ValueError("The string does not represent a list.")
  except (ValueError, SyntaxError) as e:
    print(f"Error parsing the list: {e}")
    return None

async def generate_follow_ups(search: Search):
  context = search.get_context()

  messages = [
    {
      "role": "system",
      "content": FOLLOW_UP_PROMPT
    },
    {
      "role": "user",
      "content": context
    },
  ]

  groq_client = AsyncGroq(
    api_key=GROQ_API_KEY
  )

  chat_completion = await groq_client.chat.completions.create(
    messages=messages,
    model="mixtral-8x7b-32768",
    top_p=1,
    temperature=0.1
  )

  try:
    search.follow_ups = parse_list_from_string(chat_completion.choices[0].message.content)
  except:
    pass