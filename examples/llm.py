"""Fetch a page with Requests and print LLM-ready Markdown.

Run `python examples/llm.py`; change url below to fetch another page.
"""

import requests

from lexidown import TurndownService
from lexidown.plugins.llm import llm

url = "https://github.com/EvickaStudio/lexidown"
response = requests.get(url, timeout=30)
response.raise_for_status()

service = TurndownService(
    {
        "baseUrl": response.url,
        "includeLinkUrls": False,
        "includeImageUrls": False,
    }
).use(llm)
markdown = service.turndown(response.text)

print(markdown)
