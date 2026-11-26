"""Auktionen & Versteigerungen im Umkreis.

Quellen:
- Zwangsversteigerungs-Hinweise ueber Google News (Amtsgericht-Bekannt-
  machungen schaffen es meist in die Lokalpresse; 14-Tage-Fenster)
- Eigene RSS-Feeds (custom_rss_urls) z.B. lokaler Auktionshaeuser
- Optional: eBay Browse API (offiziell, freies Developer-Konto)
"""
import os
import time

import feedparser
import requests

from briefing.sources._util import UA, dedupe, gn_feed, item, within_days

EBAY_API = "https://api.ebay.com/buy/browse/v1/item_summary/search"


def _zvg_items(towns: list[str], window: int) -> list[dict]:
    items = []
    for town in towns:
        try:
            entries = [
                e for e in gn_feed(f'"Zwangsversteigerung" "{town}"')
                if within_days(e, window)
            ]
            items += [
                item(title=e["title"], url=e["url"], source="zvg-news",
                     summary=e["summary"])
                for e in entries[:5]
            ]
        except Exception as exc:  # noqa: BLE001
            print(f"[auctions] ZVG {town}: {exc}")
    return items


def _custom_feeds(urls: list[str]) -> list[dict]:
    items = []
    for url in urls:
        try:
            resp = requests.get(url, headers=UA, timeout=25)
            fp = feedparser.parse(resp.content)
            for entry in fp.entries[:10]:
                items.append(item(title=entry.get("title", ""),
                                  url=entry.get("link", ""),
                                  source="auktionshaus"))
            time.sleep(1)
        except Exception as exc:  # noqa: BLE001
            print(f"[auctions] Feed {url}: {exc}")
    return items


def _ebay(searches: list[str]) -> list[dict]:
    token = os.environ.get("EBAY_BEARER_TOKEN", "").strip()
    if not token or not searches:
        return []
    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_DE",
    }
    items = []
    for query in searches:
        try:
            resp = requests.get(
                EBAY_API, params={"q": query, "limit": "10"},
                headers={**headers, **UA}, timeout=25,
            )
            for summary in resp.json().get("itemSummaries", []):
                price = summary.get("price", {})
                price_text = f"{price.get('value', '?')} {price.get('currency', '')}"
                items.append(
                    item(
                        title=f"[eBay] {summary.get('title', '')}",
                        url=summary.get("itemWebUrl", ""),
                        source="ebay",
                        summary=f"Preis: {price_text}",
                    )
                )
        except Exception as exc:  # noqa: BLE001
            print(f"[auctions] eBay '{query}': {exc}")
        time.sleep(1)
    return items


def fetch(cfg: dict) -> dict:
    acfg = cfg.get("auctions", {})

    # Ortsliste extrahieren (unterstützt string und dict Format)
    raw_towns = cfg["region"].get("towns", [])
    towns = []
    for t in raw_towns:
        if isinstance(t, dict):
            towns.append(t.get("name", ""))
        else:
            towns.append(str(t))
    towns = [t for t in towns if t][: acfg.get("towns_for_zvg", 6)]

    window = acfg.get("window_days", 14)

    items = _zvg_items(towns, window)
    items += _custom_feeds(acfg.get("custom_rss_urls", []))
    items += _ebay(acfg.get("ebay_searches", []))

    lines = []
    if not items:
        lines = [
            "Heute nichts gefunden. Tipp: Zoll-Auktionen unter zoll-auktion.de, "
            "amtliche ZVG-Bekanntmachungen beim Amtsgericht Bad Mergentheim prüfen."
        ]
    return {
        "key": "auctions",
        "title": "🔨 Auktionen & Versteigerungen (Umkreis)",
        "lines": lines,
        "items": dedupe(items),
        "items_label": "Interessante Treffer:",
        "comment": False,
    }
