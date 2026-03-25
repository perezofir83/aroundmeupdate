"""
Article analyzer — uses Claude LLM to categorize, score, and summarize articles.
Falls back to keyword-based analysis when no API key is available.
"""

import os
import json
from datetime import datetime


class ArticleAnalyzer:
    def __init__(self, config: dict):
        self.config = config
        self.categories = config.get("categories", [])
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.brief_language = config.get("brief_language", "he")

    def analyze_batch(self, articles: list[dict]) -> list[dict]:
        if self.api_key:
            return self._analyze_with_llm(articles)
        return self._analyze_with_keywords(articles)

    def _analyze_with_keywords(self, articles: list[dict]) -> list[dict]:
        print("  [Analyzer] Using keyword-based analysis (no ANTHROPIC_API_KEY)")
        for art in articles:
            if art.get("category") and art.get("summary_he"):
                continue
            title = (art.get("title", "") + " " + art.get("description", "")).lower()
            matched_cat = "general"
            max_matches = 0
            for cat in self.categories:
                matches = sum(1 for kw in cat.get("keywords_es", []) if kw in title)
                if matches > max_matches:
                    max_matches = matches
                    matched_cat = cat["id"]
            art["category"] = matched_cat
            art["relevance_score"] = art.get("relevance_score", min(5 + max_matches, 10))
            art["summary_he"] = art.get("summary_he", art.get("title", ""))
            art["is_relevant"] = True
        return articles

    def _analyze_with_llm(self, articles: list[dict]) -> list[dict]:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
        except Exception as e:
            print(f"  [Analyzer] LLM init failed: {e}. Falling back to keywords.")
            return self._analyze_with_keywords(articles)

        cat_list = ", ".join([c["id"] for c in self.categories])
        articles_text = ""
        for i, art in enumerate(articles):
            articles_text += f"\n[{i}] Title: {art.get('title', '')}\nDescription: {art.get('description', '')}\nSource: {art.get('source', '')}\n"

        prompt = f"""Analyze these news articles for a person living near El Sauzal, Baja California, Mexico.

For each article, provide:
1. category: one of [{cat_list}]
2. relevance_score: 1-10 (10=critical local news, 1=irrelevant)
3. summary_he: one-line summary in Hebrew
4. is_relevant: true/false

Articles:
{articles_text}

Return ONLY valid JSON array:
[{{"index": 0, "category": "...", "relevance_score": N, "summary_he": "...", "is_relevant": true}}, ...]"""

        try:
            response = client.messages.create(
                model="claude-sonnet-4-5-20250514",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            results = json.loads(text)
            for r in results:
                idx = r.get("index", 0)
                if 0 <= idx < len(articles):
                    articles[idx]["category"] = r.get("category", "general")
                    articles[idx]["relevance_score"] = r.get("relevance_score", 5)
                    articles[idx]["summary_he"] = r.get("summary_he", articles[idx].get("title", ""))
                    articles[idx]["is_relevant"] = r.get("is_relevant", True)
            print(f"  [Analyzer] LLM analyzed {len(results)} articles")
        except Exception as e:
            print(f"  [Analyzer] LLM error: {e}. Falling back to keywords.")
            return self._analyze_with_keywords(articles)

        return articles

    def generate_brief(self, articles: list[dict]) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        address = self.config.get("location", {}).get("address", "Unknown")
        min_score = self.config.get("scoring", {}).get("min_relevance_score", 3)

        relevant = [a for a in articles if a.get("relevance_score", 0) >= min_score and a.get("is_relevant", True)]
        relevant.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

        lines = [
            f"📋 *סיכום יומי — {today}*",
            f"📍 {address}",
            "━━━━━━━━━━━━━━━━━━━━━━\n",
        ]

        for cat in self.categories:
            cat_articles = [a for a in relevant if a.get("category") == cat["id"]]
            if not cat_articles:
                continue
            lines.append(f"\n*{cat['emoji']} {cat['label']}*")
            for art in cat_articles:
                score = art.get("relevance_score", 0)
                summary = art.get("summary_he", art.get("title", ""))
                source = art.get("source", "")
                lines.append(f"• [{score}/10] {summary} ({source})")

        lines.append(f"\n━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"📊 *סיכום:* {len(relevant)} כתבות רלוונטיות")

        return "\n".join(lines)
