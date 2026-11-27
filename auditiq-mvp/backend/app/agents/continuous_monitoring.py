"""Agent 6 — Continuous Monitoring Agent (Proposal Section 4 Page 12 & Section 13 Page 24).

Detects compliance risks proactively while tickets are still active (pre-closure /
pre-implementation), generates actionable owner alerts, and resolves alerts automatically
when gaps are remediated.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.agents.audit_reasoning import EvaluatedCriterion
from app.agents.base import AgentStepTrace, elapsed_ms, timer_start
from app.agents.risk_scoring import RiskAssessment
from app.agents.ticket_intelligence import TicketContext


@dataclass
class AlertDecision:
    should_alert: bool
    severity: str
    title: str
    message: str
    recommendation: str
    predicted_risk: float


class ContinuousMonitoringAgent:
    """Monitors active and high-risk tickets to convert auditing into proactive governance."""

    def evaluate_alert(
        self,
        ctx: TicketContext,
        evaluations: list[EvaluatedCriterion],
        risk: RiskAssessment,
        config: dict[str, Any],
    ) -> tuple[AlertDecision, AgentStepTrace]:
        start = timer_start()
        proactive_enabled = bool(config.get("proactive_alerts_enabled", True))
        fails = [e for e in evaluations if e.status == "FAIL"]
        reviews = [e for e in evaluations if e.status == "REVIEW"]

        should_alert = False
        severity = risk.risk_band
        title = ""
        message = ""
        recommendation = ""

        if proactive_enabled:
            if ctx.is_active and (risk.risk_band in {"CRITICAL", "HIGH"} or fails or ctx.sla_status in {"At Risk", "Breached"}):
                should_alert = True
                top_issues = [e.criterion_name for e in fails[:2]] or [e.criterion_name for e in reviews[:2]]
                if not top_issues and ctx.sla_status in {"At Risk", "Breached"}:
                    top_issues = ["SLA breach risk"]
                title = f"{', '.join(top_issues)} detected pre-closure"
                if ctx.ticket_type == "CR":
                    message = (
                        f"Change request {ctx.ticket_id} ({ctx.short_description}) is '{ctx.status}' "
                        f"with unresolved gaps: {', '.join(top_issues)}."
                    )
                    recommendation = (
                        fails[0].recommendation
                        if fails
                        else "Resolve missing change controls before scheduled implementation window."
                    )
                elif ctx.ticket_type == "INC":
                    message = (
                        f"Active incident {ctx.ticket_id} ({ctx.assignment_group}) flagged for "
                        f"{', '.join(top_issues)} (SLA: {ctx.sla_status})."
                    )
                    recommendation = (
                        fails[0].recommendation
                        if fails
                        else "Expedite resolution and document root cause before SLA breach."
                    )
                else:
                    message = (
                        f"Active service request {ctx.ticket_id} has incomplete governance evidence: "
                        f"{', '.join(top_issues)}."
                    )
                    recommendation = (
                        fails[0].recommendation
                        if fails
                        else "Complete authorization and fulfillment evidence prior to closure."
                    )
            elif not ctx.is_active and risk.risk_band == "CRITICAL":
                should_alert = True
                top_issues = [e.criterion_name for e in fails[:2]]
                title = f"Critical post-closure compliance breach ({', '.join(top_issues)})"
                message = (
                    f"Closed ticket {ctx.ticket_id} triggered critical audit risk ({int(risk.risk_score)}/100) "
                    f"due to {', '.join(top_issues)}."
                )
                recommendation = "Immediate auditor escalation and corrective governance action required."
            elif ctx.is_active and reviews:
                should_alert = True
                severity = "REVIEW"
                title = f"{reviews[0].criterion_name} requires early verification"
                message = f"Active ticket {ctx.ticket_id} has ambiguous {reviews[0].criterion_name.lower()} evidence."
                recommendation = reviews[0].recommendation

        decision = AlertDecision(
            should_alert=should_alert,
            severity=severity,
            title=title,
            message=message,
            recommendation=recommendation,
            predicted_risk=risk.predicted_failure_prob,
        )

        trace = AgentStepTrace(
            agent_number=6,
            agent_name="Continuous Monitoring Agent",
            phase="Proactive Governance & Alerting",
            status="completed",
            duration_ms=elapsed_ms(start),
            summary=(
                f"Triggered proactive {severity} alert: {title}"
                if should_alert
                else "No active compliance alert required; any prior open alerts cleared."
            ),
            metrics={
                "alertTriggered": should_alert,
                "severity": severity if should_alert else "NONE",
                "proactivePreClosure": ctx.is_active and should_alert,
            },
        )
        return decision, trace
