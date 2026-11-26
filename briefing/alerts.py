"""Keyword-Alerts: benachrichtigt bei Treffern in gesammelten Items.

Flow:
1. main.py sammelt alle Items aus allen Quellen
2. check_alerts() prueft jedes Item gegen alle aktiven Alerts
3. Neue Treffer (noch nie gefeuert) -> Alert-Liste + Telegram-Push
4. Treffer landen zusaetzlich als eigener Abschnitt im Briefing
"""
from briefing import db
from briefing.sources._util import dedupe


def check_alerts(all_items: list[dict]) -> list[dict]:
    """Prüft alle Items gegen alle aktiven Alerts.

    Returns Liste von Alert-Treffern:
    [{"alert_term", "alert_source", "item": {...}}, ...]
    Nur NEUE Treffer (nicht schon einmal gefeuert).
    """
    alerts = db.get_alerts(active_only=True)
    if not alerts or not all_items:
        return []

    hits = []
    for alert in alerts:
        term = alert["term"].lower()
        source_filter = alert["source_filter"].lower()

        for it in all_items:
            # Quellen-Filter ('*' = alle, sonst Quellenname)
            if source_filter != "*" and source_filter not in it.get("source", "").lower():
                continue

            # Term im Titel oder Summary?
            haystack = (it.get("title", "") + " " + it.get("summary", "")).lower()
            if term not in haystack:
                continue

            # Schon einmal gefeuert?
            item_id = it.get("id", "")
            if db.alert_already_fired(alert["id"], item_id):
                continue

            db.mark_alert_fired(alert["id"], item_id)
            hits.append(
                {
                    "alert_term": alert["term"],
                    "alert_source": alert["source_filter"],
                    "item": it,
                }
            )

    return hits


def format_alert_notification(hits: list[dict]) -> str:
    """Formatiert Alert-Treffer als Telegram-kompatible Nachricht."""
    if not hits:
        return ""
    lines = ["🔔 <b>ALERT</b> – deine Suchbegriffe wurden gefunden:", ""]
    for hit in hits:
        it = hit["item"]
        url = it.get("url", "")
        title = it.get("title", "")[:150]
        summary = it.get("summary", "")[:150]
        term = hit["alert_term"]
        line = f"🔍 <b>{term}</b>: "
        if url:
            line += f"<a href='{url}'>{title}</a>"
        else:
            line += title
        if summary:
            line += f"\n   <i>{summary}</i>"
        lines.append(line)
    return "\n".join(lines)


def alert_section(hits: list[dict]) -> dict:
    """Erzeugt einen Briefing-Abschnitt für Alert-Treffer."""
    if not hits:
        return {}
    items = [hit["item"] for hit in hits]
    # Für jeden Alert-Header gruppieren
    grouped: dict[str, list[dict]] = {}
    for hit in hits:
        grouped.setdefault(hit["alert_term"], []).append(hit["item"])

    lines = []
    for term, its in grouped.items():
        lines.append(f"🔍 \"{term}\": {len(its)} Treffer")

    return {
        "key": "alerts",
        "title": "🔔 Alert-Treffer",
        "lines": lines,
        "items": dedupe(items),
        "items_label": "Details:",
        "comment": False,
    }
