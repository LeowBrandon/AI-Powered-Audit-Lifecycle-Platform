"""Multi-Agent Audit Orchestrator (Proposal Section 21 Pages 33-34).

Coordinates Agents 1 through 6 in a deterministic, fully traceable pipeline:
  1. TicketIntelligenceAgent.extract(ticket)
  2. EvidenceExtractionAgent.extract(ticket_ctx)
  3. AuditRulesAgent.get_rules(conn, ticket_ctx, rag)
  4. AIAuditReasoningAgent.evaluate(ticket_ctx, rules, evidence, config)
  5. RiskScoringAgent.calculate(ticket_ctx, evaluations, config)
  6. ContinuousMonitoringAgent.evaluate_alert(ticket_ctx, evaluations, risk, config)
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any

from app.agents.audit_reasoning import AIAuditReasoningAgent, EvaluatedCriterion
from app.agents.audit_rules import AuditRulesAgent
from app.agents.base import AgentStepTrace
from app.agents.continuous_monitoring import AlertDecision, ContinuousMonitoringAgent
from app.agents.evidence_extraction import EvidenceExtractionAgent, ExtractedEvidence
from app.agents.risk_scoring import RiskAssessment, RiskScoringAgent
from app.agents.ticket_intelligence import TicketContext, TicketIntelligenceAgent
from app.services.rag_knowledge import RAGKnowledgeBase


@dataclass
class OrchestrationOutput:
    ticket_ctx: TicketContext
    evidence: ExtractedEvidence
    rules: list[dict[str, Any]]
    evaluations: list[EvaluatedCriterion]
    ai_summary: str
    risk: RiskAssessment
    alert: AlertDecision
    traces: list[AgentStepTrace]


class AuditOrchestrator:
    """Executes the 6-agent ticket audit pipeline and captures full step telemetry."""

    def __init__(self) -> None:
        self.ticket_agent = TicketIntelligenceAgent()
        self.evidence_agent = EvidenceExtractionAgent()
        self.rules_agent = AuditRulesAgent()
        self.reasoning_agent = AIAuditReasoningAgent()
        self.risk_agent = RiskScoringAgent()
        self.monitoring_agent = ContinuousMonitoringAgent()

    def audit_ticket(
        self,
        conn: sqlite3.Connection,
        raw_ticket: dict[str, Any],
        config: dict[str, Any],
        rag: RAGKnowledgeBase,
    ) -> OrchestrationOutput:
        traces: list[AgentStepTrace] = []

        ticket_ctx, t1 = self.ticket_agent.extract(raw_ticket)
        traces.append(t1)

        evidence, t2 = self.evidence_agent.extract(ticket_ctx)
        traces.append(t2)

        rules, t3 = self.rules_agent.get_rules(conn, ticket_ctx, rag)
        traces.append(t3)

        evaluations, ai_summary, t4 = self.reasoning_agent.evaluate(
            ticket_ctx, rules, evidence, config
        )
        traces.append(t4)

        risk, t5 = self.risk_agent.calculate(ticket_ctx, evaluations, config)
        traces.append(t5)

        alert, t6 = self.monitoring_agent.evaluate_alert(
            ticket_ctx, evaluations, risk, config
        )
        traces.append(t6)

        return OrchestrationOutput(
            ticket_ctx=ticket_ctx,
            evidence=evidence,
            rules=rules,
            evaluations=evaluations,
            ai_summary=ai_summary,
            risk=risk,
            alert=alert,
            traces=traces,
        )


orchestrator = AuditOrchestrator()
