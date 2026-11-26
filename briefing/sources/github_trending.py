"""GitHub Trending (täglich) – HTML-Auswertung der öffentlichen Trending-Seite."""
import re

import requests
from bs4 import BeautifulSoup

from briefing.sources._util import UA, item

TRENDING_URL = "https://github.com/trending"


def fetch(cfg: dict) -> dict:
    resp = requests.get(TRENDING_URL, headers=UA, timeout=25)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    items = []
    for article in soup.select("article"):
        link = article.select_one("h2 a") or article.select_one("a[href]")
        if not link or not link.get("href"):
            continue
        href = link["href"]
        if not re.match(r"^/[^/]+/[^/]+/?$", href):
            continue
        url = "https://github.com" + href
        repo = href.strip("/")
        desc_el = article.select_one("p")
        desc = desc_el.get_text(strip=True) if desc_el else ""
        match = re.search(r"([\d.,]+)\s+stars today", article.get_text())
        stars = f"  (+{match.group(1)} ⭐ heute)" if match else ""
        lang_el = article.select_one("[itemprop='programmingLanguage']")
        lang = f" [{lang_el.get_text(strip=True)}]" if lang_el else ""
        items.append(
            item(
                title=f"{repo}{stars}{lang}",
                url=url,
                source="github-trending",
                summary=desc[:300],
            )
        )

    max_items = cfg.get("github_trending", {}).get("max_items", 20)
    return {
        "key": "github_trending",
        "title": "🐙 GitHub Trending (heute)",
        "lines": [],
        "items": items[:max_items],
        "items_label": "Für dich relevant:",
        "comment": False,
    }
