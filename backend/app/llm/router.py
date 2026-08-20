from app.config import get_settings
from app.llm.gemini import GeminiClient
from app.llm.protocol import ChatTurn, LLMClient, LLMError, LLMResult, ToolSpec


def get_llm_client(brain: str | None = None) -> LLMClient:
    name = (brain or get_settings().joy_default_brain).strip().lower()
    if name == "gemini":
        return GeminiClient()
    raise LLMError(f"Unknown JOY_DEFAULT_BRAIN: {name}")


async def polish_reply(text: str, language: str | None) -> str:
    """N-ATLaS / specialist rewrite. Off in this slice."""
    _ = language
    if get_settings().joy_language_polish != "on":
        return text
    return text


async def complete(
    messages: list[ChatTurn],
    *,
    system: str,
    tools: list[ToolSpec] | None = None,
    language: str | None = None,
    brain: str | None = None,
) -> LLMResult:
    client = get_llm_client(brain)
    result = await client.complete(messages, system=system, tools=tools)
    if result.text:
        result.text = await polish_reply(result.text, language)
    return result
