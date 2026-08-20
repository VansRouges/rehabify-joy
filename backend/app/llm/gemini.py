from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from app.config import get_settings
from app.llm.protocol import ChatTurn, LLMError, LLMResult, ToolCall, ToolSpec

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# Backward-compatible alias used by transcription and WhatsApp.
GeminiError = LLMError

_JSON_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _tool_instruction(tools: list[ToolSpec]) -> str:
    names = ", ".join(t.name for t in tools)
    return (
        "You have tools. Respond with a single JSON object and no markdown.\n"
        'To save a durable fact: {"action":"remember_fact","key":"<key>","value":"<value>"}\n'
        'To speak to the patient: {"action":"reply","text":"<message>"}\n'
        f"Available tools: {names}. After a fact is saved you will be asked to reply."
    )


def _parse_protocol(raw: str) -> LLMResult:
    text = raw.strip()
    fenced = _JSON_FENCE.search(text)
    if fenced:
        text = fenced.group(1)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return LLMResult(text=raw.strip())
    if not isinstance(data, dict):
        return LLMResult(text=raw.strip())
    action = data.get("action")
    if action == "remember_fact":
        key = str(data.get("key") or "").strip()
        value = str(data.get("value") or "").strip()
        if key and value:
            return LLMResult(
                text="",
                tool_calls=[ToolCall(name="remember_fact", arguments={"key": key, "value": value})],
            )
    if action == "reply":
        return LLMResult(text=str(data.get("text") or "").strip())
    return LLMResult(text=raw.strip())


def _build_contents(messages: list[ChatTurn]) -> list[dict[str, Any]]:
    contents: list[dict[str, Any]] = []
    for turn in messages:
        role = "user" if turn.role == "user" else "model"
        contents.append({"role": role, "parts": [{"text": turn.content}]})
    return contents


class GeminiClient:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.gemini_api_key
        self.model = model or settings.gemini_model

    async def complete(
        self,
        messages: list[ChatTurn],
        *,
        system: str,
        tools: list[ToolSpec] | None = None,
    ) -> LLMResult:
        if not self.api_key:
            raise LLMError("GEMINI_API_KEY is not configured")
        if not messages:
            raise LLMError("complete() requires at least one message")

        system_prompt = system
        if tools:
            system_prompt = f"{system}\n\n{_tool_instruction(tools)}"

        url = f"{GEMINI_API_BASE}/{self.model}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": _build_contents(messages),
            "generationConfig": {
                "temperature": 0.7,
                "topP": 0.9,
                "maxOutputTokens": 1024,
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                params={"key": self.api_key},
                json=payload,
            )

        if response.status_code != 200:
            logger.error("Gemini API error %s: %s", response.status_code, response.text)
            raise LLMError(f"Gemini API returned {response.status_code}")

        data = response.json()
        try:
            raw = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError) as exc:
            logger.error("Unexpected Gemini response shape: %s", data)
            raise LLMError("Failed to parse Gemini response") from exc

        if tools:
            return _parse_protocol(raw)
        return LLMResult(text=raw)


async def generate_reply(
    history: list[dict[str, str]],
    user_message: str,
    *,
    system_prompt: str | None = None,
) -> str:
    """Legacy helper — prefer GeminiClient.complete via the router."""
    from app.services.session import load_system_prompt, trim_history
    from app.config import get_settings

    settings = get_settings()
    prompt = system_prompt or load_system_prompt()
    trimmed = trim_history(history, settings.max_history_turns)
    messages = [ChatTurn(role=t["role"], content=t["content"]) for t in trimmed]
    messages.append(ChatTurn(role="user", content=user_message))
    result = await GeminiClient().complete(messages, system=prompt)
    return result.text
