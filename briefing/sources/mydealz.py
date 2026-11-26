"""MyDealz – die heißesten Deals des Tages von mydealz.de.

Quelle: https://www.mydealz.de/rss/trending (offizieller RSS-Feed)
Kein Scraping nötig – sauberes RSS mit Preis, Händler und Kategorie.
"""
import re

import feedparser
import requests
from bs4 import BeautifulSoup

from briefing.sources._util import UA, dedupe, item

RSS_URL = "https://www.mydealz.de/rss/trending"


def fetch(cfg: dict) -> dict:
    md_cfg = cfg.get("mydealz", {})
    max_items = md_cfg.get("max_items", 12)

    resp = requests.get(RSS_URL, headers=UA, timeout=25)
    resp.raise_for_status()
    fp = feedparser.parse(resp.content)

    items = []
    for entry in fp.entries[:max_items]:
        title = entry.get("title", "")
        url = entry.get("link", "")

        # Preis aus pepper:merchant Tag extrahieren
        price = ""
        for el in entry.get("tags", []):
            label = el.get("label") or ""
            if "merchant" in label:
                price = el.get("value") or ""
                break

        # Kategorie
        category = ""
        for tag in entry.get("tags", []):
            scheme = tag.get("scheme") or ""
            if scheme.endswith("category"):
                category = tag.get("value") or ""
                break
        if not category:
            category = entry.get("category") or ""

        # Beschreibung bereinigen
        summary = BeautifulSoup(entry.get("description", ""), "lxml").get_text(" ", strip=True)
        summary = re.sub(r"\s+", " ", summary)[:200]

        # Kompakte Summary
        parts = []
        if price:
            parts.append(f"💰 {price}")
        if category:
            parts.append(f"📂 {category}")
        if parts:
            summary = " · ".join(parts) + " | " + summary[:150]
        else:
            summary = summary[:180]

        items.append(
            item(
                title=f"[Deal] {title[:150]}",
                url=url,
                source="mydealz",
                summary=summary,
            )
        )

    return {
        "key": "mydealz",
        "title": "🔥 MyDealz – Top-Deals heute",
        "lines": [],
        "items": dedupe(items),
        "items_label": "Heißeste Deals:",
        "comment": False,
    }
