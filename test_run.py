"""
Test run — executes the pipeline with demo data fallback.
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from main import load_config
from sources.aggregator import fetch_all, store_articles
from analysis.analyzer import ArticleAnalyzer
from web.site_generator import SiteGenerator
from demo_data import get_demo_articles


def test():
    print("LOCAL BRIEF — TEST RUN")
    print("=" * 60)

    config = load_config()
    location = config.get("location", {})
    address = location.get("address", "Unknown")
    biz_name = config.get("business", {}).get("name", "Local Brief")
    today = datetime.now().strftime("%Y-%m-%d")

    print(f"\n🏪 {biz_name}")
    print(f"📍 {address}")
    print(f"📅 {today}")
    print("=" * 60)

    # Step 1: Fetch
    print(f"\nStep 1: Fetching articles...")
    articles = fetch_all(config)

    if not articles:
        print("Live sources returned 0 articles. Loading demo data...")
        articles = get_demo_articles()
        print(f"Loaded {len(articles)} demo articles")

    # Step 2: Store
    print(f"\nStep 2: Storing articles...")
    store_articles(articles, config)

    # Step 3: Analyze
    print(f"\nStep 3: Analyzing articles...")
    analyzer = ArticleAnalyzer(config)
    has_analysis = all(a.get("category") and a.get("summary_es") for a in articles)
    if has_analysis:
        print("  Articles already analyzed (demo mode)")
        analyzed = articles
    else:
        analyzed = analyzer.analyze_batch(articles)

    # Step 4: Generate insights
    print(f"\nStep 4: Generating insights...")
    insights = analyzer.generate_insights(analyzed)

    # Step 5: Generate brief
    print(f"\nStep 5: Generating brief...")
    brief = analyzer.generate_brief(analyzed, insights)

    # Step 6: Save to web
    print(f"\nStep 6: Saving to web...")
    min_score = config.get("scoring", {}).get("min_relevance_score", 3)
    relevant_count = len([a for a in analyzed if a.get("relevance_score", 0) >= min_score])
    site_gen = SiteGenerator(config)
    site_gen.save_brief(brief, today, address, relevant_count, analyzed, insights)

    # Save text brief
    output_path = os.path.join(os.path.dirname(__file__), "briefs", "latest_test_brief.txt")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(brief)

    print(f"\n{'='*60}")
    print(f"Pipeline complete!")
    print(f"Relevant articles: {relevant_count}")
    print(f"{'='*60}")
    print(f"\n{brief}")

    return brief


if __name__ == "__main__":
    test()
