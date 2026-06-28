import base64
import logging

import httpx

from app.config import get_settings
from app.services.gemini import GeminiError

logger = logging.getLogger(__name__)
settings = get_settings()

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


async def transcribe_audio(data: bytes, mime_type: str) -> str:
    if not settings.gemini_api_key:
        raise GeminiError("GEMINI_API_KEY is not configured")

    encoded = base64.b64encode(data).decode("utf-8")
    url = f"{GEMINI_API_BASE}/{settings.gemini_model}:generateContent"

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": encoded,
                        }
                    },
                    {
                        "text": (
                            "Transcribe this audio exactly as spoken. "
                            "The speaker may use English, Pidgin, Yoruba, Igbo, or Hausa. "
                            "Return only the transcribed text with no commentary."
                        )
                    },
                ]
            }
        ],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1024},
    }

    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(
            url,
            params={"key": settings.gemini_api_key},
            json=payload,
        )

    if response.status_code != 200:
        logger.error("Gemini transcription error %s: %s", response.status_code, response.text)
        raise GeminiError(f"Transcription failed: {response.status_code}")

    result = response.json()
    try:
        text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
        if not text:
            raise GeminiError("Empty transcription")
        return text
    except (KeyError, IndexError) as exc:
        raise GeminiError("Failed to parse transcription response") from exc
