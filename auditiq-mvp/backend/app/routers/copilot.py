"""Auditor Copilot API (Proposal Section 4 Agent 7 & Screen 5)."""

from __future__ import annotations

from fastapi import APIRouter

from app.agents.auditor_copilot import AuditorCopilotAgent
from app.database import db_session
from app.schemas import CopilotRequest
from app.services.rag_knowledge import rag_kb

router = APIRouter(prefix="/api", tags=["Auditor Copilot"])
copilot_agent = AuditorCopilotAgent()


@router.post("/copilot")
def ask_copilot(payload: CopilotRequest):
    with db_session() as conn:
        ticket_id = None if payload.ticket_id in {None, "", "ALL"} else payload.ticket_id
        return copilot_agent.answer(
            conn,
            question=payload.question,
            ticket_id=ticket_id,
            rag=rag_kb,
            user_role=payload.user_role,
        )
