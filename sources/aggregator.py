"""
Aggregator — fetches from all sources, deduplicates, and stores in SQLite.
"""

import os
import sqlite3
import hashlib
from datetime import datetime

from sources.newsapi_source import NewsAPISource
from sources.google_rss_source import GoogleRSSSource
from sources.gdelt_source import GDELTSource


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "briefs", "articles.db")


def get_db(db_path=None):
    path = db_path or DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id TEXT PRIMARY KEY,
            title TEXT,
            description TEXT,
            url TEXT UNIQUE,
            source TEXT,
            published_at TEXT,
            fetched_from TEXT,
            fetched_at TEXT,
            category TEXT,
            relevance_score REAL,
            summary_he TEXT,
            is_relevant INTEGER DEFAULT 1
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS briefs (
            date TEXT PRIMARY KEY,
            location_address TEXT,
            content_md TEXT,
            created_at TEXT,
            article_count INTEGER
        )
    """)
    conn.commit()
    return conn


def article_id(article: dict) -> str:
    url = article.get("url", "")
    title = article.get("title", "")
    raw = f"{url}|{title}"
    return hashlib.md5(raw.encode()).hexdigest()


def fetch_all(config: dict) -> list[dict]:
    articles = []

    print("\n📡 Fetching from NewsAPI...")
    try:
        src = NewsAPISource(config)
        articles.extend(src.fetch())
    except Exception as e:
        print(f"  [NewsAPI] Error: {e}")

    print("📡 Fetching from Google News RSS...")
    try:
        src = GoogleRSSSource(config)
        articles.extend(src.fetch())
    except Exception as e:
        print(f"  [Google RSS] Error: {e}")

    print("📡 Fetching from GDELT...")
    try:
        src = GDELTSource(config)
        articles.extend(src.fetch())
    except Exception as e:
        print(f"  [GDELT] Error: {e}")

    # Deduplicate by URL
    seen = set()
    unique = []
    for art in articles:
        url = art.get("url", "")
        if url and url not in seen:
            seen.add(url)
            art["id"] = article_id(art)
            unique.append(art)

    print(f"\n📊 Total unique articles: {len(unique)}")
    return unique


def store_articles(articles: list[dict], config: dict):
    try:
        conn = get_db()
    except Exception:
        conn = get_db(os.path.join("/tmp", "articles.db"))

    new_count = 0
    for art in articles:
        try:
            conn.execute("""
                INSERT OR IGNORE INTO articles
                (id, title, description, url, source, published_at, fetched_from, fetched_at,
                 category, relevance_score, summary_he, is_relevant)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                art.get("id", article_id(art)),
                art.get("title", ""),
                art.get("description", ""),
                art.get("url", ""),
                art.get("source", ""),
                art.get("published_at", ""),
                art.get("fetched_from", ""),
                datetime.now().isoformat(),
                art.get("category", ""),
                art.get("relevance_score", 0),
                art.get("summary_he", ""),
                1 if art.get("is_relevant", True) else 0,
            ))
            new_count += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    print(f"💾 Stored {new_count} new articles in database")
