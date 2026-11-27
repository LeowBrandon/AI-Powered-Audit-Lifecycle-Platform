"""Analytics & Management Insights API (Proposal Sections 14, 25 & Agent 9)."""

from __future__ import annotations

from fastapi import APIRouter

from app.agents.management_insight import ManagementInsightAgent
from app.database import db_session

router = APIRouter(prefix="/api", tags=["Analytics & Management Insights"])
insight_agent = ManagementInsightAgent()


@router.get("/analytics")
def get_analytics():
    with db_session() as conn:
        return insight_agent.generate_analytics(conn)
