"""Lokale News: Google News RSS je Ort/Landkreis, Zeitfenster-gefiltert."""
from briefing.sources._util import gn_feed, item, within_days


def fetch(cfg: dict) -> dict:
    region = cfg["region"]
    ln_cfg = cfg.get("local_news", {})
    window = ln_cfg.get("window_days", 2)
    max_per_town = ln_cfg.get("max_per_town", 8)

    queries = [f'"{term}"' for term in region.get("county_terms", [])]
    queries += [f'"{town}"' for town in region.get("towns", [])]

    items = []
    for query in queries:
        try:
            entries = [
                e for e in gn_feed(query) if within_days(e, window)
            ]
            for entry in entries[:max_per_town]:
                items.append(
                    item(
                        title=entry["title"],
                        url=entry["url"],
                        source="google-news",
                        summary=entry["summary"],
                    )
                )
        except Exception as exc:  # noqa: BLE001
            print(f"[local_news] {query}: {exc}")

    return {
        "key": "local_news",
        "title": f"📰 Lokales ({region.get('center_city', '')} & 50 km)",
        "lines": [],
        "items": items,
        "items_label": "Wichtig für dich:",
        "comment": False,
    }
