"""Fuehrt Briefing-Laeufe in einem Hintergrund-Thread aus.

Faelle vollstaendig (Stacktrace, stdout/stderr) in state['log'] –
Anforderung: nie nur die letzte Fehlerzeile, immer die ganze Kette.
"""
import contextlib
import io
import threading
import traceback

from briefing.main import run as run_briefing

_lock = threading.Lock()
state = {
    "running": False,
    "started_at": None,
    "finished_at": None,
    "error": None,
    "log": "",
    "last_date": None,
    "runs_total": 0,
}


def run_now_async() -> bool:
    """Lauf im Hintergrund starten. False, wenn schon einer laeuft."""
    with _lock:
        if state["running"]:
            return False
        state["running"] = True
        state["started_at"] = _now()
        state["error"] = None
    thread = threading.Thread(target=_execute, daemon=True)
    thread.start()
    return True


def _now() -> str:
    import datetime

    return datetime.datetime.now().isoformat(timespec="seconds")


def _execute():
    """Lauf mit kompletter Ausgabe-Aufzeichnung ausfuehren."""
    import datetime

    buffer = io.StringIO()
    error = None
    data = {}
    try:
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            data = run_briefing() or {}
    except Exception as exc:  # noqa: BLE001 - komplette Kette aufschnappen
        error = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        buffer.write(error)
    with _lock:
        state["running"] = False
        state["finished_at"] = _now()
        state["error"] = error
        state["log"] = buffer.getvalue()[-8000:]
        state["last_date"] = data.get("date") or datetime.date.today().isoformat()
        state["runs_total"] += 1
    if error:
        print(f"[runner] Lauf fehlgeschlagen:\n{error}")


def status() -> dict:
    with _lock:
        return dict(state)
