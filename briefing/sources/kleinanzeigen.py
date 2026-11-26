"""Kleinanzeigen-Preischeck (OPTIONAL, standardmaessig aus).

Rechtlicher Hinweis: kein offizielles API. Wir fragen maximal
1x taeglich je konfigurierter Such-URL ab. Details in README.
"""
import time

import requests
from bs4 import BeautifulSoup

from briefing.sources._util import UA, item


def fetch(cfg: dict) -> dict:
    kcfg = cfg.get("kleinanzeigen", {})
    urls = kcfg.get("search_urls", [])
    items = []
    for url in urls:
        try:
            resp = requests.get(url, headers=UA, timeout=25)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            for article in soup.select("article"):
                link = article.select_one("a[href*='/s-anzeige/']")
                if not link or not link.get("href"):
                    continue
                href = link["href"]
                if href.startswith("/"):
                    href = "https://www.kleinanzeigen.de" + href
                title = link.get_text(" ", strip=True)
                price_el = article.select_one("[class*='price']")
                price = price_el.get_text(strip=True) if price_el else ""
                items.append(
                    item(
                        title=title,
                        url=href,
                        source="kleinanzeigen",
                        summary=f"Preis: {price} – KI prüft Unterbewertung",
                    )
                )
            time.sleep(3)  # besonders sanft
        except Exception as exc:  # noqa: BLE001
            print(f"[kleinanzeigen] {url}: {exc}")

    return {
        "key": "kleinanzeigen",
        "title": "🔎 Kleinanzeigen-Preischeck",
        "lines": [],
        "items": items,
        "items_label": "Möglicherweise unterbewertet:",
        "comment": False,
    }
