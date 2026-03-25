"""
NewsAPI source — fetches articles from newsapi.org with location-based queries.
"""

import os
import requests


class NewsAPISource:
    BASE_URL = "https://newsapi.org/v2/everything"

    def __init__(self, config: dict):
        self.config = config
        self.api_key = os.getenv("NEWSAPI_KEY", "")
        self.location = config.get("location", {})
        self.page_size = config.get("sources", {}).get("newsapi", {}).get("page_size", 50)

    def _build_query(self) -> str:
        address = self.location.get("address", "")
        parts = [p.strip() for p in address.split(",")]
        city = parts[0] if parts else ""
        region = parts[1] if len(parts) > 1 else ""
        terms = [t for t in [city, region] if t]
        return " OR ".join(terms)

    def fetch(self) -> list[dict]:
        if not self.api_key:
            print("  [NewsAPI] No API key set (NEWSAPI_KEY). Skipping.")
            return []

        query = self._build_query()
        params = {
            "q": query,
            "language": self.config.get("language", "es"),
            "sortBy": "publishedAt",
            "pageSize": self.page_size,
            "apiKey": self.api_key,
        }

        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            articles = []
            for art in data.get("articles", []):
                articles.append({
                    "title": art.get("title", ""),
                    "description": art.get("description", ""),
                    "url": art.get("url", ""),
                    "source": art.get("source", {}).get("name", "NewsAPI"),
                    "published_at": art.get("publishedAt", ""),
                    "fetched_from": "newsapi",
                })
            print(f"  [NewsAPI] Fetched {len(articles)} articles")
            return articles
        except Exception as e:
            print(f"  [NewsAPI] Error: {e}")
            return []
