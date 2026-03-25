"""
Static site generator — creates HTML pages for GitHub Pages.
"""

import os
import json
import re
from datetime import datetime


class SiteGenerator:
    def __init__(self, config: dict):
        self.config = config
        self.docs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
        os.makedirs(self.docs_dir, exist_ok=True)
        nojekyll = os.path.join(self.docs_dir, ".nojekyll")
        if not os.path.exists(nojekyll):
            with open(nojekyll, "w") as f:
                f.write("")

    def _md_to_html(self, md_text: str) -> str:
        html = md_text
        html = re.sub(r'\*([^*]+)\*', r'<strong>\1</strong>', html)
        html = html.replace("━━━━━━━━━━━━━━━━━━━━━━", "<hr>")
        lines = html.split("\n")
        result = []
        for line in lines:
            line = line.strip()
            if line.startswith("•"):
                result.append(f"<div class='item'>{line[1:].strip()}</div>")
            elif line.startswith("📋") or line.startswith("📍") or line.startswith("📊"):
                result.append(f"<div class='meta'>{line}</div>")
            elif line == "<hr>":
                result.append("<hr>")
            elif line:
                result.append(f"<p>{line}</p>")
        return "\n".join(result)

    def save_brief(self, brief_md: str, date: str, address: str, article_count: int) -> str:
        brief_html = self._md_to_html(brief_md)

        page = f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Brief — {date}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0e17; color: #e0e6ed; padding: 2rem; max-width: 800px; margin: 0 auto; }}
a {{ color: #58a6ff; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
.meta {{ color: #8b949e; margin: 0.3rem 0; font-size: 1.1rem; }}
strong {{ color: #58a6ff; display: block; margin-top: 1.5rem; font-size: 1.2rem; }}
.item {{ background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 0.8rem 1rem; margin: 0.4rem 0; }}
hr {{ border: none; border-top: 1px solid #21262d; margin: 1.5rem 0; }}
.back {{ display: inline-block; margin-bottom: 1.5rem; padding: 0.5rem 1rem; background: #21262d; border-radius: 6px; }}
</style>
</head>
<body>
<a href="index.html" class="back">← כל העדכונים</a>
{brief_html}
</body>
</html>"""

        filename = f"brief-{date}.html"
        filepath = os.path.join(self.docs_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(page)

        self._update_index(date, address, article_count, filename)
        print(f"  [Web] Saved brief: {filepath}")
        return filepath

    def _update_index(self, date: str, address: str, count: int, filename: str):
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

        self._generate_index(briefs, address)

    def _generate_index(self, briefs: list, address: str):
        items_html = ""
        for b in briefs:
            items_html += f"""<a href="{b['file']}" class="brief-card">
<span class="date">{b['date']}</span>
<span class="count">{b['count']} כתבות</span>
</a>\n"""

        index = f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Local Intelligence Brief</title>
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
</style>
</head>
<body>
<div class="header">
<h1>Local Intelligence Brief</h1>
<p class="subtitle">📍 {address}</p>
</div>
<div class="content">
<h2 style="color:#8b949e;margin-bottom:1rem;">עדכונים יומיים</h2>
{items_html}
</div>
</body>
</html>"""

        with open(os.path.join(self.docs_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(index)
