import json
from pathlib import Path
from typing import Any

import redis.asyncio as redis

from app.config import get_settings

settings = get_settings()

_redis: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


def _session_key(session_id: str) -> str:
    return f"joy:session:{session_id}"


async def get_session_state(session_id: str) -> dict[str, Any] | None:
    client = await get_redis()
    raw = await client.get(_session_key(session_id))
    if not raw:
        return None
    return json.loads(raw)


async def save_session_state(session_id: str, state: dict[str, Any]) -> None:
    client = await get_redis()
    await client.set(
        _session_key(session_id),
        json.dumps(state),
        ex=settings.session_ttl_seconds,
    )


async def delete_session_state(session_id: str) -> None:
    client = await get_redis()
    await client.delete(_session_key(session_id))


def default_session_state() -> dict[str, Any]:
    return {
        "mode": "triage",
        "history": [],
        "triage_complete": False,
    }


def trim_history(history: list[dict[str, str]], max_turns: int) -> list[dict[str, str]]:
    """Keep the last N message pairs (user + assistant)."""
    max_messages = max_turns * 2
    if len(history) <= max_messages:
        return history
    return history[-max_messages:]


def load_system_prompt() -> str:
    prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "joy_system_prompt.txt"
    return prompt_path.read_text(encoding="utf-8")
