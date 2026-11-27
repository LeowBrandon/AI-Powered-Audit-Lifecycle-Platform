"""Agent 5 — Risk Scoring, Predictive Audit & Intelligent Sampling Agent.

Implements:
- Section 4 Page 11: 7-factor Risk Score formula
- Section 15 Page 26: Predictive Audit failure risk probability & drivers
- Section 16 Page 27: Intelligent Audit Sampling routing tier
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.agents.audit_reasoning import EvaluatedCriterion
from app.agents.base import AgentStepTrace, elapsed_ms, timer_start
from app.agents.ticket_intelligence import TicketContext


@dataclass
class RiskAssessment:
    audit_score: float
    risk_score: float
    risk_band: str  # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    risk_breakdown: dict[str, float]
    predicted_failure_prob: float
    predictive_factors: list[str]
    overall_decision: str  # "PASS" | "FAIL" | "REVIEW"
    sampling_tier: str  # "Automated Audit" | "Sampled Review" | "Mandatory Audit" | "Immediate Escalation"
    audit_status: str  # "Auto-Closed" | "Needs Review" | "Escalated"
    ai_confidence: float


class RiskScoringAgent:
    """Computes audit compliance score, 7-factor risk score, predictive risk, and sampling routing."""

    def calculate(
        self,
        ctx: TicketContext,
        evaluations: list[EvaluatedCriterion],
        config: dict[str, Any],
    ) -> tuple[RiskAssessment, AgentStepTrace]:
        start = timer_start()
        crit_thresh = int(config.get("critical_risk_threshold", 80))
        high_thresh = int(config.get("high_risk_threshold", 60))
        med_thresh = int(config.get("medium_risk_threshold", 35))
        conf_rec = int(config.get("confidence_recommend", 80))
        auto_close_low = bool(config.get("auto_close_low_risk", True))

        # 1. Weighted compliance score (0-100)
        total_weight = sum(e.weight for e in evaluations) or 1.0
        earned = 0.0
        for e in evaluations:
            if e.status == "PASS":
                earned += e.weight
            elif e.status == "REVIEW":
                earned += e.weight * 0.55
        audit_score = round((earned / total_weight) * 100.0, 1)

        # 2. Exact 7-Factor Risk Score Formula (Proposal Page 11)
        fails = [e for e in evaluations if e.status == "FAIL"]
        reviews = [e for e in evaluations if e.status == "REVIEW"]

        rule_violations = 0.0
        for e in fails:
            if e.severity_if_failed == "CRITICAL":
                rule_violations += 24.0
            elif e.severity_if_failed == "HIGH":
                rule_violations += 18.0
            else:
                rule_violations += 11.0
        rule_violations = min(44.0, round(rule_violations, 1))

        missing_evidence = min(
            18.0,
            round(sum(5.5 for e in fails if e.missing_evidence) + sum(4.0 for e in reviews), 1),
        )
        historical_risk = min(12.0, round(ctx.historical_group_risk * 0.65, 1))
        ticket_complexity = min(14.0, round(ctx.complexity_score * 0.85, 1))
        sla_breach = (
            14.0
            if ctx.sla_status == "Breached"
            else 8.0
            if ctx.sla_status == "At Risk"
            else 0.0
        )

        avg_conf = (
            sum(e.confidence for e in evaluations) / len(evaluations)
            if evaluations
            else 95.0
        )
        low_conf_items = [e for e in evaluations if e.confidence < conf_rec]
        ai_confidence_risk = min(
            10.0,
            round((max(0.0, 96.0 - avg_conf) * 0.45) + len(low_conf_items) * 2.5, 1),
        )
        previous_audit_history = min(8.0, round(ctx.previous_audit_issues * 2.5, 1))

        # When all criteria PASS and SLA is met, keep residual risk genuinely low
        raw_risk = (
            rule_violations
            + historical_risk
            + ticket_complexity
            + sla_breach
            + missing_evidence
            + ai_confidence_risk
            + previous_audit_history
        )
        if not fails and not reviews and sla_breach == 0:
            raw_risk = min(raw_risk, max(12.0, med_thresh - 6.0))

        risk_score = round(max(5.0, min(98.0, raw_risk)), 1)

        if risk_score >= crit_thresh:
            risk_band = "CRITICAL"
            sampling_tier = "Immediate Escalation"
        elif risk_score >= high_thresh:
            risk_band = "HIGH"
            sampling_tier = "Mandatory Audit"
        elif risk_score >= med_thresh:
            risk_band = "MEDIUM"
            sampling_tier = "Sampled Review"
        else:
            risk_band = "LOW"
            sampling_tier = "Automated Audit"

        # 3. Three-Way Overall Decision & Workflow Routing (Section 6 & 7)
        if fails:
            overall_decision = "FAIL"
        elif reviews or avg_conf < conf_rec:
            overall_decision = "REVIEW"
        else:
            overall_decision = "PASS"

        if risk_band == "CRITICAL":
            audit_status = "Escalated"
        elif overall_decision in {"FAIL", "REVIEW"} or risk_band == "HIGH":
            audit_status = "Needs Review"
        elif risk_band == "MEDIUM":
            audit_status = "Needs Review"
        else:
            audit_status = "Auto-Closed" if auto_close_low else "Needs Review"

        # 4. Predictive Audit Probability & Factors (Section 15 Page 26)
        predictive_factors: list[str] = []
        if ctx.ticket_type == "CR" and (ctx.priority in {"P1", "P2"} or ctx.is_production_scope):
            predictive_factors.append(f"High-risk {ctx.priority} production change")
        for e in fails:
            if e.criterion_name == "Business approval":
                predictive_factors.append("Business approval missing or pending")
            elif e.criterion_name == "Rollback plan":
                predictive_factors.append("No rollback plan detected")
            elif e.criterion_name == "Post-implementation review":
                predictive_factors.append("Post-implementation validation not yet recorded")
            elif e.criterion_name == "Authorization":
                predictive_factors.append("Required authorization missing")
            else:
                predictive_factors.append(f"{e.criterion_name} violation detected")
        for e in reviews:
            predictive_factors.append(f"{e.criterion_name} evidence incomplete ({int(e.confidence)}% confidence)")
        if ctx.sla_status in {"At Risk", "Breached"}:
            predictive_factors.append(f"SLA {ctx.sla_status.lower()} — breach window approaching")
        if ctx.previous_audit_issues >= 2:
            predictive_factors.append(f"Similar historical {ctx.assignment_group} tickets failed audits")
        if ctx.is_active and ctx.target_window:
            predictive_factors.append(f"Implementation scheduled soon ({ctx.target_window})")

        if ctx.is_active:
            predicted_prob = min(96.0, round(risk_score + (6.0 if fails else 0.0), 1))
        else:
            predicted_prob = min(95.0, round(risk_score * 0.85, 1)) if fails else round(max(4.0, risk_score * 0.4), 1)

        breakdown = {
            "Rule Violations": rule_violations,
            "Missing Evidence": missing_evidence,
            "SLA Breach": sla_breach,
            "Ticket Complexity": ticket_complexity,
            "Historical Risk": historical_risk,
            "AI Confidence": ai_confidence_risk,
            "Previous Audit History": previous_audit_history,
        }

        assessment = RiskAssessment(
            audit_score=audit_score,
            risk_score=risk_score,
            risk_band=risk_band,
            risk_breakdown=breakdown,
            predicted_failure_prob=predicted_prob,
            predictive_factors=predictive_factors[:6],
            overall_decision=overall_decision,
            sampling_tier=sampling_tier,
            audit_status=audit_status,
            ai_confidence=round(avg_conf, 1),
        )

        trace = AgentStepTrace(
            agent_number=5,
            agent_name="Risk Scoring Agent",
            phase="Phase 4 — Risk Scoring & Intelligent Sampling",
            status="completed",
            duration_ms=elapsed_ms(start),
            summary=(
                f"Assigned Compliance {audit_score}%, Risk {risk_score}/100 ({risk_band}), "
                f"Decision {overall_decision}, Routing '{sampling_tier}'."
            ),
            metrics={
                "auditScore": audit_score,
                "riskScore": risk_score,
                "riskBand": risk_band,
                "predictedFailureProb": predicted_prob,
                "samplingTier": sampling_tier,
            },
        )
        return assessment, trace
