import os
import requests
from dotenv import load_dotenv

load_dotenv()

def get_investment_news():
    api_key = os.getenv("NEWS_API_KEY")
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": "investment OR stock market OR finance",
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": 5,
        "apiKey": api_key
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if "articles" in data:
            articles = [(a["title"], a["url"]) for a in data["articles"]]
            news_context = "\n".join([f"{i+1}. {title} - {url}" for i, (title, url) in enumerate(articles)])
            return articles, news_context
    except Exception:
        return [("⚠️ Could not fetch news", "#")], "No fresh news available."
    return [], "No news available."
