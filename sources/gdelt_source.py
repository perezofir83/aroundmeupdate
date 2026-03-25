"""
GDELT source — fetches geo-filtered events from the GDELT Global Knowledge Graph.
"""

import requests
from math import cos, radians


class GDELTSource:
    DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"
    GEO_API = "https://api.gdeltproject.org/api/v2/geo/geo"

    def __init__(self, config: dict):
        self.config = config
        self.location = config.get("location", {})
        self.max_records = config.get("sources", {}).get("gdelt", {}).get("max_records", 100)

    def fetch(self) -> list[dict]:
        articles = []
        address = self.location.get("address", "")
        parts = address.split(",")
        city = parts[1].strip() if len(parts) > 1 else parts[0].strip()

        try:
            params = {
                "query": f"{city} sourcelang:spa",
                "mode": "artlist",
                "maxrecords": min(self.max_records, 75),
                "format": "json",
                "timespan": "48h",
                "sort": "datedesc",
            }
            resp = requests.get(self.DOC_API, params=params, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                for art in data.get("articles", []):
                    articles.append({
                        "title": art.get("title", ""),
                        "description": art.get("seendate", ""),
                        "url": art.get("url", ""),
                        "source": art.get("domain", "GDELT"),
                        "published_at": art.get("seendate", ""),
                        "fetched_from": "gdelt",
                    })
        except Exception as e:
            print(f"  [GDELT DOC] Error: {e}")

        try:
            geo_params = {
                "query": "sourcelang:spa",
                "mode": "pointdata",
                "format": "json",
                "timespan": "48h",
                "maxpoints": 50,
                "locationcc": "MX",
            }
            resp = requests.get(self.GEO_API, params=geo_params, timeout=20)
            if resp.status_code == 200:
                text = resp.text.strip()
                if text and text.startswith(("{", "[")):
                    data = resp.json()
                    features = data if isinstance(data, list) else data.get("features", [])
                    for feat in features[:50]:
                        props = feat.get("properties", feat) if isinstance(feat, dict) else {}
                        if props.get("url"):
                            articles.append({
                                "title": props.get("name", ""),
                                "description": props.get("html", ""),
                                "url": props.get("url", ""),
                                "source": props.get("domain", "GDELT-GEO"),
                                "published_at": props.get("dateadded", ""),
                                "fetched_from": "gdelt_geo",
                            })
        except Exception as e:
            print(f"  [GDELT GEO] Error: {e}")

        seen = set()
        unique = []
        for art in articles:
            if art["url"] and art["url"] not in seen:
                seen.add(art["url"])
                unique.append(art)

        print(f"  [GDELT] Fetched {len(unique)} articles")
        return unique
