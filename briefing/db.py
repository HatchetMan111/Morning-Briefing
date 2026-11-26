"""SQLite-Datenbank: gesehene Items + Feedback + Alerts + Preis-Watcher."""
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
    conn.execute(
        "CREATE TABLE IF NOT EXISTS alerts "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, "
        " term TEXT NOT NULL, "
        " source_filter TEXT DEFAULT '*', "
        " active INTEGER DEFAULT 1, "
        " created_date TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS alert_seen "
        "(alert_id INTEGER, item_id TEXT, date TEXT, "
        " PRIMARY KEY (alert_id, item_id))"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS price_watch "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, "
        " query TEXT NOT NULL, "
        " threshold REAL DEFAULT 0, "
        " last_price REAL, "
        " last_title TEXT, "
        " last_url TEXT, "
        " last_checked TEXT, "
        " active INTEGER DEFAULT 1, "
        " created_date TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS price_history "
        "(watch_id INTEGER, price REAL, title TEXT, url TEXT, date TEXT, "
        " PRIMARY KEY (watch_id, url, date))"
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


# ==================== KEYWORD-ALERTS ====================

def get_alerts(active_only: bool = True) -> list[dict]:
    conn = connect()
    query = "SELECT id, term, source_filter, active FROM alerts"
    if active_only:
        query += " WHERE active = 1"
    rows = conn.execute(query).fetchall()
    conn.close()
    return [
        {"id": r[0], "term": r[1], "source_filter": r[2], "active": bool(r[3])}
        for r in rows
    ]


def add_alert(term: str, source_filter: str = "*") -> int:
    today = datetime.date.today().isoformat()
    conn = connect()
    cursor = conn.execute(
        "INSERT INTO alerts (term, source_filter, active, created_date) "
        "VALUES (?, ?, 1, ?)",
        (term.strip(), source_filter.strip() or "*", today),
    )
    conn.commit()
    alert_id = cursor.lastrowid
    conn.close()
    return alert_id


def delete_alert(alert_id: int) -> bool:
    conn = connect()
    cursor = conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
    conn.execute("DELETE FROM alert_seen WHERE alert_id = ?", (alert_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def alert_already_fired(alert_id: int, item_id: str) -> bool:
    conn = connect()
    row = conn.execute(
        "SELECT 1 FROM alert_seen WHERE alert_id = ? AND item_id = ?",
        (alert_id, item_id),
    ).fetchone()
    conn.close()
    return row is not None


def mark_alert_fired(alert_id: int, item_id: str):
    today = datetime.date.today().isoformat()
    conn = connect()
    conn.execute(
        "INSERT OR IGNORE INTO alert_seen (alert_id, item_id, date) "
        "VALUES (?, ?, ?)",
        (alert_id, item_id, today),
    )
    conn.commit()
    conn.close()


# ==================== PREIS-WATCHER ====================

def get_price_watches(active_only: bool = True) -> list[dict]:
    conn = connect()
    query = (
        "SELECT id, query, threshold, last_price, last_title, "
        "last_url, last_checked, active FROM price_watch"
    )
    if active_only:
        query += " WHERE active = 1"
    rows = conn.execute(query).fetchall()
    conn.close()
    return [
        {
            "id": r[0], "query": r[1], "threshold": r[2],
            "last_price": r[3], "last_title": r[4], "last_url": r[5],
            "last_checked": r[6], "active": bool(r[7]),
        }
        for r in rows
    ]


def add_price_watch(query: str, threshold: float = 0) -> int:
    today = datetime.date.today().isoformat()
    conn = connect()
    cursor = conn.execute(
        "INSERT INTO price_watch (query, threshold, active, created_date) "
        "VALUES (?, ?, 1, ?)",
        (query.strip(), float(threshold), today),
    )
    conn.commit()
    watch_id = cursor.lastrowid
    conn.close()
    return watch_id


def delete_price_watch(watch_id: int) -> bool:
    conn = connect()
    cursor = conn.execute("DELETE FROM price_watch WHERE id = ?", (watch_id,))
    conn.execute("DELETE FROM price_history WHERE watch_id = ?", (watch_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def update_price_watch(watch_id: int, price: float, title: str, url: str):
    today = datetime.date.today().isoformat()
    conn = connect()
    conn.execute(
        "UPDATE price_watch SET last_price = ?, last_title = ?, "
        "last_url = ?, last_checked = ? WHERE id = ?",
        (price, title[:200], url, today, watch_id),
    )
    conn.execute(
        "INSERT OR IGNORE INTO price_history (watch_id, price, title, url, date) "
        "VALUES (?, ?, ?, ?, ?)",
        (watch_id, price, title[:200], url, today),
    )
    conn.commit()
    conn.close()
