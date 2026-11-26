"""Spritpreise: Günstigste Tankstellen im Umkreis (Tankerkönig API).

API: https://creativecommons.tankerkoenig.de (kostenlos, nur API-Key nötig)
Key beantragen: https://creativecommons.tankerkoenig.de/
Key in .env als TANKERKOENIG_API_KEY hinterlegen.
"""
import os

import requests

from briefing.sources._util import UA

API_URL = "https://creativecommons.tankerkoenig.de/json/list.php"

FUEL_LABELS = {
    "e5": "🟢 E5",
    "e10": "🔵 E10",
    "diesel": "⚫ Diesel",
}


def _find_cheapest(stations: list[dict], fuel_key: str) -> dict | None:
    """Günstigste offene Station für einen Sprittyp finden."""
    cheapest = None
    for s in stations:
        price = s.get(fuel_key)
        if price is None or price <= 0 or not s.get("isOpen", False):
            continue
        if cheapest is None or price < cheapest[fuel_key]:
            cheapest = s
    return cheapest


def fetch(cfg: dict) -> dict:
    fp_cfg = cfg.get("fuel_prices", {})
    api_key = os.environ.get("TANKERKOENIG_API_KEY", "").strip()

    if not api_key:
        return {
            "key": "fuel_prices",
            "title": "⛽ Spritpreise",
            "lines": [
                "Kein TANKERKOENIG_API_KEY gesetzt.",
                "Kostenlosen Key beantragen: https://creativecommons.tankerkoenig.de/",
                "Dann in den Einstellungen (.env) eintragen.",
            ],
            "items": [],
            "comment": False,
        }

    lat = fp_cfg.get("lat", 49.4667)   # Creglingen
    lng = fp_cfg.get("lng", 9.8833)
    radius = fp_cfg.get("radius_km", 15)

    try:
        resp = requests.get(
            API_URL,
            params={
                "lat": lat,
                "lng": lng,
                "rad": radius,
                "type": "all",
                "sort": "dist",
                "apikey": api_key,
            },
            headers=UA,
            timeout=25,
        )
        resp.raise_for_status()
        stations = resp.json().get("stations", [])
    except Exception as exc:  # noqa: BLE001
        return {
            "key": "fuel_prices",
            "title": "⛽ Spritpreise",
            "lines": [f"Tankerkönig-API Fehler: {exc}"],
            "items": [],
            "comment": False,
        }

    lines = []
    items = []

    for fuel_key, label in FUEL_LABELS.items():
        cheapest = _find_cheapest(stations, fuel_key)
        if cheapest:
            name = cheapest.get("name", "?")
            brand = cheapest.get("brand", "") or name
            place = cheapest.get("place", "?")
            dist = cheapest.get("dist", 0)
            price = cheapest.get(fuel_key, 0)
            street = cheapest.get("street", "")
            line = (
                f"{label}: {price:.3f} € bei {brand} ({place}, "
                f"{dist:.1f} km)"
            )
            lines.append(line)
            items.append(
                {
                    "title": f"{label} {price:.3f} € – {brand}",
                    "url": "",
                    "source": "tankerkoenig",
                    "summary": f"📍 {street}, {place} · {dist:.1f} km · offen",
                    "score": 90,
                }
            )

    return {
        "key": "fuel_prices",
        "title": f"⛽ Spritpreise (günstigste im {radius}-km-Umkreis)",
        "lines": lines,
        "items": items,
        "items_label": "Details:",
        "comment": False,
    }
