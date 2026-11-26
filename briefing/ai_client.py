"""Gemini-Flash-Client mit Modell-Fallback und Rate-Limit (Free-Tier schonen).

Kein API-Key gesetzt -> alle Funktionen liefern leer zurück,
das Briefing läuft dann ohne KI-Anreicherung weiter.
"""
import json
import os
import time

import requests

MODEL_FALLBACK = [
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-2.0-flash-lite",
    "gemini-flash-lite-latest",
]
RATE_LIMIT_SECONDS = 5.0
_last_call = 0.0


def api_key() -> str:
    return os.environ.get("GEMINI_API_KEY", "").strip()


def available() -> bool:
    return bool(api_key())


def _throttle():
    global _last_call
    elapsed = time.time() - _last_call
    if elapsed < RATE_LIMIT_SECONDS:
        time.sleep(RATE_LIMIT_SECONDS - elapsed)
    _last_call = time.time()


def _post(model: str, payload: dict) -> str:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key()}"
    )
    resp = requests.post(url, json=payload, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"{model} -> HTTP {resp.status_code}")
    return (
        resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    )


def generate_text(prompt: str, max_tokens: int = 2048) -> str:
    """Freitext-Antwort mit Fallback über mehrere Modelle."""
    if not available():
        return ""
    _throttle()
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": max_tokens},
    }
    for model in MODEL_FALLBACK:
        try:
            return _post(model, payload)
        except Exception as exc:  # noqa: BLE001 - Fallback beabsichtigt
            print(f"[ai] {exc}")
            continue
    return ""


def generate_json(prompt: str, max_tokens: int = 3072) -> dict:
    """JSON-Antwort; robust gegen Markdown-Codefences."""
    text = generate_text(
        prompt + "\n\nAntworte NUR mit gueltigem JSON, ohne Markdown-Codefences.",
        max_tokens=max_tokens,
    )
    if not text:
        return {}
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}
