"""Telegram-Zustellung: HTML, auf <=3800 Zeichen pro Nachricht gestückelt."""
import os

import requests


def _chunk(text: str, limit: int = 3800) -> list[str]:
    parts, current = [], ""
    for para in text.split("\n\n"):
        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) <= limit:
            current = candidate
        else:
            if current:
                parts.append(current)
            current = para
    if current:
        parts.append(current)
    return parts or [text]


def send(text: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("[notify] Kein TELEGRAM_BOT_TOKEN/CHAT_ID gesetzt – nur Konsole:")
        print(text)
        return False
    ok = True
    for chunk in _chunk(text):
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": chunk,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=30,
            )
            if resp.status_code != 200:
                print(f"[notify] HTTP {resp.status_code}: {resp.text[:200]}")
                ok = False
        except requests.RequestException as exc:
            print(f"[notify] Fehler: {exc}")
            ok = False
    return ok
