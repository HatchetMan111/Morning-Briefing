"""SQLite-Datenbank: gesehene Items (Deduplizierung) + Nutzer-Feedback."""
import datetime
import pathlib
import sqlite3

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ARCHIVE = DATA / "archive"


def connect() -> sqlite3.Connection:
    DATA.mkdir(exist_ok=True)
    conn = sqlite3.connect(DATA / "briefing.db")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS seen "
        "(id TEXT PRIMARY KEY, section TEXT, date TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS feedback "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, text TEXT, date TEXT)"
    )
    return conn


def filter_new(items: list[dict], section: str) -> list[dict]:
    """Nur Items zurückgeben, die noch nie im Briefing waren."""
    conn = connect()
    seen = {row[0] for row in conn.execute(
        "SELECT id FROM seen WHERE section = ?", (section,)
    )}
    conn.close()
    return [it for it in items if it.get("id") not in seen]


def mark_seen(items: list[dict], section: str):
    today = datetime.date.today().isoformat()
    conn = connect()
    conn.executemany(
        "INSERT OR IGNORE INTO seen (id, section, date) VALUES (?, ?, ?)",
        [(it["id"], section, today) for it in items],
    )
    conn.commit()
    conn.close()


def add_feedback(kind: str, text: str):
    today = datetime.date.today().isoformat()
    conn = connect()
    conn.execute(
        "INSERT INTO feedback (kind, text, date) VALUES (?, ?, ?)",
        (kind, text, today),
    )
    conn.commit()
    conn.close()


def load_feedback() -> dict:
    conn = connect()
    rows = conn.execute(
        "SELECT kind, text FROM feedback ORDER BY id ASC"
    ).fetchall()
    conn.close()
    fb = {"positive": [], "negative": []}
    for kind, text in rows:
        if kind in fb:
            fb[kind].append(text)
    return fb
