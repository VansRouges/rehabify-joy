from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools import AGENT_TOOLS, apply_remember_fact
from app.db.models import Patient
from app.llm.protocol import ChatTurn, LLMResult
from app.llm.router import complete
from app.memory.audit import write_audit
from app.memory.compiler import CompiledContext

logger = logging.getLogger(__name__)

MAX_TOOL_ITERS = 3
FALLBACK_REPLY = (
    "I'm here with you — tell me a bit more about how your body has been feeling."
)


async def run_agent(
    db: AsyncSession,
    patient: Patient,
    compiled: CompiledContext,
    user_text: str,
    session_id: str,
) -> str:
    messages: list[ChatTurn] = list(compiled.history)
    messages.append(ChatTurn(role="user", content=user_text))
    last = LLMResult(text="")

    for _ in range(MAX_TOOL_ITERS):
        last = await complete(
            messages,
            system=compiled.system,
            tools=AGENT_TOOLS,
            language=compiled.language,
        )
        if not last.tool_calls:
            return last.text.strip() or FALLBACK_REPLY

        for call in last.tool_calls:
            if call.name != "remember_fact":
                continue
            key = str(call.arguments.get("key") or "")
            value = str(call.arguments.get("value") or "")
            apply_remember_fact(patient, key, value)
            await write_audit(
                db,
                patient_id=patient.id,
                session_id=session_id,
                kind="memory_write",
                payload={"key": key, "value": value},
            )
            messages.append(
                ChatTurn(
                    role="assistant",
                    content=f'{{"action":"remember_fact","key":"{key}","value":"{value}"}}',
                )
            )
            messages.append(
                ChatTurn(
                    role="user",
                    content="Fact saved. Now reply to the patient. Do not mention the tool.",
                )
            )

    return last.text.strip() or FALLBACK_REPLY
