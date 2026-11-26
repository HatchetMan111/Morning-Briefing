"""Gemeinsame Helfer für alle Quellen-Module."""
import datetime
import time

import feedparser
import requests
from bs4 import BeautifulSoup

UA = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; morning-briefing/1.0; "
        "personal non-commercial research)"
    )
}


def gn_feed(query: str) -> list[dict]:
    """Google News RSS als Liste {title, url, summary, published}.

    'published' ist UTC oder None. Zwischen Requests 1 s Pause
    (sanft zu den Quellen bleiben).
    """
    url = (
        "https://news.google.com/rss/search?q="
        + requests.utils.quote(query)
        + "&hl=de&gl=DE&ceid=DE:de"
    )
    resp = requests.get(url, headers=UA, timeout=25)
    fp = feedparser.parse(resp.content)
    out = []
    for entry in fp.entries:
        published = None
        if entry.get("published_parsed"):
            published = datetime.datetime(
                *entry["published_parsed"][:6], tzinfo=datetime.timezone.utc
            )
        summary = BeautifulSoup(entry.get("summary", ""), "lxml").get_text(" ", strip=True)
        out.append(
            {
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "summary": summary[:250],
                "published": published,
            }
        )
    time.sleep(1.0)
    return out


def within_days(entry: dict, days: int) -> bool:
    """Einträge ohne Datum zulassen, sonst Zeitfenster prüfen."""
    if entry.get("published") is None:
        return True
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
    return entry["published"] >= cutoff


def item(title: str, url: str, source: str, summary: str = "") -> dict:
    return {
        "id": url or f"{source}:{title}",
        "title": title,
        "url": url,
        "source": source,
        "summary": summary or "",
    }


def dedupe(items: list[dict]) -> list[dict]:
    """Reihenfolge erhalten, Duplikate (id/url/title) entfernen."""
    seen, out = set(), []
    for it in items:
        key = it.get("id") or it.get("url") or it.get("title")
        if key and key not in seen:
            seen.add(key)
            out.append(it)
    return out
