"""Zusammensetzung des Briefings (Telegram-HTML) + HTML-Archiv."""
import datetime
import html
import pathlib

from briefing.db import ARCHIVE

WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag",
            "Freitag", "Samstag", "Sonntag"]


def today_header() -> str:
    now = datetime.date.today()
    return f"{WEEKDAYS[now.weekday()]}, {now.strftime('%d.%m.%Y')}"


def _item_line(item: dict) -> str:
    title = html.escape(item.get("title", "")[:220])
    url = html.escape(item.get("url", ""), quote=True)
    summary = html.escape(
        item.get("ai_summary") or item.get("summary", "") or ""
    )[:220]
    line = f"• <a href='{url}'>{title}</a>" if url else f"• {title}"
    if summary:
        line += f" — <i>{summary}</i>"
    return line


def section_body(section: dict, scored_items: list[dict], commentary: str) -> str:
    body = []
    for line in section.get("lines", []):
        body.append(html.escape(line))
    if commentary:
        if body:
            body.append("")
        body.append(f"<i>{html.escape(commentary)}</i>")
    if scored_items:
        label = section.get("items_label")
        if label:
            if body:
                body.append("")
            body.append(f"<b>{html.escape(label)}</b>")
        body.extend(_item_line(it) for it in scored_items)
    return "\n".join(body)


def briefing_html(sections: list[tuple[str, str]]) -> str:
    parts = [
        "🌅 <b>Morning Briefing</b>",
        f"<i>{today_header()} · Creglingen &amp; 50 km · Welt · Tech · KI</i>",
    ]
    for title, body in sections:
        if not body:
            continue
        parts.append(f"\n<b>{html.escape(title)}</b>\n{body}")
    return "\n\n".join(parts)


def archive(full_html: str) -> pathlib.Path:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    date_str = datetime.date.today().isoformat()
    page = f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Morning Briefing {date_str}</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:760px;margin:2rem auto;padding:0 1rem;line-height:1.5}}
a{{color:#0b6bcb}}
</style></head><body>
{full_html}
</body></html>"""
    path = ARCHIVE / f"{date_str}.html"
    path.write_text(page, encoding="utf-8")
    return path
