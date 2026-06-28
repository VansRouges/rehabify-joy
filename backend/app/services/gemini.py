import logging
from typing import Any

import httpx

from app.config import get_settings
from app.services.session import load_system_prompt, trim_history

logger = logging.getLogger(__name__)
settings = get_settings()

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiError(Exception):
    pass


def _build_contents(history: list[dict[str, str]], user_message: str) -> list[dict[str, Any]]:
    contents: list[dict[str, Any]] = []

    for turn in history:
        role = "user" if turn["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": turn["content"]}]})

    contents.append({"role": "user", "parts": [{"text": user_message}]})
    return contents


async def generate_reply(
    history: list[dict[str, str]],
    user_message: str,
    *,
    system_prompt: str | None = None,
) -> str:
    if not settings.gemini_api_key:
        raise GeminiError("GEMINI_API_KEY is not configured")

    prompt = system_prompt or load_system_prompt()
    trimmed = trim_history(history, settings.max_history_turns)
    contents = _build_contents(trimmed, user_message)

    url = f"{GEMINI_API_BASE}/{settings.gemini_model}:generateContent"
    payload = {
        "systemInstruction": {"parts": [{"text": prompt}]},
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "topP": 0.9,
            "maxOutputTokens": 1024,
        },
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            url,
            params={"key": settings.gemini_api_key},
            json=payload,
        )

    if response.status_code != 200:
        logger.error("Gemini API error %s: %s", response.status_code, response.text)
        raise GeminiError(f"Gemini API returned {response.status_code}")

    data = response.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError) as exc:
        logger.error("Unexpected Gemini response shape: %s", data)
        raise GeminiError("Failed to parse Gemini response") from exc
