import requests
import os
import json
from dotenv import load_dotenv
load_dotenv()
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

def search_web(query: str) -> str:
    """
    Performs a real-time web search using Serper API and returns a summary.
    """
    if not SERPER_API_KEY:
        return "Web search is not configured. Please add SERPER_API_KEY to your .env file."

    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": query})
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        response.raise_for_status() # Raise an exception for bad status codes
        
        search_results = response.json()
        
        # Process the search results to create a concise context
        snippets = [
            f"Title: {result.get('title')}\nSnippet: {result.get('snippet')}\nLink: {result.get('link')}"
            for result in search_results.get('organic', [])
        ]
        
        if not snippets:
            return "No relevant search results found."
            
        return "\n\n".join(snippets)

    except requests.exceptions.RequestException as e:
        return f"An error occurred during the web search: {e}"