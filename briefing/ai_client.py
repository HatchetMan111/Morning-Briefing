"""Multi-Provider LLM-Client: Gemini, OpenRouter, Ollama.

Provider wird per env LLM_PROVIDER gesetzt (gemini|openrouter|ollama).
Ohne API-Key: alle Funktionen liefern leer zurueck.
"""
import json
import os
import time

import requests

RATE_LIMIT_SECONDS = 3.0
_last_call = 0.0


def _throttle():
    global _last_call
    elapsed = time.time() - _last_call
    if elapsed < RATE_LIMIT_SECONDS:
        time.sleep(RATE_LIMIT_SECONDS - elapsed)
    _last_call = time.time()


# ==================== PROVIDER: GEMINI ====================

def _gemini_available() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY", "").strip())


def _gemini_generate(prompt: str, max_tokens: int) -> str:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": max_tokens},
    }
    resp = requests.post(url, json=payload, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini HTTP {resp.status_code}: {resp.text[:200]}")
    return (
        resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    )


# ==================== PROVIDER: OPENROUTER ====================

def _openrouter_available() -> bool:
    return bool(os.environ.get("OPENROUTER_API_KEY", "").strip())


def _openrouter_generate(prompt: str, max_tokens: int) -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    model = os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free")
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        },
        timeout=60,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"OpenRouter HTTP {resp.status_code}: {resp.text[:200]}")
    return resp.json()["choices"][0]["message"]["content"].strip()


# ==================== PROVIDER: OLLAMA ====================

def _ollama_available() -> bool:
    base_url = os.environ.get("OLLAMA_BASE_URL", "").strip()
    return bool(base_url)


def _ollama_generate(prompt: str, max_tokens: int) -> str:
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").strip()
    model = os.environ.get("OLLAMA_MODEL", "llama3.2")
    resp = requests.post(
        f"{base_url}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=120,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Ollama HTTP {resp.status_code}: {resp.text[:200]}")
    return resp.json().get("response", "").strip()


# ==================== PUBLIC API ====================

def get_provider() -> str:
    """Aktuell aktiver LLM-Provider."""
    provider = os.environ.get("LLM_PROVIDER", "gemini").strip().lower()
    if provider in ("openrouter",) and _openrouter_available():
        return "openrouter"
    if provider in ("ollama",) and _ollama_available():
        return "ollama"
    if _gemini_available():
        return "gemini"
    return provider


def available() -> bool:
    provider = get_provider()
    return (
        (provider == "gemini" and _gemini_available())
        or (provider == "openrouter" and _openrouter_available())
        or (provider == "ollama" and _ollama_available())
    )


def provider_info() -> dict:
    return {
        "provider": get_provider(),
        "gemini": _gemini_available(),
        "openrouter": _openrouter_available(),
        "ollama": _ollama_available(),
        "openrouter_model": os.environ.get("OPENROUTER_MODEL", ""),
        "ollama_model": os.environ.get("OLLAMA_MODEL", ""),
    }


def generate_text(prompt: str, max_tokens: int = 2048) -> str:
    """Freitext-Antwort ueber den aktiven Provider."""
    if not available():
        return ""
    _throttle()
    provider = get_provider()
    try:
        if provider == "openrouter":
            return _openrouter_generate(prompt, max_tokens)
        if provider == "ollama":
            return _ollama_generate(prompt, max_tokens)
        return _gemini_generate(prompt, max_tokens)
    except Exception as exc:  # noqa: BLE001
        print(f"[ai:{provider}] Fehler: {exc}")
        # Fallback auf Gemini wenn verfuegbar
        if provider != "gemini" and _gemini_available():
            try:
                print(f"[ai] Fallback auf Gemini")
                return _gemini_generate(prompt, max_tokens)
            except Exception:
                pass
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
