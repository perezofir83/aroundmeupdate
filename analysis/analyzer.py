"""
Article analyzer — uses Claude LLM to categorize, score, summarize,
and generate business insights for Mercado del Sauzal.
"""

import os
import json
import re
from datetime import datetime


class ArticleAnalyzer:
    def __init__(self, config: dict):
        self.config = config
        self.categories = config.get("categories", [])
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.brief_language = config.get("brief_language", "es")
        self.business = config.get("business", {})

    def _get_business_context(self) -> str:
        biz = self.business
        if not biz:
            return ""
        interests = "\n".join([f"- {i}" for i in biz.get("interests", [])])
        customers = "\n".join([f"- {c['type']}: {c['description']}" for c in biz.get("customers", [])])
        return f"""
NEGOCIO: {biz.get('name', '')} — {biz.get('type', '')}
UBICACIÓN: {biz.get('location', '')}
DESCRIPCIÓN: {biz.get('description', '')}
CLIENTES:
{customers}
INTERESES COMERCIALES:
{interests}"""

    def analyze_batch(self, articles: list[dict]) -> list[dict]:
        if self.api_key:
            return self._analyze_with_llm(articles)
        return self._analyze_with_keywords(articles)

    def _analyze_with_keywords(self, articles: list[dict]) -> list[dict]:
        print("  [Analyzer] Using keyword-based analysis (no ANTHROPIC_API_KEY)")
        for art in articles:
            if art.get("category") and art.get("summary_es"):
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
            art["summary_es"] = art.get("summary_es", art.get("title", ""))
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
        biz_context = self._get_business_context()

        batch_size = 5
        analyzed_count = 0
        for batch_start in range(0, len(articles), batch_size):
            batch = articles[batch_start:batch_start + batch_size]
            batch_text = ""
            for i, art in enumerate(batch):
                batch_text += f"\n[{i}] Title: {art.get('title', '')}\nSource: {art.get('source', '')}\n"

            batch_prompt = f"""Eres un analista de inteligencia comercial para un negocio local.
{biz_context}

Analiza estos {len(batch)} artículos de noticias. Para cada uno:
1. category: una de [{cat_list}]
2. relevance_score: 1-10 (10=impacto directo en el negocio, 1=irrelevante)
3. summary_es: resumen de una línea en español
4. is_relevant: true/false

Artículos:
{batch_text}

Responde SOLO con un JSON array, sin texto adicional:
[{{"index":0,"category":"...","relevance_score":5,"summary_es":"...","is_relevant":true}}]"""

            try:
                print(f"  [Analyzer] Calling Claude for batch {batch_start//batch_size + 1}...")
                response = client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=2048,
                    messages=[{"role": "user", "content": batch_prompt}],
                )
                text = response.content[0].text.strip()
                if "```" in text:
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                    text = text.strip()
                start = text.find("[")
                end = text.rfind("]") + 1
                if start >= 0 and end > start:
                    text = text[start:end]
                text = re.sub(r',\s*]', ']', text)

                results = json.loads(text)
                for r in results:
                    idx = r.get("index", 0)
                    if 0 <= idx < len(batch):
                        real_idx = batch_start + idx
                        articles[real_idx]["category"] = r.get("category", "general")
                        articles[real_idx]["relevance_score"] = r.get("relevance_score", 5)
                        articles[real_idx]["summary_es"] = r.get("summary_es", articles[real_idx].get("title", ""))
                        articles[real_idx]["is_relevant"] = r.get("is_relevant", True)
                        analyzed_count += 1
            except Exception as e:
                print(f"  [Analyzer] Batch error: {e}")
                for art in batch:
                    if not art.get("summary_es"):
                        art["summary_es"] = art.get("title", "")
                        art["category"] = art.get("category", "general")
                        art["relevance_score"] = 5
                        art["is_relevant"] = True

        print(f"  [Analyzer] LLM analyzed {analyzed_count}/{len(articles)} articles")
        return articles

    def generate_insights(self, articles: list[dict]) -> str:
        """Use LLM to generate business insights and action items."""
        if not self.api_key:
            return ""

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
        except Exception:
            return ""

        biz_context = self._get_business_context()
        min_score = self.config.get("scoring", {}).get("min_relevance_score", 3)
        relevant = [a for a in articles if a.get("relevance_score", 0) >= min_score]
        top_news = "\n".join([f"- [{a.get('relevance_score')}/10] {a.get('summary_es', a.get('title', ''))}" for a in relevant[:10]])

        prompt = f"""Eres un asesor estratégico para un negocio local.
{biz_context}

Basándote en estas noticias de hoy:
{top_news}

Genera 3-5 RECOMENDACIONES ACCIONABLES para el dueño del negocio.
Cada recomendación debe:
- Conectar una noticia específica con una oportunidad o riesgo para el negocio
- Ser práctica y ejecutable esta semana
- Considerar los dos tipos de clientes (locales regulares y de paso)

Formato: lista numerada, máximo 2 líneas por recomendación. Solo en español."""

        try:
            print("  [Insights] Generating business insights...")
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            insights = response.content[0].text.strip()
            print("  [Insights] Done!")
            return insights
        except Exception as e:
            print(f"  [Insights] Error: {e}")
            return ""

    def generate_brief(self, articles: list[dict], insights: str = "") -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        biz_name = self.business.get("name", "Local Brief")
        address = self.config.get("location", {}).get("address", "Unknown")
        min_score = self.config.get("scoring", {}).get("min_relevance_score", 3)

        relevant = [a for a in articles if a.get("relevance_score", 0) >= min_score and a.get("is_relevant", True)]
        relevant.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

        # Deduplicate by title similarity
        seen_titles = set()
        unique = []
        for a in relevant:
            title_key = a.get("title", "")[:50].lower()
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique.append(a)
        relevant = unique

        lines = [
            f"📋 *Resumen Diario — {today}*",
            f"🏪 {biz_name}",
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
                summary = art.get("summary_es", art.get("title", ""))
                source = art.get("source", "")
                url = art.get("url", "")
                if url:
                    lines.append(f"• [{score}/10] {summary}\n  📰 {source} — {url}")
                else:
                    lines.append(f"• [{score}/10] {summary} ({source})")

        if insights:
            lines.append(f"\n━━━━━━━━━━━━━━━━━━━━━━")
            lines.append(f"\n*💡 Recomendaciones para {biz_name}*")
            lines.append(insights)

        lines.append(f"\n━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"📊 *Total:* {len(relevant)} noticias relevantes")

        return "\n".join(lines)
