from typing import Optional, Dict, Any
import httpx
import time

from .helpers import clean_graph, fix_graph_links

async def search_entity(entity: str, language: str = "en") -> Optional[Dict[str, Any]]:
  """
  Asynchronously search for a Wikidata entity by query and return its first matching result.

  Parameters:
  entity (str): The search query to find the entity on Wikidata.
  language (str, optional): The language in which to perform the search. Defaults to "en".

  Returns:
  Optional[Dict[str, Any]]: The first matching entity as a dictionary, or None if no match is found.
  """
  wikidata_search_url = "https://www.wikidata.org/w/api.php"
  params = {
    "action": "wbsearchentities",
    "language": language,
    "format": "json",
    "search": entity
  }
  try:
    async with httpx.AsyncClient() as client:
      response = await client.get(wikidata_search_url, params=params)
    response.raise_for_status()  # Raises HTTPError for bad responses

    # Parse the JSON response
    data = response.json()

    # Check if search results exist, if yes then return the first result
    if data['search']:
      return data['search'][0]
    else:
      return None
  except httpx.HTTPStatusError as http_err:
    print(f"HTTP error occurred: {http_err}")
    return None
  except httpx.RequestError as err:
    print(f"Request exception: {err}")
    return None

async def get_knowledge_graph(q_number: str, language: str = "en") -> Optional[Dict]:
  try:
    # Configure the SPARQL query
    endpoint = "https://query.wikidata.org/sparql"
    query = f"""
    SELECT ?property ?propertyLabel ?value ?valueLabel
    WHERE {{
      wd:{q_number} ?property ?value .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "{language}". }}
    }}
    """
    params = {
        "query": query,
        "format": "json"
    }

    # Asynchronously fetch data from the SPARQL endpoint
    async with httpx.AsyncClient() as client:
      response = await client.get(endpoint, params=params)
    response.raise_for_status()  # Raises exception for bad responses

    results = response.json()

    if len(results['results']['bindings']) <= 0:
      return None

    property_labels = {
      'P18': 'image',
      'P2002': 'twitter',
      'P2013': 'facebook',
      'P2003': 'instagram',
      'P6634': 'linkedin',
      'P856': 'website',
    }

    attribute_labels = {
      'P106': 'Occupation',              # Person
      'P101': 'Field of Work',           # Person
      'P800': 'Notable Work',            # Person / Organisation
      'P27': 'Country of Citizenship',   # Person
      'P27': 'Nationality',              # Person
      'P569': 'Date of Birth',           # Person
      'P22': 'Father',                   # Person
      'P25': 'Mother',                   # Person
      'P3373': 'Siblings',               # Person
      'P26': 'Spouse',                   # Person
      'P40': 'Children',                 # Person
      'P2218': 'Net Worth',              # Person
      'P108': 'Employer',                # Person
      'P39': 'Position Held',            # Person
      'P2048': 'Height',                 # Person
      'P102': 'Political Affiliation',   # Person
      'P69': 'Educated at',              # Person

      'Located In': 'City',              # Place
      'P1376': 'Capital Of',             # Place
      'P2046': 'Area',                   # Place
      'P1082': 'Population',             # Place
      'P36': 'Capital',                  # Place
      'P6': 'Head of Government',        # Place
      'P571': 'Inception',               # Place
      'P1082': 'Population',             # Place

      'P101': 'Field of Work',           # Organisation (Company)
      'P169': 'CEO',                     # Organisation (Company)
      'P452': 'Industry',                # Organisation (Company)
      'P159': 'Headquarters',            # Organisation (Company)
      'P112': 'Founded by',              # Organisation (Company) / Place
      'P3320': 'Board Members',          # Organisation (Company)
      'P17': 'Country',                  # Organisation (Company) / Place
      'P1128': 'Employees',              # Organisation (Company)

      'P166': 'Award Received',          # Person / Organisation / Place
      'P1830': 'Owner of',               # Person / Organisation
    }

    # Initialize a dictionary to store the extracted information
    graph = {label: [] for label in property_labels.values()}
    attributes = {attribute: [] for attribute in attribute_labels.values()}

    # Process the SPARQL result
    for binding in results['results']['bindings']:
      prop = binding['property']['value'].split('/')[-1]  # Extract property ID from URI
      value_label = binding.get('valueLabel', {}).get('value', None)
      if value_label.startswith("statement/"):
        value_label = None
      if (prop in property_labels or prop in attribute_labels) and value_label:
        readable_label = property_labels.get(prop) or attribute_labels.get(prop)
        if prop in property_labels:
          graph[readable_label].append(value_label)
        elif prop in attribute_labels:
          attributes[readable_label].append(value_label)

    graph = clean_graph(graph)
    graph = fix_graph_links(graph)
    graph['attributes'] = clean_graph(attributes)

    return graph
  except Exception as e:
    print(f"Problem encountered: {e}")
    return None

async def generate_knowledge_panel(query: str, language: str = "en"):
  """
  Generates a Knowledge Panel/Graph for the given entity (query)

  Parameters:
  query (str): The search query to find the entity on Wikidata.

  Returns:
  dict: A dictionary of knowledge graph with image, label, description and attributes
  """
  entity = await search_entity(query, language)

  if not entity:
    return None

  q_number = entity['id']
  label = entity['display']['label']['value']
  description = entity['display']['description']['value']

  graph = await get_knowledge_graph(q_number, language)

  if not graph:
    return None

  graph['label'] = label
  graph['description'] = description

  return graph

if __name__ == "__main__":
  import asyncio
  query = "OpenAI"
  graph = asyncio.run(generate_knowledge_panel(query))
  for key, value in graph.items():
    print(f"{key}: {str(value)}")