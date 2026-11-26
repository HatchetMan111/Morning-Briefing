"""Orchestrator: Module sammeln -> deduplizieren -> KI-Synthese -> Briefing.

run() liefert strukturierte Daten zurueck (dict) und speichert sie als
JSON unter data/briefings/<date>.json – Basis fuer CLI, Telegram und Web-UI.
"""
import datetime
import json
import pathlib
import traceback

import yaml
from dotenv import load_dotenv

load_dotenv()

from briefing import db, notify, render, synthesize  # noqa: E402
from briefing.filters import dedupe, passes_blocklist  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load_cfg() -> dict:
    return yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))


def _sources() -> dict:
    """Lazy Imports: ein kaputtes Modul legt nie den ganzen Lauf lahm."""
    from briefing.sources import (
        ai_news,
        auctions,
        companies,
        econ_calendar,
        fuel_prices,
        github_trending,
        kleinanzeigen,
        local_news,
        markets,
        mydealz,
        selfhosted,
        zoll_auktion,
    )
    return {
        "markets": markets,
        "econ_calendar": econ_calendar,
        "fuel_prices": fuel_prices,
        "local_news": local_news,
        "auctions": auctions,
        "zoll_auktion": zoll_auktion,
        "mydealz": mydealz,
        "companies": companies,
        "ai_news": ai_news,
        "selfhosted": selfhosted,
        "github_trending": github_trending,
        "kleinanzeigen": kleinanzeigen,
    }


def _context() -> str:
    path = ROOT / "profile" / "context.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _store_json(data: dict) -> pathlib.Path:
    out_dir = db.DATA / "briefings"
    out_dir.mkdir(parents=True, exist_ok=True)
    # Dateiname mit Stunde -> mehrere Briefings pro Tag möglich
    hour = data["generated_at"][11:13]  # "HH" aus ISO-Timestamp
    path = out_dir / f"{data['date']}_{hour}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def collect_briefings() -> list[str]:
    """Verfügbare Briefing-Daten (Datum-Strings, neueste zuerst)."""
    b_dir = db.DATA / "briefings"
    if not b_dir.exists():
        return []
    return sorted(
        (p.stem for p in b_dir.glob("*.json")),
        reverse=True,
    )


