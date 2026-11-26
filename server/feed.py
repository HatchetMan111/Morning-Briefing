"""RSS 2.0 Feed – /feed.xml – Briefing in jedem RSS-Reader abonnierbar."""
import datetime
import html
import pathlib
from xml.etree import ElementTree as ET

from briefing.main import collect_briefings, load_briefing

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _section_to_html(section: dict) -> str:
    """Einzelnen Briefing-Abschnitt als HTML formatieren."""
    parts = [f"<h3>{html.escape(section.get('title', ''))}</h3>"]
    for line in section.get("lines", []):
        parts.append(f"<p>{html.escape(line)}</p>")
    if section.get("commentary"):
        parts.append(f"<p><i>{html.escape(section['commentary'])}</i></p>")
    items = section.get("items", [])
    if items:
        parts.append("<ul>")
        for it in items:
            url = html.escape(it.get("url", ""), quote=True)
            title = html.escape(it.get("title", ""))
            summary = html.escape(it.get("summary", ""))
            line = f"<li><a href='{url}'>{title}</a>"
            if summary:
                line += f" – {summary}"
            line += "</li>"
            parts.append(line)
        parts.append("</ul>")
    return "\n".join(parts)


def generate_feed(base_url: str = "") -> str:
    """RSS 2.0 XML aus den letzten 10 Briefings generieren."""
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "Morning Briefing – Creglingen & Welt"
    ET.SubElement(channel, "link").text = base_url or "http://localhost:8080"
    ET.SubElement(
        channel, "description"
    ).text = "Tägliches Briefing: Lokales, Märkte, KI, Self-Hosting & mehr"
    ET.SubElement(channel, "language").text = "de-DE"

    dates = collect_briefings()[:10]
    for date_str in dates:
        data = load_briefing(date_str)
        if not data:
            continue

        xitem = ET.SubElement(channel, "item")
        ET.SubElement(xitem, "title").text = f"Morning Briefing – {date_str}"
        ET.SubElement(xitem, "link").text = f"{base_url}/api/briefings/{date_str}"

        # Inhalt als HTML
        html_parts = []
        for section in data.get("sections", []):
            html_parts.append(_section_to_html(section))
        description = "\n".join(html_parts)
        ET.SubElement(xitem, "description").text = description

        # Datum
        try:
            dt = datetime.datetime.fromisoformat(data.get("generated_at", ""))
            dt_utc = dt.astimezone(datetime.timezone.utc)
            ET.SubElement(xitem, "pubDate").text = dt_utc.strftime(
                "%a, %d %b %Y %H:%M:%S +0000"
            )
        except (ValueError, TypeError):
            pass

        ET.SubElement(xitem, "guid").text = f"morning-briefing-{date_str}"

    return ET.tostring(rss, encoding="unicode", xml_declaration=False)
