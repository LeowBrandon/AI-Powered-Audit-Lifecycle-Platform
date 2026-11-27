"""Agent 4 — AI Audit Reasoning Agent (Proposal Sections 4, 6, 11, 22, 23).

Combines Deterministic Rules + AI Reasoning to evaluate extracted evidence
against applicable audit criteria using the Three-Way Decision Model (PASS / FAIL / REVIEW)
and AI Confidence Framework (95-100% Auto, 80-94% Recommendation, <80% Human Review).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.agents.base import AgentStepTrace, elapsed_ms, llm_client, timer_start
from app.agents.evidence_extraction import ExtractedEvidence
from app.agents.ticket_intelligence import TicketContext
from app.config import settings


@dataclass
class EvaluatedCriterion:
    criterion_id: str
    criterion_name: str
    requirement: str
    method: str
    policy_ref: str
    weight: float
    severity_if_failed: str
    status: str  # "PASS" | "FAIL" | "REVIEW"
    confidence: float
    confidence_tier: str  # "Auto Decision" | "AI Recommendation" | "Human Review"
    reason: str
    detected_evidence: str
    missing_evidence: str
    evidence_source: str
    searched_sources: list[str]
    recommendation: str


CRITERION_TO_FACT_KEY: dict[str, str] = {
    "Categorization": "categorization",
    "Priority": "priority",
    "SLA": "sla",
    "Root Cause": "root_cause",
    "Resolution": "resolution",
    "Customer Communication": "customer_communication",
    "Closure Code": "closure",
    "Request classification": "categorization",
    "Authorization": "manager_authorization",
    "Fulfillment": "fulfillment",
    "Documentation": "documentation",
    "Closure": "closure",
    "Risk assessment": "risk_assessment",
    "Business approval": "business_approval",
    "Technical approval": "technical_approval",
    "Implementation plan": "implementation_plan",
    "Rollback plan": "rollback_plan",
    "Testing": "testing",
    "Post-implementation review": "post_implementation_review",
}


class AIAuditReasoningAgent:
    """Evaluates evidence against audit criteria with full explainability."""

    def evaluate(
        self,
        ctx: TicketContext,
        rules: list[dict[str, Any]],
        evidence: ExtractedEvidence,
        config: dict[str, Any],
    ) -> tuple[list[EvaluatedCriterion], str, AgentStepTrace]:
        start = timer_start()
        conf_auto = int(config.get("confidence_auto", 95))
        conf_rec = int(config.get("confidence_recommend", 80))

        evaluations: list[EvaluatedCriterion] = []
        for rule in rules:
            eval_item = self._evaluate_single(ctx, rule, evidence, conf_auto, conf_rec)
            evaluations.append(eval_item)

        summary = self._build_audit_summary(ctx, evaluations)

        passed = sum(1 for e in evaluations if e.status == "PASS")
        failed = sum(1 for e in evaluations if e.status == "FAIL")
        review = sum(1 for e in evaluations if e.status == "REVIEW")

        trace = AgentStepTrace(
            agent_number=4,
            agent_name="AI Audit Reasoning Agent",
            phase="Phase 4 — Rules + AI Reasoning",
            status="completed",
            duration_ms=elapsed_ms(start),
            model=settings.active_ai_model_label,
            summary=(
                f"Evaluated {len(evaluations)} criteria with Three-Way Decision Model: "
                f"{passed} PASS, {failed} FAIL, {review} REVIEW."
            ),
            metrics={
                "passCount": passed,
                "failCount": failed,
                "reviewCount": review,
                "llmAugmented": settings.llm_enabled,
            },
        )
        return evaluations, summary, trace

    def _evaluate_single(
        self,
        ctx: TicketContext,
        rule: dict[str, Any],
        evidence: ExtractedEvidence,
        conf_auto: int,
        conf_rec: int,
    ) -> EvaluatedCriterion:
        name = rule["criterion_name"]
        method = rule["method"]
        policy_ref = rule["policy_ref"]
        weight = float(rule["weight"])
        severity = rule["severity_if_failed"]

        fact_key = CRITERION_TO_FACT_KEY.get(name)
        fact = evidence.facts.get(fact_key) if fact_key else self._evaluate_custom_criterion(ctx, rule)

        # Evaluate status using Three-Way Decision Model
        if fact["found"] and not fact.get("partial"):
            status = "PASS"
            confidence = float(fact["confidence"])
            reason = f"{name} requirement satisfied: {fact['detected']}"
            recommendation = "No corrective action required; evidence archived for audit trail."
        elif fact.get("partial"):
            # Ambiguous or incomplete evidence -> REVIEW (reduces hallucination risk!)
            status = "REVIEW"
            confidence = float(min(fact["confidence"], conf_rec - 2)) if method == "ai" else float(fact["confidence"])
            if name == "SLA" and ctx.sla_status == "At Risk":
                status = "REVIEW"
                confidence = 91.0
                reason = f"SLA is currently At Risk on active ticket {ctx.ticket_id}; breach is projected without intervention."
                recommendation = "Prioritize execution and notify assignment group lead to prevent SLA breach."
            elif name in {"Closure Code", "Closure"} and ctx.is_active:
                status = "PASS"
                confidence = 90.0
                reason = f"Ticket is active ({ctx.status}); closure control will be verified upon closure."
                recommendation = "Ensure standardized closure code is entered before closing ticket."
            else:
                reason = (
                    f"Partial or ambiguous evidence detected for {name}. "
                    f"{fact['detected']} Auditor confirmation required."
                )
                recommendation = f"Request or verify complete {name.lower()} evidence before final sign-off."
        else:
            status = "FAIL"
            confidence = float(fact["confidence"])
            # For active CR tickets, Post-implementation review is expected after implementation
            if name == "Post-implementation review" and ctx.is_active:
                reason = (
                    "Post-implementation validation evidence has not been recorded yet "
                    "and is mandatory prior to change closure."
                )
                recommendation = "Complete post-implementation health checks and record validation evidence before closing CR."
            elif name == "Business approval":
                reason = "Change requires documented business owner authorization before implementation; none detected."
                recommendation = "Obtain documented business owner approval before scheduled change window."
            elif name == "Rollback plan":
                reason = "No actionable rollback plan detected for this change ticket."
                recommendation = "Document step-by-step rollback commands, trigger thresholds, and verification checks."
            elif name == "Authorization":
                reason = "Service request lacks required manager/owner authorization prior to fulfillment."
                recommendation = "Attach documented manager approval record to satisfy SR Governance Policy."
            else:
                reason = f"{name} requirement not satisfied. {fact['missing'] or fact['detected']}"
                recommendation = f"Remediate {name.lower()} gap: {fact['missing'] or rule['rule']}"

        # Governance rule (Section 22): Deterministic policy failures cannot be downgraded by low AI confidence
        if method == "deterministic" and status == "FAIL":
            confidence = max(confidence, 95.0)
        elif method == "ai" and status != "PASS" and confidence < conf_rec:
            status = "REVIEW"

        confidence_tier = (
            "Auto Decision"
            if confidence >= conf_auto
            else "AI Recommendation"
            if confidence >= conf_rec
            else "Human Review"
        )

        # Optional LLM refinement of explanation text when API key is configured
        if settings.llm_enabled and status != "PASS":
            llm_note = llm_client.chat_completion(
                system_prompt=(
                    "You are AuditIQ's AI Audit Reasoning Agent. Write one concise, formal enterprise "
                    "audit explanation sentence grounded strictly in the provided evidence and policy."
                ),
                user_prompt=(
                    f"Ticket: {ctx.ticket_id} ({ctx.ticket_type})\n"
                    f"Criterion: {name} | Policy: {policy_ref} | Status: {status}\n"
                    f"Detected: {fact['detected']}\nMissing: {fact['missing']}"
                ),
                max_tokens=110,
            )
            if llm_note:
                reason = llm_note

        return EvaluatedCriterion(
            criterion_id=rule["criterion_id"],
            criterion_name=name,
            requirement=rule["requirement"],
            method=method,
            policy_ref=policy_ref,
            weight=weight,
            severity_if_failed=severity,
            status=status,
            confidence=round(confidence, 1),
            confidence_tier=confidence_tier,
            reason=reason,
            detected_evidence=fact["detected"],
            missing_evidence=fact["missing"],
            evidence_source=fact["source"],
            searched_sources=list(evidence.searched_sources),
            recommendation=recommendation,
        )

    @staticmethod
    def _evaluate_custom_criterion(ctx: TicketContext, rule: dict[str, Any]) -> dict[str, Any]:
        """Evaluates admin-defined custom rules against the combined ticket corpus."""
        keywords = [
            w.lower()
            for w in rule["criterion_name"].replace("-", " ").split()
            if len(w) > 3
        ]
        corpus = ctx.combined_corpus.lower()
        matches = [kw for kw in keywords if kw in corpus]
        if matches and len(matches) >= max(1, len(keywords) // 2):
            return {
                "found": True,
                "partial": False,
                "source": "Work Notes / Ticket Corpus",
                "detected": f"Custom rule keywords ({', '.join(matches)}) matched in ticket documentation.",
                "missing": "",
                "confidence": 88,
            }
        return {
            "found": False,
            "partial": True,
            "source": "Ticket Corpus",
            "detected": f"No explicit mention of '{rule['criterion_name']}' detected.",
            "missing": f"Verification for custom governance criterion '{rule['criterion_name']}'.",
            "confidence": 74,
        }

    @staticmethod
    def _build_audit_summary(ctx: TicketContext, evaluations: list[EvaluatedCriterion]) -> str:
        fails = [e for e in evaluations if e.status == "FAIL"]
        reviews = [e for e in evaluations if e.status == "REVIEW"]

        if not fails and not reviews:
            return (
                f"All {len(evaluations)} governance criteria for {ctx.ticket_id} ({ctx.ticket_type}) "
                f"are satisfied with verified evidence and high AI confidence."
            )

        parts: list[str] = []
        if fails:
            names = ", ".join(e.criterion_name for e in fails)
            parts.append(f"{len(fails)} non-compliant criteria ({names})")
        if reviews:
            names = ", ".join(e.criterion_name for e in reviews)
            parts.append(f"{len(reviews)} items requiring human review ({names})")

        lifecycle_clause = (
            "Proactive pre-closure governance detected "
            if ctx.is_active
            else "Automated post-closure audit identified "
        )
        return f"{lifecycle_clause}{' and '.join(parts)}."
