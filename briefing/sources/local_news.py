"""Lokale News: Google News RSS mit PLZ + Ortsname, intelligent gefiltert.

Queries kombinieren Postleitzahl UND Ortsname für präzisere Treffer.
Polizeiberichte werden per Ausschluss-Operatoren eliminiert.
"""
from briefing.sources._util import gn_feed, item, within_days


def _town_list(cfg: dict) -> list[tuple[str, str]]:
    """Extrahiert (name, plz) Paare aus der Konfiguration."""
    towns = cfg.get("region", {}).get("towns", [])
    result = []
    for t in towns:
        if isinstance(t, dict):
            result.append((t.get("name", ""), t.get("plz", "")))
        else:
            result.append((str(t), ""))
    return result


def _build_query(name: str, plz: str, excludes: list[str]) -> str:
    """Google News Query mit PLZ, Ortsname und Ausschluss-Begriffen."""
    if plz:
        query = f'"{plz}" OR "{name}"'
    else:
        query = f'"{name}"'
    for ex in excludes:
        query += f' -"{ex}"'
    return query


def fetch(cfg: dict) -> dict:
    region = cfg["region"]
    ln_cfg = cfg.get("local_news", {})
    window = ln_cfg.get("window_days", 2)
    max_per_town = ln_cfg.get("max_per_town", 8)
    excludes = ln_cfg.get("exclude_keywords", [])

    towns = _town_list(cfg)
    queries = []
    for term in region.get("county_terms", []):
        queries.append(_build_query(term, "", excludes))
    for name, plz in towns:
        queries.append(_build_query(name, plz, excludes))

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
