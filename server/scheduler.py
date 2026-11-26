"""Scheduler: prueft jede Minute, ob eine konfigurierte Laufzeit erreicht ist.

Unterstützt MEHRERE Laufzeiten pro Tag (z.B. 09:00 + 18:00).
Prüft den Zeitstempel des letzten Briefings: Ist eine konfigurierte
Zeit erreicht, ohne dass danach ein Briefing erzeugt wurde -> Lauf.
"""
import datetime
import threading
import time
from zoneinfo import ZoneInfo

from briefing.main import collect_briefings, load_briefing, load_cfg
from server import runner

_started = False
_thread = None


def start():
    global _started, _thread
    if _started:
        return
    _started = True
    _thread = threading.Thread(target=_loop, daemon=True, name="scheduler")
    _thread.start()
    print("[scheduler] gestartet")


def _get_times(cfg: dict) -> list[tuple[int, int]]:
    """Laufzeiten aus config.yaml lesen (unterstützt 'times' und 'time')."""
    run_cfg = cfg.get("run", {})
    times = []
    if "times" in run_cfg:
        for t in run_cfg["times"]:
            hh, mm = (int(x) for x in t.split(":"))
            times.append((hh, mm))
    elif "time" in run_cfg:
        hh, mm = (int(x) for x in run_cfg["time"].split(":"))
        times.append((hh, mm))
    return times or [(9, 0)]


def _latest_generated_at() -> datetime.datetime | None:
    """Zeitstempel des letzten Briefings (naive Ortszeit) oder None."""
    dates = collect_briefings()
    if not dates:
        return None
    data = load_briefing(dates[0])
    if not data:
        return None
    try:
        dt = datetime.datetime.fromisoformat(data.get("generated_at", ""))
        # Naive Ortszeit sicherstellen (Timezone-Info entfernen falls vorhanden)
        return dt.replace(tzinfo=None)
    except (ValueError, TypeError):
        return None


def _loop():
    while True:
        try:
            cfg = load_cfg()
            times = _get_times(cfg)
            tz = ZoneInfo(cfg["run"].get("timezone", "Europe/Berlin"))
            # Naive Ortszeit für Vergleiche (generated_at ist auch Ortszeit)
            now = datetime.datetime.now(tz).replace(tzinfo=None)

            latest = _latest_generated_at()

            for hh, mm in times:
                scheduled = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
                if now >= scheduled and (latest is None or latest < scheduled):
                    if not runner.status()["running"]:
                        print(f"[scheduler] Starte Lauf ({hh:02d}:{mm:02d})")
                        runner.run_now_async()
                    break
        except Exception as exc:  # noqa: BLE001 - Scheduler darf nie sterben
            print(f"[scheduler] Fehler (ignoriert): {exc}")
        time.sleep(60)
