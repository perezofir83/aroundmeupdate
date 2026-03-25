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
            print(f"  [Analyzer] ANTHROPIC_API_KEY found (starts with {self.api_key[:20]}...)")
            return self._analyze_with_llm(articles)
        print("  [Analyzer] No ANTHROPIC_API_KEY found!")
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

        # Process articles in small batches to get reliable JSON
        batch_size = 5
        analyzed_count = 0
        for batch_start in range(0, len(articles), batch_size):
            batch = articles[batch_start:batch_start + batch_size]
            batch_text = ""
            for i, art in enumerate(batch):
                batch_text += f"\n[{i}] Title: {art.get('title', '')}\nSource: {art.get('source', '')}\n"

            batch_prompt = f"""Analyze these {len(batch)} news articles for someone in El Sauzal, Baja California, Mexico.
For each, give: category (one of: {cat_list}), relevance_score (1-10), summary_he (one line Hebrew summary).
Return ONLY a JSON array, no other text:
[{{"index":0,"category":"...","relevance_score":5,"summary_he":"...","is_relevant":true}}]

Articles:
{batch_text}"""

            try:
                print(f"  [Analyzer] Calling Claude for batch {batch_start//batch_size + 1}...")
                response = client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=2048,
                    messages=[{"role": "user", "content": batch_prompt}],
                )
                text = response.content[0].text.strip()
                # Extract JSON from response
                if "```" in text:
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                    text = text.strip()
                # Find the JSON array
                start = text.find("[")
                end = text.rfind("]") + 1
                if start >= 0 and end > start:
                    text = text[start:end]

                import re
                text = re.sub(r',\s*]', ']', text)  # Remove trailing commas

                results = json.loads(text)
                for r in results:
                    idx = r.get("index", 0)
                    if 0 <= idx < len(batch):
                        real_idx = batch_start + idx
                        articles[real_idx]["category"] = r.get("category", "general")
                        articles[real_idx]["relevance_score"] = r.get("relevance_score", 5)
                        articles[real_idx]["summary_he"] = r.get("summary_he", articles[real_idx].get("title", ""))
                        articles[real_idx]["is_relevant"] = r.get("is_relevant", True)
                        analyzed_count += 1
            except Exception as e:
                print(f"  [Analyzer] Batch error: {e}")
                for art in batch:
                    if not art.get("summary_he"):
                        art["summary_he"] = art.get("title", "")
                        art["category"] = art.get("category", "general")
                        art["relevance_score"] = 5
                        art["is_relevant"] = True

        print(f"  [Analyzer] LLM analyzed {analyzed_count}/{len(articles)} articles")

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
