"""Agent 3 — Audit Rules Agent (Proposal Section 4, Page 8).

Selects applicable deterministic and AI audit criteria for INC, SR, and CR tickets
from the governance database and retrieves grounded policy passages via RAG.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from app.agents.base import AgentStepTrace, elapsed_ms, timer_start
from app.agents.ticket_intelligence import TicketContext
from app.services.rag_knowledge import RAGKnowledgeBase


class AuditRulesAgent:
    """Determines active audit rules and enriches each criterion with Policy KB context."""

    def get_rules(
        self,
        conn: sqlite3.Connection,
        ctx: TicketContext,
        rag: RAGKnowledgeBase,
    ) -> tuple[list[dict[str, Any]], AgentStepTrace]:
        start = timer_start()
        rows = conn.execute(
            """
            SELECT criterion_id, audit_type, criterion_name, requirement, rule,
                   policy_ref, method, weight, severity_if_failed, active
            FROM audit_criteria
            WHERE audit_type = ? AND active = 1
            ORDER BY criterion_id ASC
            """,
            (ctx.ticket_type,),
        ).fetchall()

        rules: list[dict[str, Any]] = []
        det_count = 0
        ai_count = 0
        for row in rows:
            item = dict(row)
            if item["method"] == "deterministic":
                det_count += 1
            else:
                ai_count += 1

            # Retrieve top policy passage from Knowledge Base (RAG)
            hits = rag.search(
                f"{ctx.ticket_type} {item['criterion_name']} {item['rule']}",
                ticket_type=ctx.ticket_type,
                top_k=1,
            )
            item["rag_policy"] = (
                {
                    "policyId": hits[0].policy_id,
                    "title": hits[0].title,
                    "version": hits[0].version,
                    "excerpt": hits[0].excerpt,
                    "score": hits[0].score,
                }
                if hits
                else None
            )
            rules.append(item)

        trace = AgentStepTrace(
            agent_number=3,
            agent_name="Audit Rules Agent",
            phase="Phase 2 — Policy Enrichment & Rule Selection",
            status="completed",
            duration_ms=elapsed_ms(start),
            summary=(
                f"Selected {len(rules)} active {ctx.ticket_type} governance criteria "
                f"({det_count} deterministic rules + {ai_count} AI reasoning checks) "
                f"grounded in Enterprise Policy Knowledge Base."
            ),
            metrics={
                "totalCriteria": len(rules),
                "deterministicRules": det_count,
                "aiCriteria": ai_count,
            },
        )
        return rules, trace
