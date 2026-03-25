"""
Local Intelligence Brief — main pipeline.
Fetches news, analyzes with LLM, generates brief, delivers.
"""

import os
import sys
import yaml
from datetime import datetime

from sources.aggregator import fetch_all, store_articles, get_db
from analysis.analyzer import ArticleAnalyzer
from delivery.telegram_delivery import TelegramDelivery
from web.site_generator import SiteGenerator


def load_config(config_path=None) -> dict:
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")

    # Load .env file if present
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_pipeline(config: dict, deliver: bool = False, verbose: bool = True) -> str:
    location = config.get("location", {})
    address = location.get("address", "Unknown")
    today = datetime.now().strftime("%Y-%m-%d")

    if verbose:
        print(f"\n{'='*60}")
        print(f"📋 LOCAL INTELLIGENCE BRIEF")
        print(f"📍 Location: {address}")
        print(f"📅 Date: {today}")
        print(f"{'='*60}")

    # Step 1: Fetch
    if verbose:
        print(f"\n🔄 Step 1: Fetching articles...")
    articles = fetch_all(config)

    if not articles:
        if verbose:
            print("⚠️  No articles found from any source.")
        return f"📋 *Resumen Diario — {today}*\n📍 {address}\n\n⚠️ No se encontraron noticias nuevas hoy."

    # Step 2: Store
    if verbose:
        print(f"\n💾 Step 2: Storing articles...")
    store_articles(articles, config)

    # Step 3: Analyze
    if verbose:
        print(f"\n🧠 Step 3: Analyzing articles...")
    analyzer = ArticleAnalyzer(config)
    analyzed = analyzer.analyze_batch(articles)

    # Step 4: Generate insights
    if verbose:
        print(f"\n💡 Step 4: Generating insights...")
    insights = analyzer.generate_insights(analyzed)

    # Step 5: Generate brief
    if verbose:
        print(f"\n📝 Step 5: Generating brief...")
    brief = analyzer.generate_brief(analyzed, insights)

    # Step 6: Save to web
    if verbose:
        print(f"\n🌐 Step 6: Saving to web...")
    min_score = config.get("scoring", {}).get("min_relevance_score", 3)
    relevant_count = len([a for a in analyzed if a.get("relevance_score", 0) >= min_score])
    site_gen = SiteGenerator(config)
    site_gen.save_brief(brief, today, address, relevant_count, analyzed, insights)

    # Step 7: Deliver
    if deliver:
        if verbose:
            print(f"\n📤 Step 7: Delivering...")
        method = config.get("delivery", {}).get("method", "telegram")
        if method == "telegram":
            tg = TelegramDelivery(config)
            tg.send(brief)
    else:
        if verbose:
            print(f"\n📤 Step 7: Delivery skipped (test mode)")

    if verbose:
        print(f"\n{'='*60}")
        print(f"✅ Pipeline complete!")
        print(f"{'='*60}")

    return brief


if __name__ == "__main__":
    config = load_config()
    deliver = "--deliver" in sys.argv
    brief = run_pipeline(config, deliver=deliver)
    print(f"\n{brief}")
