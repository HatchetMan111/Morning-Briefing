"""Zoll-Auktion.de – offizielle Versteigerungen von Bund, Ländern und Gemeinden.

Quelle: https://www.zoll-auktion.de
Methode: HTML-Scraping der Auktionsübersicht (Bootstrap-Struktur).
Parser-Felder (per Aria-Label): Artikelstandort, Restlaufzeit, Gebotsstatus.
"""
import re
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from briefing.sources._util import UA, item

BASE = "https://www.zoll-auktion.de"
OVERVIEW_URL = f"{BASE}/auktion/auktionsuebersicht.php?n0=search"


def _parse_tile(tile) -> dict | None:
    """Eine Auktions-Kachel in das Item-Schema überführen."""
    h4 = tile.select_one("h4.sr-only")
    link = tile.select_one("a[href*='/auktion/produkt/']")
    if not h4 or not link:
        return None

    title = h4.get_text(strip=True)
    url = BASE + link.get("href", "")

    location, time_left, bids, price = "", "", "", ""
    for li in tile.select("ul[aria-label='Auktionsdetails'] > li"):
        text = li.get_text(" ", strip=True)
        icon = li.select_one("[aria-label]")
        label = icon.get("aria-label", "") if icon else ""
        if "Artikelstandort" in label:
            location = text
        elif "Restlaufzeit" in label:
            time_left = text
        elif "Gebotsstatus" in label:
            bids = text

    price_el = tile.select_one("p.text-right span.font-weight-bold")
    if price_el:
        price = price_el.get_text(strip=True)

    summary_parts = []
    if location:
        summary_parts.append(f"📍 {location}")
    if price:
        summary_parts.append(f"💰 {price}")
    if bids:
        summary_parts.append(f"🔨 {bids}")
    if time_left:
        summary_parts.append(f"⏱ {time_left}")

    return item(
        title=f"[Zoll] {title}",
        url=url,
        source="zoll-auktion",
        summary=" · ".join(summary_parts),
    )


def fetch(cfg: dict) -> dict:
    zcfg = cfg.get("zoll_auktion", {})
    max_pages = zcfg.get("max_pages", 3)

    items = []
    for page in range(1, max_pages + 1):
        url = OVERVIEW_URL
        if page > 1:
            url += f"&pagination={page}"
        try:
            resp = requests.get(url, headers=UA, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            for tile in soup.select("ul.auktionen_kachel_list > li"):
                parsed = _parse_tile(tile)
                if parsed:
                    items.append(parsed)
        except Exception as exc:  # noqa: BLE001
            print(f"[zoll_auktion] Seite {page}: {exc}")
        time.sleep(2)

    return {
        "key": "zoll_auktion",
        "title": "🏛️ Zoll-Auktionen (offiziell)",
        "lines": [],
        "items": items,
        "items_label": "Aktuelle Auktionen:",
        "comment": False,
    }
