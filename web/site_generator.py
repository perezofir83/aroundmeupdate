"""
Static site generator — creates HTML pages for GitHub Pages.
Outputs embeddable HTML that can be copied into any website.
"""

import os
import json
import re
from datetime import datetime


class SiteGenerator:
    def __init__(self, config: dict):
        self.config = config
        self.business = config.get("business", {})
        self.docs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
        os.makedirs(self.docs_dir, exist_ok=True)
        nojekyll = os.path.join(self.docs_dir, ".nojekyll")
        if not os.path.exists(nojekyll):
            with open(nojekyll, "w") as f:
                f.write("")

    def save_brief(self, brief_md: str, date: str, address: str, article_count: int,
                   articles: list = None, insights: str = "") -> str:
        """Save brief as full page + embeddable widget + JSON data."""
        min_score = self.config.get("scoring", {}).get("min_relevance_score", 3)
        relevant = []
        if articles:
            relevant = [a for a in articles if a.get("relevance_score", 0) >= min_score and a.get("is_relevant", True)]
            relevant.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            # Deduplicate
            seen = set()
            unique = []
            for a in relevant:
                key = a.get("title", "")[:50].lower()
                if key not in seen:
                    seen.add(key)
                    unique.append(a)
            relevant = unique

        biz_name = self.business.get("name", "Local Brief")
        categories = self.config.get("categories", [])

        # Build article cards HTML
        cards_html = ""
        for cat in categories:
            cat_articles = [a for a in relevant if a.get("category") == cat["id"]]
            if not cat_articles:
                continue
            cards_html += f'<div class="cat-section"><h3>{cat["emoji"]} {cat["label"]}</h3>\n'
            for art in cat_articles:
                score = art.get("relevance_score", 0)
                summary = art.get("summary_es", art.get("title", ""))
                source = art.get("source", "")
                url = art.get("url", "")
                score_class = "high" if score >= 7 else "mid" if score >= 5 else "low"
                link = f'<a href="{url}" target="_blank" rel="noopener">{source}</a>' if url else source
                cards_html += f'''<div class="news-card {score_class}">
  <div class="score">{score}/10</div>
  <div class="content">
    <p class="summary">{summary}</p>
    <p class="source">📰 {link}</p>
  </div>
</div>\n'''
            cards_html += '</div>\n'

        # Build insights HTML
        insights_html = ""
        if insights:
            insights_lines = insights.strip().split("\n")
            insights_html = '<div class="insights-section"><h3>💡 Recomendaciones</h3>\n'
            for line in insights_lines:
                line = line.strip()
                if line:
                    insights_html += f'<div class="insight-card">{line}</div>\n'
            insights_html += '</div>\n'

        # Save JSON data for API/embedding
        json_data = {
            "date": date,
            "business": biz_name,
            "address": address,
            "article_count": len(relevant),
            "insights": insights,
            "articles": [{
                "title": a.get("title", ""),
                "summary": a.get("summary_es", a.get("title", "")),
                "category": a.get("category", ""),
                "score": a.get("relevance_score", 0),
                "source": a.get("source", ""),
                "url": a.get("url", ""),
            } for a in relevant],
        }
        json_path = os.path.join(self.docs_dir, f"data-{date}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        # Also save as latest.json
        latest_path = os.path.join(self.docs_dir, "latest.json")
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        # Save embeddable widget
        widget_html = self._generate_widget(date, biz_name, address, cards_html, insights_html, len(relevant))
        widget_path = os.path.join(self.docs_dir, "widget.html")
        with open(widget_path, "w", encoding="utf-8") as f:
            f.write(widget_html)

        # Save full page
        page = self._generate_full_page(date, biz_name, address, cards_html, insights_html, len(relevant))
        filename = f"brief-{date}.html"
        filepath = os.path.join(self.docs_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(page)

        self._update_index(date, address, len(relevant), filename)
        print(f"  [Web] Saved: {filepath}")
        print(f"  [Web] Widget: {widget_path}")
        print(f"  [Web] JSON: {json_path}")
        return filepath

    def _css(self) -> str:
        return """
* { margin: 0; padding: 0; box-sizing: border-box; }
.local-brief { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0e17; color: #e0e6ed; max-width: 800px; margin: 0 auto; }
.local-brief a { color: #58a6ff; text-decoration: none; }
.local-brief a:hover { text-decoration: underline; }
.brief-header { background: linear-gradient(135deg, #1a1f2e 0%, #0d1117 100%); border: 1px solid #21262d; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; text-align: center; }
.brief-header h2 { font-size: 1.4rem; color: #58a6ff; margin-bottom: 0.3rem; }
.brief-header .meta { color: #8b949e; font-size: 0.9rem; }
.cat-section { margin-bottom: 1.5rem; }
.cat-section h3 { color: #c9d1d9; font-size: 1.1rem; margin-bottom: 0.5rem; padding-bottom: 0.3rem; border-bottom: 1px solid #21262d; }
.news-card { display: flex; gap: 0.8rem; background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 0.8rem 1rem; margin: 0.4rem 0; transition: border-color 0.2s; }
.news-card:hover { border-color: #58a6ff; }
.news-card.high { border-left: 3px solid #f85149; }
.news-card.mid { border-left: 3px solid #d29922; }
.news-card.low { border-left: 3px solid #388bfd; }
.news-card .score { font-weight: 700; font-size: 0.85rem; color: #8b949e; min-width: 35px; text-align: center; padding-top: 2px; }
.news-card .summary { margin-bottom: 0.3rem; line-height: 1.4; }
.news-card .source { font-size: 0.8rem; color: #8b949e; }
.insights-section { background: linear-gradient(135deg, #0d1f0d 0%, #0d1117 100%); border: 1px solid #238636; border-radius: 12px; padding: 1.2rem; margin: 1.5rem 0; }
.insights-section h3 { color: #3fb950; margin-bottom: 0.8rem; }
.insight-card { background: #161b22; border-radius: 6px; padding: 0.7rem 1rem; margin: 0.4rem 0; line-height: 1.5; font-size: 0.95rem; }
.brief-footer { text-align: center; color: #8b949e; font-size: 0.85rem; padding: 1rem; border-top: 1px solid #21262d; margin-top: 1rem; }
"""

    def _generate_widget(self, date, biz_name, address, cards_html, insights_html, count) -> str:
        css = self._css()
        return f"""<!-- Local Brief Widget — embed this in any page -->
<div class="local-brief" id="local-brief-widget">
<style>{css}</style>
<div class="brief-header">
  <h2>📋 Resumen Diario — {date}</h2>
  <p class="meta">🏪 {biz_name} | 📍 {address}</p>
</div>
{cards_html}
{insights_html}
<div class="brief-footer">📊 {count} noticias relevantes | Actualizado: {date}</div>
</div>
<!-- End Local Brief Widget -->"""

    def _generate_full_page(self, date, biz_name, address, cards_html, insights_html, count) -> str:
        css = self._css()
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{biz_name} — Resumen {date}</title>
<style>
body {{ background: #0a0e17; padding: 1rem; }}
{css}
.back {{ display: inline-block; margin-bottom: 1rem; padding: 0.5rem 1rem; background: #21262d; border-radius: 6px; color: #c9d1d9; text-decoration: none; font-size: 0.9rem; }}
.back:hover {{ background: #30363d; }}
</style>
</head>
<body>
<div class="local-brief">
<a href="index.html" class="back">← Todos los resúmenes</a>
<div class="brief-header">
  <h2>📋 Resumen Diario — {date}</h2>
  <p class="meta">🏪 {biz_name} | 📍 {address}</p>
</div>
{cards_html}
{insights_html}
<div class="brief-footer">📊 {count} noticias relevantes</div>
</div>
</body>
</html>"""

    def _update_index(self, date, address, count, filename):
        briefs_json = os.path.join(self.docs_dir, "briefs.json")
        briefs = []
        if os.path.exists(briefs_json):
            try:
                with open(briefs_json, "r") as f:
                    briefs = json.load(f)
            except Exception:
                briefs = []

        entry = {"date": date, "address": address, "count": count, "file": filename}
        briefs = [b for b in briefs if b.get("date") != date]
        briefs.insert(0, entry)
        briefs = briefs[:365]

        with open(briefs_json, "w") as f:
            json.dump(briefs, f, ensure_ascii=False, indent=2)

        biz_name = self.business.get("name", "Local Brief")
        items_html = ""
        for b in briefs:
            items_html += f'''<a href="{b['file']}" class="brief-card">
<span class="date">{b['date']}</span>
<span class="count">{b['count']} noticias</span>
</a>\n'''

        index = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{biz_name} — Inteligencia Local</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0e17; color: #e0e6ed; min-height: 100vh; }}
.header {{ background: linear-gradient(135deg, #1a1f2e 0%, #0d1117 100%); border-bottom: 1px solid #21262d; padding: 2rem; text-align: center; }}
.header h1 {{ font-size: 1.8rem; background: linear-gradient(90deg, #58a6ff, #79c0ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.5rem; }}
.header .subtitle {{ color: #8b949e; font-size: 0.95rem; }}
.content {{ max-width: 700px; margin: 2rem auto; padding: 0 1rem; }}
.brief-card {{ display: flex; justify-content: space-between; align-items: center; background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 1rem 1.2rem; margin: 0.5rem 0; text-decoration: none; color: #e0e6ed; transition: border-color 0.2s; }}
.brief-card:hover {{ border-color: #58a6ff; }}
.date {{ font-weight: 600; }}
.count {{ color: #8b949e; font-size: 0.9rem; }}
.embed-info {{ background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 1rem; margin-top: 2rem; font-size: 0.85rem; color: #8b949e; }}
.embed-info code {{ background: #0d1117; padding: 0.2rem 0.4rem; border-radius: 4px; font-size: 0.8rem; }}
</style>
</head>
<body>
<div class="header">
<h1>🏪 {biz_name}</h1>
<p class="subtitle">📍 {address} | Inteligencia Comercial Diaria</p>
</div>
<div class="content">
<h2 style="color:#8b949e;margin-bottom:1rem;">Resúmenes Diarios</h2>
{items_html}
<div class="embed-info">
<strong>Para embeber en tu sitio web:</strong><br>
Usa <code>widget.html</code> o consume <code>latest.json</code> vía API.
</div>
</div>
</body>
</html>"""

        with open(os.path.join(self.docs_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(index)
