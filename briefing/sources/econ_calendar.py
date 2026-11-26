"""Wirtschaftskalender (heute) – ForexFactory-Kalender (frei nutzbares JSON)."""
import datetime
import time
from zoneinfo import ZoneInfo

import requests

from briefing.sources._util import UA

URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
FLAGS = {
    "USD": "🇺🇸", "EUR": "🇪🇺", "DEU": "🇩🇪", "GBP": "🇬🇧",
    "CNY": "🇨🇳", "JPY": "🇯🇵", "FOMC": "🇺🇸", "CAD": "🇨🇦", "AUD": "🇦🇺",
}


def fetch(cfg: dict) -> dict:
    ec_cfg = cfg.get("econ_calendar", {})
    countries = set(ec_cfg.get("countries", ["USD", "EUR", "DEU"]))
    impacts = set(ec_cfg.get("impacts", ["High"]))
    tz = ZoneInfo(cfg["run"]["timezone"])
    now = datetime.datetime.now(tz)

    resp = None
    for attempt in range(2):
        resp = requests.get(URL, headers=UA, timeout=25)
        if resp.status_code == 200:
            break
        time.sleep(20)  # 429 abwarten und einmal wiederholen
    if resp is None or resp.status_code != 200:
        raise RuntimeError(f"Wirtschaftskalender HTTP {resp.status_code if resp else '??'}")
    events = resp.json()

    lines = []
    for event in events:
        try:
            dt = datetime.datetime.fromisoformat(event["date"])
        except (KeyError, ValueError):
            continue
        if dt.date() != now.date():
            continue
        country = event.get("country", "")
        if country not in countries:
            continue
        impact = event.get("impact", "")
        medium_eu = impact == "Medium" and country in ("EUR", "DEU")
        if impact not in impacts and not medium_eu:
            continue
        flag = FLAGS.get(country, "🌍")
        extras = []
        if event.get("forecast"):
            extras.append(f"Prog: {event['forecast']}")
        if event.get("previous"):
            extras.append(f"zuvor: {event['previous']}")
        line = f"{dt.astimezone(tz):%H:%M} {flag} {event.get('title', '')}"
        if extras:
            line += f" ({', '.join(extras)})"
        lines.append(line)

    lines.sort()
    lines = lines[: ec_cfg.get("max_events", 10)]
    return {
        "key": "econ_calendar",
        "title": "📅 Wirtschaftskalender (heute)",
        "lines": lines,
        "items": [],
        "comment": True,
    }
