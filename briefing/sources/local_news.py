"""Lokale News: Google News RSS je Ort/Landkreis, intelligent gefiltert.

Polizeiberichte und Unfälle werden per Ausschluss-Operatoren (-Begriff)
schon in der Query eliminiert und zusätzlich hart vorfiltered.
"""
from briefing.sources._util import gn_feed, item, within_days


def _build_query(town: str, excludes: list[str]) -> str:
    """Google News Query mit Ausschluss-Begriffen."""
    query = f'"{town}"'
    for ex in excludes:
        query += f' -"{ex}"'
    return query


def fetch(cfg: dict) -> dict:
    region = cfg["region"]
    ln_cfg = cfg.get("local_news", {})
    window = ln_cfg.get("window_days", 2)
    max_per_town = ln_cfg.get("max_per_town", 8)
    excludes = ln_cfg.get("exclude_keywords", [])

    queries = []
    for term in region.get("county_terms", []):
        queries.append(_build_query(term, excludes))
    for town in region.get("towns", []):
        queries.append(_build_query(town, excludes))

    # Lokale Wirtschafts-/Community-Keywords bevorzugen
    priority_patterns = [
        "Wirtschaft", "Unternehmen", "Investition", "Eröffnung", "Projekt",
        "Neueröffnung", "Auszeichnung", "Forschung", "Schule", "Kultur",
        "Veranstaltung", "Stadtrat", "Gemeinderat", "Planung", "Zukunft",
        "Digitalisierung", "Energie", "Klima", "Bahnhof", "Gewerbe",
    ]

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
            print(f"[local_news] {query[:50]}: {exc}")

    return {
        "key": "local_news",
        "title": f"📰 Lokales ({region.get('center_city', '')} & 50 km)",
        "lines": [],
        "items": items,
        "items_label": "Wichtig für dich:",
        "comment": False,
    }
