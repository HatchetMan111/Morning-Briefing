"""Scheduler: prueft jede Minute, ob die konfigurierte Laufzeit erreicht ist.

Genau EIN Lauf pro Tag (auch ueber Neustarts hinweg): Der Scheduler liest
bei jedem Prueflauf config.yaml neu (Aenderungen ohne Neustart aktiv) und
prueft auf Disk, ob fuer heute bereits ein Briefing existiert.
"""
import datetime
import threading
import time
from zoneinfo import ZoneInfo

from briefing.main import collect_briefings, load_cfg
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


def _loop():
    while True:
        try:
            cfg = load_cfg()
            hh, mm = (int(x) for x in cfg["run"]["time"].split(":"))
            tz = ZoneInfo(cfg["run"]["timezone"])
            now = datetime.datetime.now(tz)
            today = now.date().isoformat()

            scheduled_reached = (now.hour, now.minute) >= (hh, mm)
            latest = collect_briefings()  # neueste zuerst
            already_ran_today = bool(latest) and latest[0] == today

            if (
                scheduled_reached
                and not already_ran_today
                and not runner.status()["running"]
            ):
                print(f"[scheduler] Starte geplanten Lauf (config: {cfg['run']['time']})")
                runner.run_now_async()
        except Exception as exc:  # noqa: BLE001 - Scheduler darf nie sterben
            print(f"[scheduler] Fehler im Prueflauf (ignoriert): {exc}")
        time.sleep(60)
