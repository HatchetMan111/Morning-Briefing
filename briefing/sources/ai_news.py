"""KI-News: Hacker News (Algolia-API) + neueste KI-Papers von arXiv."""
import time

import feedparser
import requests

from briefing.sources._util import UA, dedupe, item

HN_API = "https://hn.algolia.com/api/v1/search_by_date"
ARXIV_API = "http://export.arxiv.org/api/query"


def _hn(query: str, min_points: int) -> list[dict]:
    resp = requests.get(
        HN_API,
        params={"tags": "story", "query": query,
                "numericFilters": f"points>{min_points}"},
        headers=UA,
        timeout=25,
    )
    resp.raise_for_status()
    out = []
    for hit in resp.json().get("hits", []):
        url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        meta = f"{hit.get('points', 0)} Punkte · {hit.get('num_comments', 0)} Kommentare"
        out.append(item(title=hit.get("title", ""), url=url,
                        source="hackernews", summary=meta))
    return out


def _arxiv(max_results: int) -> list[dict]:
    resp = requests.get(
        ARXIV_API,
        params={
            "search_query": "cat:cs.AI OR cat:cs.CL OR cat:cs.LG",
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": str(max_results),
        },
        headers=UA,
        timeout=30,
    )
    resp.raise_for_status()
    fp = feedparser.parse(resp.content)
    out = []
    for entry in fp.entries:
        out.append(
            item(
                title=f"Paper: {entry.get('title', '').strip()}",
                url=entry.get("link", ""),
                source="arxiv",
                summary=entry.get("summary", "").strip()[:250],
            )
        )
    return out


def fetch(cfg: dict) -> dict:
    ai_cfg = cfg.get("ai_news", {})
    items = []
    for query in ("AI", "LLM"):
        try:
            items += _hn(query, ai_cfg.get("min_points_hn", 40))
        except Exception as exc:  # noqa: BLE001
            print(f"[ai_news] HN {query}: {exc}")
        time.sleep(1)
    try:
        items += _arxiv(ai_cfg.get("max_arxiv", 8))
    except Exception as exc:  # noqa: BLE001
        print(f"[ai_news] arXiv: {exc}")
    return {
        "key": "ai_news",
        "title": "🤖 KI-News",
        "lines": [],
        "items": dedupe(items),
        "items_label": "Top für dich:",
        "comment": False,
    }
