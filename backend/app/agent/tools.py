from __future__ import annotations

from app.llm.protocol import ToolSpec
from app.memory.facts import remember_fact

REMEMBER_TOOL = ToolSpec(
    name="remember_fact",
    description="Save a durable fact about this patient so Joy never re-asks it.",
    parameters={
        "type": "object",
        "properties": {
            "key": {"type": "string"},
            "value": {"type": "string"},
        },
        "required": ["key", "value"],
    },
)

AGENT_TOOLS = [REMEMBER_TOOL]


def apply_remember_fact(patient, key: str, value: str) -> dict:
    return remember_fact(patient, key, value)
