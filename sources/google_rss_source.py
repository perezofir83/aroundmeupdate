"""
Google News RSS source — fetches geo-targeted news via Google News RSS feeds.
"""

import feedparser
import urllib.parse


class GoogleRSSSource:
    BASE_URL = "https://news.google.com/rss/search"

    def __init__(self, config: dict):
        self.config = config
        self.location = config.get("location", {})
        self.max_results = config.get("sources", {}).get("google_rss", {}).get("max_results", 30)

    def _build_queries(self) -> list[str]:
        address = self.location.get("address", "")
        parts = [p.strip() for p in address.split(",")]
        city = parts[0] if parts else ""
        region = parts[1] if len(parts) > 1 else ""
        queries = []
        if city:
            queries.append(f"{city} noticias")
        if region:
            queries.append(f"{region} noticias")
        queries.append(f"{city} seguridad")
        queries.append(f"{city} eventos")
        return queries

    def fetch(self) -> list[dict]:
        articles = []
        seen_urls = set()
        queries = self._build_queries()

        for query in queries:
            if len(articles) >= self.max_results:
                break
            try:
                encoded = urllib.parse.quote(query)
                url = f"{self.BASE_URL}?q={encoded}&hl=es-419&gl=MX&ceid=MX:es-419"
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    link = entry.get("link", "")
                    if link in seen_urls:
                        continue
                    seen_urls.add(link)
                    articles.append({
                        "title": entry.get("title", ""),
                        "description": entry.get("summary", ""),
                        "url": link,
                        "source": entry.get("source", {}).get("title", "Google News"),
                        "published_at": entry.get("published", ""),
                        "fetched_from": "google_rss",
                    })
            except Exception as e:
                print(f"  [Google RSS] Error fetching '{query}': {e}")

        print(f"  [Google RSS] Fetched {len(articles)} articles")
        return articles
