"""Self-Hosting: neue awesome-selfhosted-Eintraege, Show HN, r/selfhosted."""
import re
import time

import feedparser
import requests

from briefing import db
from briefing.sources._util import UA, dedupe, item

AWESOME_RAW = (
    "https://raw.githubusercontent.com/awesome-selfhosted/awesome-selfhosted/"
    "master/README.md"
)
HN_API = "https://hn.algolia.com/api/v1/search_by_date"
REDDIT_RSS = "https://www.reddit.com/r/selfhosted/top/.rss?t=day"


def _new_awesome_apps() -> list[dict]:
    """README speichern und gegen den letzten Stand diffen -> neue Apps."""
    resp = requests.get(AWESOME_RAW, headers=UA, timeout=30)
    resp.raise_for_status()
    current = resp.text
    prev_path = db.DATA / "awesome_selfhosted_prev.md"
    new_lines: list[str] = []
    if prev_path.exists():
        previous = set(prev_path.read_text(encoding="utf-8").splitlines())
        new_lines = [
            ln for ln in current.splitlines()
            if ln.startswith("- [") and ln not in previous
        ]
    prev_path.parent.mkdir(parents=True, exist_ok=True)
    prev_path.write_text(current, encoding="utf-8")

    items = []
    for line in new_lines:
        match = re.match(r"- \[([^\]]+)\]\(([^)]+)\)(?:\s*[-–]\s*(.*))?", line)
        if not match:
            continue
        items.append(
            item(
                title=f"Neu in awesome-selfhosted: {match.group(1)}",
                url=match.group(2),
                source="awesome-selfhosted",
                summary=(match.group(3) or "")[:250],
            )
        )
    return items[:15]


def _show_hn() -> list[dict]:
    """Show HN: Suchen je Keyword (Algolia versteht keine OR-Queries)."""
    keywords = ("docker", "homelab", "self-hosted", "selfhosted", "server")
    hits: dict[str, dict] = {}
    for keyword in keywords:
        try:
            resp = requests.get(
                HN_API,
                params={
                    "tags": "show_hn",
                    "query": keyword,
                    "numericFilters": "points>10",
                },
                headers=UA,
                timeout=25,
            )
            resp.raise_for_status()
            for hit in resp.json().get("hits", [])[:8]:
                object_id = hit.get("objectID")
                if object_id and object_id not in hits:
                    hits[object_id] = hit
        except Exception as exc:  # noqa: BLE001
            print(f"[selfhosted] show-hn '{keyword}': {exc}")
        time.sleep(1)
    out = []
    for hit in hits.values():
        url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        out.append(item(title=hit.get("title", ""), url=url,
                        source="show-hn", summary=f"{hit.get('points', 0)} Punkte"))
    return out


def _reddit() -> list[dict]:
    resp = requests.get(REDDIT_RSS, headers=UA, timeout=25)
    resp.raise_for_status()
    fp = feedparser.parse(resp.content)
    out = []
    for entry in fp.entries[:10]:
        out.append(item(title=entry.get("title", ""), url=entry.get("link", ""),
                         source="r/selfhosted"))
    return out


def fetch(cfg: dict) -> dict:
    sh_cfg = cfg.get("selfhosted", {})
    items: list[dict] = []
    if sh_cfg.get("awesome_diff", True):
        try:
            items += _new_awesome_apps()
        except Exception as exc:  # noqa: BLE001
            print(f"[selfhosted] awesome-diff: {exc}")
    if sh_cfg.get("show_hn", True):
        try:
            items += _show_hn()
        except Exception as exc:  # noqa: BLE001
            print(f"[selfhosted] show-hn: {exc}")
        time.sleep(1)
    if sh_cfg.get("reddit", True):
        try:
            items += _reddit()
        except Exception as exc:  # noqa: BLE001
            print(f"[selfhosted] reddit: {exc}")
    return {
        "key": "selfhosted",
        "title": "🖥️ Self-Hosting (Proxmox & Co.)",
        "lines": [],
        "items": dedupe(items),
        "items_label": "Interessant für dein Homelab:",
        "comment": False,
    }
