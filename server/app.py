"""FastAPI: Web-UI (statisch) + REST-API fuer Briefings, Laeufe, Konfig."""
import pathlib

import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from briefing import db
from briefing.main import (
    collect_briefings,
    load_briefing,
    load_cfg,
)
from server import runner, scheduler

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIST = ROOT / "frontend" / "dist"

app = FastAPI(title="Morning Briefing", version="1.0.0")


class Feedback(BaseModel):
    kind: str  # "positive" | "negative"
    text: str


class ConfigUpdate(BaseModel):
    yaml: str


class EnvUpdate(BaseModel):
    env: str


class AlertCreate(BaseModel):
    term: str
    source_filter: str = "*"


class PriceWatchCreate(BaseModel):
    query: str
    threshold: float = 0


# ---------------- Scheduler ----------------
@app.on_event("startup")
def _on_startup():
    scheduler.start()


# ---------------- Briefings ----------------
@app.get("/api/briefings")
def api_briefings():
    return {"briefings": collect_briefings()}


@app.get("/api/briefing/latest")
def api_latest():
    dates = collect_briefings()
    if not dates:
        raise HTTPException(404, "Noch kein Briefing vorhanden – starte einen Lauf.")
    return load_briefing(dates[0])


@app.get("/api/briefings/{date}")
def api_briefing(date: str):
    data = load_briefing(date)
    if data is None:
        raise HTTPException(404, f"Kein Briefing für {date}.")
    return data


# ---------------- Lauf steuern ----------------
@app.post("/api/run")
def api_run():
    started = runner.run_now_async()
    if not started:
        raise HTTPException(409, "Es läuft bereits ein Briefing-Lauf.")
    return {"started": True}


@app.get("/api/run")
def api_run_status():
    return runner.status()


# ---------------- Status ----------------
@app.get("/api/status")
def api_status():
    cfg = load_cfg()
    import os

    latest = collect_briefings()
    latest_data = load_briefing(latest[0]) if latest else {}
    return {
        "app": "Morning Briefing",
        "version": app.version,
        "run_time": cfg["run"]["time"],
        "region": cfg["region"]["center_city"],
        "modules": {
            k: v.get("enabled", False) for k, v in cfg.get("modules", {}).items()
        },
        "telegram_configured": bool(os.environ.get("TELEGRAM_BOT_TOKEN")),
        "gemini_configured": bool(os.environ.get("GEMINI_API_KEY")),
        "latest_briefing": latest[0] if latest else None,
        "latest_sources": latest_data.get("sources", {}),
        "runner": runner.status(),
    }


# ---------------- Feedback ----------------
@app.get("/api/feedback")
def api_feedback():
    return db.load_feedback()


@app.post("/api/feedback")
def api_feedback_add(fb: Feedback):
    if fb.kind not in ("positive", "negative"):
        raise HTTPException(400, "kind muss 'positive' oder 'negative' sein.")
    if not fb.text.strip():
        raise HTTPException(400, "text darf nicht leer sein.")
    db.add_feedback(fb.kind, fb.text.strip())
    return db.load_feedback()


# ---------------- Keyword-Alerts ----------------
@app.get("/api/alerts")
def api_alerts():
    return {"alerts": db.get_alerts(active_only=False)}


@app.post("/api/alerts")
def api_alert_add(a: AlertCreate):
    if not a.term.strip():
        raise HTTPException(400, "term darf nicht leer sein.")
    db.add_alert(a.term, a.source_filter)
    return {"alerts": db.get_alerts(active_only=False)}


@app.delete("/api/alerts/{alert_id}")
def api_alert_delete(alert_id: int):
    if not db.delete_alert(alert_id):
        raise HTTPException(404, f"Alert {alert_id} nicht gefunden.")
    return {"alerts": db.get_alerts(active_only=False)}


# ---------------- Preis-Tracker ----------------
@app.get("/api/price-watch")
def api_price_watch():
    return {"watches": db.get_price_watches(active_only=False)}


@app.post("/api/price-watch")
def api_price_watch_add(pw: PriceWatchCreate):
    if not pw.query.strip():
        raise HTTPException(400, "query darf nicht leer sein.")
    db.add_price_watch(pw.query, pw.threshold)
    return {"watches": db.get_price_watches(active_only=False)}


@app.delete("/api/price-watch/{watch_id}")
def api_price_watch_delete(watch_id: int):
    if not db.delete_price_watch(watch_id):
        raise HTTPException(404, f"Watch {watch_id} nicht gefunden.")
    return {"watches": db.get_price_watches(active_only=False)}


# ---------------- RSS-Feed ----------------
@app.get("/feed.xml")
def rss_feed(request: Request):
    from fastapi.responses import Response

    from server.feed import generate_feed

    base_url = str(request.base_url).rstrip("/")
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + generate_feed(base_url)
    return Response(content=xml, media_type="application/rss+xml")


# ---------------- Konfiguration (config.yaml) ----------------
@app.get("/api/config")
def api_config():
    return {"yaml": (ROOT / "config.yaml").read_text(encoding="utf-8")}


@app.put("/api/config")
def api_config_update(update: ConfigUpdate):
    try:
        parsed = yaml.safe_load(update.yaml)
        if not isinstance(parsed, dict) or "run" not in parsed or "region" not in parsed:
            raise ValueError("Pflicht-Sektionen fehlen: run, region")
    except yaml.YAMLError as exc:
        raise HTTPException(400, f"Ungültiges YAML: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    backup = ROOT / "config.yaml.bak"
    source = ROOT / "config.yaml"
    if source.exists():
        backup.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    source.write_text(update.yaml, encoding="utf-8")
    return {"ok": True, "backup": str(backup)}


# ---------------- .env (Token) ----------------
ALLOWED_ENV_KEYS = {"TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "GEMINI_API_KEY", "EBAY_BEARER_TOKEN"}


@app.get("/api/env")
def api_env():
    path = ROOT / ".env"
    if not path.exists():
        return {"env": ""}
    raw = path.read_text(encoding="utf-8")
    # Werte maskieren: nur anzeigen, ob gesetzt
    masked = []
    for line in raw.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            masked.append(f"{key}={'***' if value.strip() else ''}")
        else:
            masked.append(line)
    return {"env": "\n".join(masked)}


@app.put("/api/env")
def api_env_update(update: EnvUpdate):
    keep_values = {}
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                keep_values[key.strip()] = value
    new_lines = []
    for line in update.env.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise HTTPException(400, f"Ungültige Zeile (kein KEY=WERT): {stripped}")
        key, value = stripped.split("=", 1)
        if key not in ALLOWED_ENV_KEYS:
            raise HTTPException(400, f"Unbekannter Schlüssel: {key}")
        if value.strip() and value.strip() != "***":
            keep_values[key] = value
    content = "\n".join(f"{k}={v}" for k, v in keep_values.items()) + "\n"
    backup = ROOT / ".env.bak"
    if path.exists():
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    path.write_text(content, encoding="utf-8")
    return {"ok": True, "hint": "Neustart erforderlich: systemctl restart morning-briefing"}


# ---------------- Web-UI (zuletzt gemountet, API gewinnt) ----------------
if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="ui")
else:
    @app.get("/")
    def _fallback_root():
        return {"error": "frontend/dist fehlt – Web-UI nicht gebaut."}