def load_briefing(date_str: str) -> dict | None:
    path = db.DATA / "briefings" / f"{date_str}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def run() -> dict:
    cfg = load_cfg()
    context = _context()
    fb_prompt = synthesize.build_feedback_prompt(db.load_feedback())
    modules_cfg = cfg.get("modules", {})
    today = datetime.date.today().isoformat()

    sections = []
    sources_status: dict[str, str] = {}
    for key, module in _sources().items():
        if not modules_cfg.get(key, {}).get("enabled", False):
            continue
        try:
            result = module.fetch(cfg)
            if result:
                sections.append(result)
                sources_status[key] = "ok"
                print(f"[{key}] ok")
        except Exception as exc:  # noqa: BLE001 - Fehlerprotokoll, Lauf geht weiter
            sources_status[key] = f"fehler: {exc}"
            print(f"[{key}] FEHLER: {exc}")
            traceback.print_exc()

    # ==================== WOCHENRÜCKBLICK ====================
    from briefing import weekly as weekly_mod
    if weekly_mod.should_generate(cfg):
        try:
            wr_sec = weekly_mod.generate(cfg)
            if wr_sec:
                sections.append(wr_sec)
                sources_status["weekly_review"] = "ok"
                print("[weekly_review] ok")
        except Exception as exc:  # noqa: BLE001
            sources_status["weekly_review"] = f"fehler: {exc}"
            print(f"[weekly_review] FEHLER: {exc}")

    # ==================== ALERTS & PREIS-TRACKER ====================
    from briefing import alerts as alerts_mod
    from briefing import price_watch as pw_mod

    # Alle Items aus allen Sektionen für Alert-Prüfung sammeln
    all_raw_items = []
    for sec in sections:
        all_raw_items.extend(sec.get("items", []))

    # Keyword-Alerts prüfen
    alert_hits = alerts_mod.check_alerts(all_raw_items)
    alert_sec = alerts_mod.alert_section(alert_hits)
    if alert_sec:
        sections.insert(0, alert_sec)
        sources_status["alerts"] = f"{len(alert_hits)} Treffer"
        print(f"[alerts] {len(alert_hits)} Treffer")

    # Sofortige Telegram-Benachrichtigung bei Alerts
    if alert_hits:
        alert_msg = alerts_mod.format_alert_notification(alert_hits)
        notify.send(alert_msg)

    # Preis-Tracker (eBay)
    pw_triggered = pw_mod.check_price_watches()
    pw_sec = pw_mod.price_watch_section(pw_triggered)
    if pw_sec:
        sections.insert(0, pw_sec)
        sources_status["price_watch"] = f"{len(pw_triggered)} unter Limit"
        print(f"[price_watch] {len(pw_triggered)} unter Limit")
        pw_msg = pw_mod.format_price_alert(pw_triggered)
        notify.send(pw_msg)

    # ==================== BRIEFING-RENDERING ====================
    section_bodies = []   # (titel, html-body) für Telegram/Archiv
    data_sections = []    # strukturierte Daten für Web-UI
    for sec in sections:
        items = [i for i in sec.get("items", []) if passes_blocklist(i, cfg)]
        items = dedupe(items)
        items = db.filter_new(items, sec["key"])
        scored = []
        if items:
            enriched = synthesize.enrich_items(items, context, fb_prompt, cfg)
            enriched.sort(key=lambda x: x.get("ai_score", 50), reverse=True)
            max_items = int(cfg.get("ai", {}).get("max_items_per_section", 8))
            scored = enriched[:max_items]
            db.mark_seen(items, sec["key"])

        commentary = ""
        if (
            sec.get("comment")
            and cfg.get("ai", {}).get("commentary", True)
            and sec.get("lines")
        ):
            commentary = synthesize.commentate(sec["title"], sec["lines"], context)

        body = render.section_body(sec, scored, commentary)
        if body:
            section_bodies.append((sec["title"], body))

        data_sections.append(
            {
                "key": sec["key"],
                "title": sec["title"],
                "lines": sec.get("lines", []),
                "commentary": commentary,
                "items": [
                    {
                        "title": it.get("title", ""),
                        "url": it.get("url", ""),
                        "summary": it.get("ai_summary") or it.get("summary", ""),
                        "score": it.get("ai_score", 50),
                        "source": it.get("source", ""),
                    }
                    for it in scored
                ],
            }
        )

    # ==================== TOP STORIES & CHARTS ====================
    # Die 5 wichtigsten Items über alle Sektionen (nach KI-Score)
    all_scored = []
    for sec in data_sections:
        for it in sec.get("items", []):
            if it.get("score", 0) >= 30:  # Mindestrelevanz
                all_scored.append({**it, "section": sec["title"]})
    all_scored.sort(key=lambda x: x.get("score", 0), reverse=True)
    top_stories = all_scored[:5]

    # Chart-Daten: vom markets-Modul direkt mitgeliefert
    market_chart = []
    for sec in sections:
        if sec.get("chart_data"):
            market_chart = sec["chart_data"]
            break

    # ==================== ZUSAMMENFASSUNG ====================
    total_items = sum(len(s.get("items", [])) for s in data_sections)
    full_html = render.briefing_html(section_bodies)
    notify.send(full_html)
    render.archive(full_html)

    data = {
        "date": today,
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "sources": sources_status,
        "sections": data_sections,
        "top_stories": top_stories,
        "market_chart": market_chart,
        "stats": {
            "total_items": total_items,
            "section_count": len(data_sections),
            "alert_count": len(alert_hits),
        },
    }
    json_path = _store_json(data)
    stats = ", ".join(f"{t}: ok" for t, _ in section_bodies) or "keine Sektionen"
    print(f"Briefing fertig ({stats}) – JSON: {json_path}")
    return data


if __name__ == "__main__":
    run()
