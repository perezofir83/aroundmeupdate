"""
Test run — executes the pipeline with demo data fallback.
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from main import load_config
from sources.aggregator import fetch_all, store_articles, get_db
from analysis.analyzer import ArticleAnalyzer
from web.site_generator import SiteGenerator
from demo_data import get_demo_articles


def test():
    print("LOCAL BRIEF — TEST RUN")
    print("=" * 60)

    config = load_config()
    location = config.get("location", {})
    address = location.get("address", "Unknown")
    today = datetime.now().strftime("%Y-%m-%d")

    print(f"\nLOCAL INTELLIGENCE BRIEF")
    print(f"Location: {address}")
    print(f"Date: {today}")
    print("=" * 60)

    # Step 1: Try live sources, fall back to demo
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
    has_analysis = all(a.get("category") and a.get("summary_he") for a in articles)
    if has_analysis:
        print("  Articles already analyzed (demo mode)")
        analyzed = articles
    else:
        analyzer = ArticleAnalyzer(config)
        analyzed = analyzer.analyze_batch(articles)

    # Step 4: Generate brief
    print(f"\nStep 4: Generating brief...")
    analyzer = ArticleAnalyzer(config)
    brief = analyzer.generate_brief(analyzed)

    # Step 5: Save to web
    print(f"\nStep 5: Saving to web...")
    min_score = config.get("scoring", {}).get("min_relevance_score", 3)
    relevant_count = len([a for a in analyzed if a.get("relevance_score", 0) >= min_score])
    site_gen = SiteGenerator(config)
    site_gen.save_brief(brief, today, address, relevant_count)

    # Save brief to text file
    output_path = os.path.join(os.path.dirname(__file__), "briefs", "latest_test_brief.txt")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(brief)

    print(f"\n{'='*60}")
    print(f"Pipeline complete!")
    print(f"Brief saved to: {output_path}")
    print(f"Relevant articles: {relevant_count}")
    print(f"{'='*60}")
    print(f"\nBRIEF OUTPUT:\n")
    print(brief)

    return brief


if __name__ == "__main__":
    test()
