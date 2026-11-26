"""Firmen der Region: Tagesbewegung regionaler Aktien + Neugründungs-News."""
import time

import yfinance as yf

from briefing.sources._util import gn_feed, item, within_days


def _movers(listed: list[dict], threshold: float) -> list[str]:
    lines = []
    for company in listed:
        try:
            hist = yf.Ticker(company["ticker"]).history(period="5d")
            if len(hist) < 2:
                continue
            pct = (hist["Close"].iloc[-1] / hist["Close"].iloc[-2] - 1) * 100
            if abs(pct) >= threshold:
                emoji = "📈" if pct > 0 else "📉"
                lines.append(
                    f"{emoji} {company['name']} ({company['ticker']}): {pct:+.1f} % heute"
                )
        except Exception as exc:  # noqa: BLE001
            print(f"[companies] {company.get('name')}: {exc}")
    return lines


def _news_queries(cfg: dict) -> list[tuple[str, int, str]]:
    """(Query, Zeitfenster in Tagen, Quelle) – ortsbezogene Firmennachrichten."""
    region = cfg["region"]
    ccfg = cfg.get("companies", {})
    founders_window = ccfg.get("founders_window_days", 7)

    # Ortsliste extrahieren (unterstützt string und dict Format)
    raw_towns = region.get("towns", [])
    town_names = []
    for t in raw_towns:
        if isinstance(t, dict):
            town_names.append(t.get("name", ""))
        else:
            town_names.append(str(t))

    queries: list[tuple[str, int, str]] = []
    for town in [t for t in town_names if t][:8]:
        queries.append((
            f'"{town}" (Neugründung OR Startup OR "neues Unternehmen" '
            f"OR Eröffnung OR eröffnet)",
            founders_window,
            "gruendung",
        ))
    for company in ccfg.get("listed", []):
        queries.append((f'"{company["name"]}"', 3, "firma-news"))
    return queries


def fetch(cfg: dict) -> dict:
    ccfg = cfg.get("companies", {})
    lines = _movers(
        ccfg.get("listed", []), ccfg.get("move_threshold_pct", 3.0)
    )

    items = []
    for query, window, source in _news_queries(cfg):
        try:
            entries = [e for e in gn_feed(query) if within_days(e, window)]
            items += [
                item(title=e["title"], url=e["url"], source=source,
                     summary=e["summary"])
                for e in entries[:5]
            ]
        except Exception as exc:  # noqa: BLE001
            print(f"[companies] {query}: {exc}")

    return {
        "key": "companies",
        "title": "🏢 Firmen & Neugründungen (Region)",
        "lines": lines,
        "items": items,
        "items_label": "Neues aus der Region:",
        "comment": bool(lines),
    }
