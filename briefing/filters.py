"""Regelbasierte Vorfilter – billig, laufen vor der KI."""
from briefing.sources._util import dedupe  # noqa: F401  (re-export)


def passes_blocklist(item: dict, cfg: dict) -> bool:
    blocked = [b.lower() for b in cfg.get("filters", {}).get("blocked_keywords", [])]
    if not blocked:
        return True
    haystack = (item.get("title", "") + " " + item.get("summary", "")).lower()
    return not any(b in haystack for b in blocked)
