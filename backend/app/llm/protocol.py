from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class LLMError(Exception):
    pass


@dataclass
class ChatTurn:
    role: str  # "user" | "assistant"
    content: str


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResult:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMClient(Protocol):
    async def complete(
        self,
        messages: list[ChatTurn],
        *,
        system: str,
        tools: list[ToolSpec] | None = None,
    ) -> LLMResult: ...
