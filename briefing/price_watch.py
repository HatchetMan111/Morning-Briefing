"""Preis-Tracker: beobachtet eBay-Suchen und warnt bei Schwellenwert.

Flow:
1. User definiert Watch: query="homelab server", threshold=150 EUR
2. Bei jedem Briefing-Lauf: eBay Browse API nach query durchsuchen
3. Niedrigster Preis <= threshold -> Alert + Preis-Update in DB
4. Preis-Historie fuer Trend-Analyse
"""
import os
import re

import requests

from briefing import db
from briefing.sources._util import UA

EBAY_API = "https://api.ebay.com/buy/browse/v1/item_summary/search"


def _search_ebay(query: str, limit: int = 10) -> list[dict]:
    """eBay Browse API - gibt Liste von {title, url, price} zurück."""
    token = os.environ.get("EBAY_BEARER_TOKEN", "").strip()
    if not token:
        return []
    try:
        resp = requests.get(
            EBAY_API,
            params={"q": query, "limit": str(limit)},
            headers={
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": "EBAY_DE",
                **UA,
            },
            timeout=25,
        )
        resp.raise_for_status()
        results = []
        for summary in resp.json().get("itemSummaries", []):
            price_raw = summary.get("price", {})
            try:
                price_val = float(price_raw.get("value", 0))
            except (ValueError, TypeError):
                continue
            results.append(
                {
                    "title": summary.get("title", ""),
                    "url": summary.get("itemWebUrl", ""),
                    "price": price_val,
                    "currency": price_raw.get("currency", "EUR"),
                }
            )
        return results
    except Exception as exc:  # noqa: BLE001
        print(f"[price_watch] eBay '{query}': {exc}")
        return []


def check_price_watches() -> list[dict]:
    """Alle aktiven Watches prüfen. Returns Liste von Treffern:
    [{"watch": {...}, "match": {...}}, ...]
    """
    watches = db.get_price_watches(active_only=True)
    if not watches:
        return []

    triggered = []
    for watch in watches:
        query = watch["query"]
        threshold = watch["threshold"] or 0
        results = _search_ebay(query)
        if not results:
            continue

        # Niedrigster Preis
        cheapest = min(results, key=lambda r: r["price"])
        db.update_price_watch(
            watch["id"], cheapest["price"], cheapest["title"], cheapest["url"]
        )

        if threshold > 0 and cheapest["price"] <= threshold:
            triggered.append({"watch": watch, "match": cheapest})

    return triggered


def format_price_alert(triggered: list[dict]) -> str:
    """Formatiert Preis-Alerts als Telegram-Nachricht."""
    if not triggered:
        return ""
    lines = ["💰 <b>PREIS-ALERT</b> – Schwellenwert erreicht:", ""]
    for t in triggered:
        w = t["watch"]
        m = t["match"]
        lines.append(
            f"📉 \"{w['query']}\" für {m['price']:.2f} EUR "
            f"(Limit: {w['threshold']:.0f} EUR)"
        )
        if m["url"]:
            lines.append(f"   <a href='{m['url']}'>{m['title'][:80]}</a>")
    return "\n".join(lines)


def price_watch_section(triggered: list[dict]) -> dict:
    """Erzeugt einen Briefing-Abschnitt für Preis-Alerts."""
    if not triggered:
        return {}
    from briefing.sources._util import item as mk_item

    lines = []
    items = []
    for t in triggered:
        w = t["watch"]
        m = t["match"]
        lines.append(
            f"📉 \"{w['query']}\": {m['price']:.2f} EUR "
            f"(Limit: {w['threshold']:.0f} EUR)"
        )
        items.append(
            mk_item(
                title=f"[Preis] {m['title']}",
                url=m["url"],
                source="price-watch",
                summary=f"Nur {m['price']:.2f} EUR (Limit: {w['threshold']:.0f})",
            )
        )
    return {
        "key": "price_watch",
        "title": "💰 Preis-Tracker",
        "lines": lines,
        "items": items,
        "items_label": "Angebote unter deinem Limit:",
        "comment": False,
    }
