"""Core Audit Lifecycle Service bridging Database, Multi-Agent Orchestrator, RAG KB, and WebSockets."""

from __future__ import annotations

import csv
import io
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from app.agents.orchestrator import orchestrator
from app.config import settings
from app.database import parse_json_col
from app.services.rag_knowledge import rag_kb
from app.services.websocket_manager import ws_manager

AUDITORS = ["A. Rahman", "J. Lim", "S. Tan", "M. Lee"]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def short_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def get_governance_config(conn: sqlite3.Connection) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM governance_config WHERE id = 1").fetchone()
    if row:
        return dict(row)
    now = utc_now()
    conn.execute(
        """
        INSERT INTO governance_config (
            id, confidence_auto, confidence_recommend, critical_risk_threshold,
            high_risk_threshold, medium_risk_threshold, medium_sampling_pct,
            proactive_alerts_enabled, auto_close_low_risk, updated_by, updated_at
        ) VALUES (1, 95, 80, 80, 60, 35, 25, 1, 1, 'Governance Administrator', ?)
        """,
        (now,),
    )
    return dict(conn.execute("SELECT * FROM governance_config WHERE id = 1").fetchone())


def refresh_rag_index(conn: sqlite3.Connection) -> int:
    rows = conn.execute("SELECT * FROM policy_documents").fetchall()
    docs = []
    for r in rows:
        d = dict(r)
        d["tags"] = parse_json_col(d.get("tags_json"), [])
        docs.append(d)
    rag_kb.rebuild(docs)
    return len(docs)


def log_audit_trail(
    conn: sqlite3.Connection,
    *,
    ticket_id: str,
    audit_id: str,
    who: str,
    role: str,
    what: str,
    rule: str = "",
    evidence: str = "",
    ai_model: str | None = None,
    confidence: float = 100.0,
    decision: str = "",
    human_override: bool = False,
) -> dict[str, Any]:
    trail_id = short_id("TRL")
    ts = utc_now()
    model_name = ai_model or settings.active_ai_model_label
    conn.execute(
        """
        INSERT INTO audit_trail (
            trail_id, ticket_id, audit_id, who, role, what, timestamp,
            rule, evidence, ai_model, confidence, decision, human_override
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            trail_id,
            ticket_id,
            audit_id,
            who,
            role,
            what,
            ts,
            rule,
            evidence,
            model_name,
            confidence,
            decision,
            1 if human_override else 0,
        ),
    )
    return {
        "trailId": trail_id,
        "ticketId": ticket_id,
        "auditId": audit_id,
        "who": who,
        "role": role,
        "what": what,
        "timestamp": ts,
        "rule": rule,
        "evidence": evidence,
        "aiModel": model_name,
        "confidence": confidence,
        "decision": decision,
        "humanOverride": human_override,
    }


def pick_auditor(ticket_id: str) -> str:
    idx = sum(ord(ch) for ch in ticket_id) % len(AUDITORS)
    return AUDITORS[idx]


def run_ticket_audit(
    conn: sqlite3.Connection,
    ticket_id: str,
    *,
    actor: str = "AuditIQ Orchestrator",
    actor_role: str = "AI Agent",
    auditor_override: str | None = None,
    broadcast: bool = True,
) -> dict[str, Any]:
    """Runs the 6-agent pipeline on a ticket and persists results, findings, alerts, and trail."""
    t_row = conn.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)).fetchone()
    if not t_row:
        raise KeyError(f"Ticket {ticket_id} not found")
    raw_ticket = dict(t_row)

    cfg = get_governance_config(conn)
    output = orchestrator.audit_ticket(conn, raw_ticket, cfg, rag_kb)
    now = utc_now()

    existing_audit = conn.execute(
        "SELECT audit_id, auditor, qc_status, qc_reviewer, qc_note FROM audits WHERE ticket_id = ?",
        (ticket_id,),
    ).fetchone()
    audit_id = existing_audit["audit_id"] if existing_audit else short_id("AUD")
    assigned_auditor = (
        auditor_override
        or (existing_audit["auditor"] if existing_audit and existing_audit["auditor"] != "Unassigned" else pick_auditor(ticket_id))
    )
    qc_status = (
        existing_audit["qc_status"]
        if existing_audit and existing_audit["qc_status"] in {"Verified", "Disputed"}
        else ("Pending" if output.risk.risk_band in {"CRITICAL", "HIGH"} else "Not Required")
    )
    qc_reviewer = existing_audit["qc_reviewer"] if existing_audit else ""
    qc_note = existing_audit["qc_note"] if existing_audit else ""

    # Estimated effective audit time (low risk auto-audited ~1.5-3m; complex review ~6-9m vs 25m manual)
    est_duration = (
        2.1 if output.risk.sampling_tier == "Automated Audit"
        else 5.4 if output.risk.sampling_tier == "Sampled Review"
        else 7.8 if output.risk.sampling_tier == "Mandatory Audit"
        else 9.2
    )

    if existing_audit:
        conn.execute(
            """
            UPDATE audits SET
                audit_type = ?, audit_score = ?, risk_score = ?, risk_band = ?,
                risk_breakdown_json = ?, predicted_failure_prob = ?, predictive_factors_json = ?,
                decision = ?, sampling_tier = ?, ai_confidence = ?, ai_summary = ?,
                status = ?, auditor = ?, qc_status = ?, qc_reviewer = ?, qc_note = ?,
                agent_trace_json = ?, highlights_json = ?, audit_duration_min = ?, updated_at = ?
            WHERE audit_id = ?
            """,
            (
                output.ticket_ctx.ticket_type,
                output.risk.audit_score,
                output.risk.risk_score,
                output.risk.risk_band,
                json.dumps(output.risk.risk_breakdown),
                output.risk.predicted_failure_prob,
                json.dumps(output.risk.predictive_factors),
                output.risk.overall_decision,
                output.risk.sampling_tier,
                output.risk.ai_confidence,
                output.ai_summary,
                output.risk.audit_status,
                assigned_auditor,
                qc_status,
                qc_reviewer,
                qc_note,
                json.dumps([t.to_dict() for t in output.traces]),
                json.dumps([h.to_dict() for h in output.evidence.highlights]),
                est_duration,
                now,
                audit_id,
            ),
        )
        conn.execute("DELETE FROM audit_results WHERE audit_id = ?", (audit_id,))
        conn.execute("DELETE FROM findings WHERE audit_id = ?", (audit_id,))
    else:
        conn.execute(
            """
            INSERT INTO audits (
                audit_id, ticket_id, audit_type, audit_score, risk_score, risk_band,
                risk_breakdown_json, predicted_failure_prob, predictive_factors_json,
                decision, sampling_tier, ai_confidence, ai_summary, status, auditor,
                qc_status, qc_reviewer, qc_note, agent_trace_json, highlights_json,
                audit_duration_min, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audit_id,
                ticket_id,
                output.ticket_ctx.ticket_type,
                output.risk.audit_score,
                output.risk.risk_score,
                output.risk.risk_band,
                json.dumps(output.risk.risk_breakdown),
                output.risk.predicted_failure_prob,
                json.dumps(output.risk.predictive_factors),
                output.risk.overall_decision,
                output.risk.sampling_tier,
                output.risk.ai_confidence,
                output.ai_summary,
                output.risk.audit_status,
                assigned_auditor,
                qc_status,
                qc_reviewer,
                qc_note,
                json.dumps([t.to_dict() for t in output.traces]),
                json.dumps([h.to_dict() for h in output.evidence.highlights]),
                est_duration,
                now,
                now,
            ),
        )

    for ev in output.evaluations:
        conn.execute(
            """
            INSERT INTO audit_results (
                result_id, audit_id, criterion_id, criterion_name, requirement, method,
                policy_ref, status, confidence, confidence_tier, reason,
                detected_evidence, missing_evidence, evidence_source,
                searched_sources_json, recommendation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                short_id("RES"),
                audit_id,
                ev.criterion_id,
                ev.criterion_name,
                ev.requirement,
                ev.method,
                ev.policy_ref,
                ev.status,
                ev.confidence,
                ev.confidence_tier,
                ev.reason,
                ev.detected_evidence,
                ev.missing_evidence,
                ev.evidence_source,
                json.dumps(ev.searched_sources),
                ev.recommendation,
            ),
        )
        if ev.status in {"FAIL", "REVIEW"}:
            sev = ev.severity_if_failed if ev.status == "FAIL" else "MEDIUM"
            conn.execute(
                """
                INSERT INTO findings (
                    finding_id, audit_id, ticket_id, criterion_id, criterion_name, policy_ref,
                    severity, ai_status, status, confidence, description,
                    detected_evidence, missing_evidence, recommendation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Open', ?, ?, ?, ?, ?)
                """,
                (
                    short_id("FND"),
                    audit_id,
                    ticket_id,
                    ev.criterion_id,
                    ev.criterion_name,
                    ev.policy_ref,
                    sev,
                    ev.status,
                    ev.confidence,
                    ev.reason,
                    ev.detected_evidence,
                    ev.missing_evidence,
                    ev.recommendation,
                ),
            )

    # Sync Continuous Monitoring Alerts
    active_alert = conn.execute(
        "SELECT alert_id FROM monitoring_alerts WHERE ticket_id = ? AND status IN ('Active', 'Acknowledged')",
        (ticket_id,),
    ).fetchone()
    if output.alert.should_alert:
        if active_alert:
            conn.execute(
                """
                UPDATE monitoring_alerts
                SET severity = ?, title = ?, message = ?, recommendation = ?, predicted_risk = ?, status = 'Active'
                WHERE alert_id = ?
                """,
                (
                    output.alert.severity,
                    output.alert.title,
                    output.alert.message,
                    output.alert.recommendation,
                    output.alert.predicted_risk,
                    active_alert["alert_id"],
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO monitoring_alerts (
                    alert_id, ticket_id, severity, title, message, recommendation,
                    predicted_risk, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'Active', ?)
                """,
                (
                    short_id("ALT"),
                    ticket_id,
                    output.alert.severity,
                    output.alert.title,
                    output.alert.message,
                    output.alert.recommendation,
                    output.alert.predicted_risk,
                    now,
                ),
            )
    elif active_alert:
        conn.execute(
            "UPDATE monitoring_alerts SET status = 'Resolved', resolved_at = ? WHERE alert_id = ?",
            (now, active_alert["alert_id"]),
        )

    log_audit_trail(
        conn,
        ticket_id=ticket_id,
        audit_id=audit_id,
        who=actor,
        role=actor_role,
        what=(
            f"Multi-agent audit completed: Compliance {output.risk.audit_score}%, "
            f"Risk {output.risk.risk_score} ({output.risk.risk_band}), Decision {output.risk.overall_decision}."
        ),
        rule=f"{output.ticket_ctx.ticket_type} Governance Ruleset ({len(output.evaluations)} checks)",
        evidence=output.ai_summary,
        confidence=output.risk.ai_confidence,
        decision=output.risk.overall_decision,
        human_override=False,
    )

    detail = get_ticket_detail(conn, ticket_id)
    if broadcast:
        ws_manager.broadcast_sync(
            "audit_updated",
            {
                "ticketId": ticket_id,
                "ticketType": output.ticket_ctx.ticket_type,
                "auditScore": output.risk.audit_score,
                "riskScore": output.risk.risk_score,
                "riskBand": output.risk.risk_band,
                "decision": output.risk.overall_decision,
                "alertTriggered": output.alert.should_alert,
                "alertTitle": output.alert.title,
            },
        )
    return detail


def apply_finding_action(
    conn: sqlite3.Connection,
    ticket_id: str,
    finding_id: str,
    *,
    decision: str,
    note: str,
    auditor: str,
    role: str,
    improvement_target: str,
) -> dict[str, Any]:
    """Executes Human-in-the-Loop governance decision on a finding & logs Feedback + Audit Trail."""
    f_row = conn.execute(
        "SELECT * FROM findings WHERE finding_id = ? AND ticket_id = ?",
        (finding_id, ticket_id),
    ).fetchone()
    if not f_row:
        raise KeyError(f"Finding {finding_id} not found on ticket {ticket_id}")
    finding = dict(f_row)
    now = utc_now()
    audit_id = finding["audit_id"]

    is_override = decision in {"OVERRIDE_PASS", "OVERRIDE_FAIL"}
    new_finding_status = (
        "Approved"
        if decision == "APPROVE_FINDING"
        else "Overridden"
        if is_override
        else "Evidence Requested"
    )
    human_decision_label = (
        "PASS"
        if decision == "OVERRIDE_PASS"
        else "FAIL"
        if decision in {"APPROVE_FINDING", "OVERRIDE_FAIL"}
        else "REQUEST_EVIDENCE"
    )

    conn.execute(
        """
        UPDATE findings
        SET status = ?, human_decision = ?, human_note = ?, decided_by = ?, decided_at = ?
        WHERE finding_id = ?
        """,
        (new_finding_status, human_decision_label, note, auditor, now, finding_id),
    )

    # Sync corresponding AuditResult row if overridden
    if decision == "OVERRIDE_PASS":
        conn.execute(
            """
            UPDATE audit_results
            SET status = 'PASS', reason = ?
            WHERE audit_id = ? AND criterion_id = ?
            """,
            (f"Human Override (PASS) by {auditor}: {note}", audit_id, finding["criterion_id"]),
        )
    elif decision == "OVERRIDE_FAIL":
        conn.execute(
            """
            UPDATE audit_results
            SET status = 'FAIL', reason = ?
            WHERE audit_id = ? AND criterion_id = ?
            """,
            (f"Human Override (FAIL) by {auditor}: {note}", audit_id, finding["criterion_id"]),
        )

    # Record into Closed-Loop Learning Feedback Store on overrides (Proposal Section 24)
    feedback_record = None
    if is_override:
        fb_id = short_id("FBK")
        conn.execute(
            """
            INSERT INTO feedback (
                feedback_id, audit_id, ticket_id, criterion_name, ai_decision,
                auditor_decision, reason, improvement_target, auditor, applied_status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Captured', ?)
            """,
            (
                fb_id,
                audit_id,
                ticket_id,
                finding["criterion_name"],
                finding["ai_status"],
                human_decision_label,
                note,
                improvement_target,
                auditor,
                now,
            ),
        )
        feedback_record = {
            "feedbackId": fb_id,
            "criterion": finding["criterion_name"],
            "aiDecision": finding["ai_status"],
            "auditorDecision": human_decision_label,
            "improvementTarget": improvement_target,
        }

    # Recompute audit score & status after human decision
    _recompute_audit_after_human_action(conn, audit_id, ticket_id, decision, auditor)

    trail = log_audit_trail(
        conn,
        ticket_id=ticket_id,
        audit_id=audit_id,
        who=auditor,
        role=role,
        what=f"{decision.replace('_', ' ').title()} on '{finding['criterion_name']}': {note}",
        rule=finding["policy_ref"],
        evidence=finding["detected_evidence"] or finding["missing_evidence"],
        confidence=finding["confidence"],
        decision=human_decision_label,
        human_override=is_override,
    )

    ws_manager.broadcast_sync(
        "finding_action",
        {
            "ticketId": ticket_id,
            "findingId": finding_id,
            "criterion": finding["criterion_name"],
            "decision": decision,
            "auditor": auditor,
        },
    )

    return {
        "message": f"Recorded {decision.replace('_', ' ').lower()} for {finding['criterion_name']}.",
        "ticket": get_ticket_detail(conn, ticket_id),
        "auditTrailEntry": trail,
        "feedback": feedback_record,
    }


def _recompute_audit_after_human_action(
    conn: sqlite3.Connection,
    audit_id: str,
    ticket_id: str,
    last_decision: str,
    auditor: str,
) -> None:
    cfg = get_governance_config(conn)
    res_rows = conn.execute(
        """
        SELECT r.status, COALESCE(c.weight, 1.0) AS weight
        FROM audit_results r
        LEFT JOIN audit_criteria c ON c.criterion_id = r.criterion_id
        WHERE r.audit_id = ?
        """,
        (audit_id,),
    ).fetchall()
    open_findings = conn.execute(
        "SELECT severity, status FROM findings WHERE audit_id = ? AND status IN ('Open', 'Approved', 'Evidence Requested')",
        (audit_id,),
    ).fetchall()

    total_w = sum(r["weight"] for r in res_rows) or 1.0
    earned = sum(
        r["weight"] if r["status"] == "PASS" else (r["weight"] * 0.55 if r["status"] == "REVIEW" else 0.0)
        for r in res_rows
    )
    new_score = round((earned / total_w) * 100.0, 1)

    audit_row = dict(conn.execute("SELECT * FROM audits WHERE audit_id = ?", (audit_id,)).fetchone())
    new_risk = audit_row["risk_score"]
    if last_decision == "OVERRIDE_PASS":
        new_risk = round(max(12.0, new_risk - 16.0), 1)
        if not open_findings:
            new_risk = min(new_risk, 24.0)
    elif last_decision == "OVERRIDE_FAIL":
        new_risk = round(min(96.0, new_risk + 12.0), 1)

    crit_t = int(cfg["critical_risk_threshold"])
    high_t = int(cfg["high_risk_threshold"])
    med_t = int(cfg["medium_risk_threshold"])
    new_band = (
        "CRITICAL" if new_risk >= crit_t
        else "HIGH" if new_risk >= high_t
        else "MEDIUM" if new_risk >= med_t
        else "LOW"
    )

    if last_decision == "REQUEST_EVIDENCE":
        new_status = "Evidence Requested"
    elif not open_findings and new_score >= 90.0:
        new_status = "Approved"
    else:
        new_status = "In Review"

    new_decision = (
        "PASS" if all(r["status"] == "PASS" for r in res_rows)
        else "FAIL" if any(r["status"] == "FAIL" for r in res_rows)
        else "REVIEW"
    )

    conn.execute(
        """
        UPDATE audits
        SET audit_score = ?, risk_score = ?, risk_band = ?, decision = ?,
            status = ?, auditor = ?, updated_at = ?
        WHERE audit_id = ?
        """,
        (new_score, new_risk, new_band, new_decision, new_status, auditor, utc_now(), audit_id),
    )

    if new_band == "LOW" and not open_findings:
        conn.execute(
            "UPDATE monitoring_alerts SET status = 'Resolved', resolved_at = ? WHERE ticket_id = ? AND status != 'Resolved'",
            (utc_now(), ticket_id),
        )


def apply_ticket_remediation(
    conn: sqlite3.Connection,
    ticket_id: str,
    *,
    action_type: str,
    actor: str,
    role: str,
    approver: str,
    note: str,
    closure_code: str,
) -> dict[str, Any]:
    """Uploads missing approvals/evidence/work notes or closes ticket, then re-runs AI audit."""
    row = conn.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)).fetchone()
    if not row:
        raise KeyError(f"Ticket {ticket_id} not found")
    t = dict(row)
    now = utc_now()
    hhmm = datetime.now(timezone.utc).strftime("%H:%M")

    notes = parse_json_col(t["work_notes_json"], [])
    approvals = parse_json_col(t["approvals_json"], [])
    attachments = parse_json_col(t["attachments_json"], [])
    status = t["status"]
    sla_status = t["sla_status"]
    resolution = t["resolution"]
    c_code = t["closure_code"]
    closed_at = t["closed_at"]

    action_summary = ""
    if action_type == "business_approval":
        approvals.append(
            {
                "type": "Business",
                "approver": approver or "VP Finance Operations",
                "status": "Approved",
                "timestamp": now,
                "note": note or "Business owner approval uploaded via AuditIQ proactive alert remediation.",
            }
        )
        notes.append(
            {
                "timestamp": hhmm,
                "author": approver or "VP Finance Operations",
                "text": note or f"Business owner approval confirmed by {approver or 'VP Finance Operations'} prior to implementation.",
            }
        )
        if status == "Pending Approval":
            status = "Scheduled"
        action_summary = f"Business owner approval uploaded ({approver})"

    elif action_type == "technical_approval":
        approvals.append(
            {
                "type": "Technical",
                "approver": approver or "Principal Architecture Lead",
                "status": "Approved",
                "timestamp": now,
                "note": note or "Technical review and architecture sign-off recorded.",
            }
        )
        action_summary = f"Technical approval uploaded ({approver})"

    elif action_type == "rollback_plan":
        attachments.append(
            {
                "name": "Rollback Runbook v2.pdf",
                "section": "Section 4 — Verified Rollback Procedure",
                "content_summary": note
                or "Step-by-step rollback procedure verified: snapshot restore command, traffic drain sequence, 15-minute RTO, and health validation checks.",
            }
        )
        notes.append(
            {
                "timestamp": hhmm,
                "author": actor,
                "text": note
                or "Complete rollback plan uploaded and peer-verified with step-by-step restore commands and RTO benchmarks.",
            }
        )
        action_summary = "Complete rollback runbook attached"

    elif action_type == "post_validation":
        attachments.append(
            {
                "name": "Post-Implementation Validation Report.pdf",
                "section": "PIR Sign-off",
                "content_summary": note
                or "Post-implementation validation passed: all production cluster health checks, replication lag, and application smoke tests verified green.",
            }
        )
        notes.append(
            {
                "timestamp": hhmm,
                "author": actor,
                "text": note
                or "Post-implementation validation completed successfully; smoke tests passed and customer notified of healthy service.",
            }
        )
        resolution = (
            note
            or "Change implemented within approved window; post-implementation validation and service health checks passed."
        )
        if sla_status == "At Risk":
            sla_status = "Met"
        action_summary = "Post-implementation validation evidence uploaded"

    elif action_type == "root_cause":
        notes.append(
            {
                "timestamp": hhmm,
                "author": actor,
                "text": note
                or "Root cause confirmed via telemetry: connection pool exhaustion triggered by unindexed query; hotfix deployed and problem record linked.",
            }
        )
        if not resolution:
            resolution = "Root cause identified and remediated; service stability verified across all nodes."
        action_summary = "Detailed root cause documentation recorded"

    elif action_type == "customer_communication":
        notes.append(
            {
                "timestamp": hhmm,
                "author": actor,
                "text": note or "Customer notified of service restoration; customer confirmed full recovery.",
            }
        )
        action_summary = "Customer recovery confirmation logged"

    elif action_type == "work_note":
        notes.append(
            {
                "timestamp": hhmm,
                "author": actor,
                "text": note or "Additional audit evidence note recorded.",
            }
        )
        action_summary = "Work note appended"

    elif action_type == "close_ticket":
        status = "Closed"
        closed_at = now
        c_code = closure_code or "Successful - Validated"
        if sla_status == "At Risk":
            sla_status = "Met"
        if not resolution:
            resolution = (
                note
                or "Ticket implemented and validated cleanly; closed with verified compliance evidence."
            )
        notes.append(
            {
                "timestamp": hhmm,
                "author": actor,
                "text": note or f"Ticket closed cleanly with closure code '{c_code}'. Post-implementation validation verified.",
            }
        )
        action_summary = f"Ticket closed ({c_code})"

    conn.execute(
        """
        UPDATE tickets
        SET status = ?, sla_status = ?, closure_code = ?, resolution = ?,
            work_notes_json = ?, approvals_json = ?, attachments_json = ?,
            updated_at = ?, closed_at = ?
        WHERE ticket_id = ?
        """,
        (
            status,
            sla_status,
            c_code,
            resolution,
            json.dumps(notes),
            json.dumps(approvals),
            json.dumps(attachments),
            now,
            closed_at,
            ticket_id,
        ),
    )

    detail = run_ticket_audit(
        conn,
        ticket_id,
        actor=actor,
        actor_role=role,
        broadcast=True,
    )
    return {
        "message": f"{action_summary}. Multi-agent audit re-evaluated {ticket_id}.",
        "ticket": detail,
    }


def get_ticket_detail(conn: sqlite3.Connection, ticket_id: str) -> dict[str, Any]:
    t_row = conn.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)).fetchone()
    if not t_row:
        raise KeyError(f"Ticket {ticket_id} not found")
    t = dict(t_row)

    a_row = conn.execute("SELECT * FROM audits WHERE ticket_id = ?", (ticket_id,)).fetchone()
    if not a_row:
        return run_ticket_audit(conn, ticket_id, broadcast=False)
    a = dict(a_row)

    results = [
        {
            "resultId": r["result_id"],
            "criterionId": r["criterion_id"],
            "criterion": r["criterion_name"],
            "requirement": r["requirement"],
            "method": r["method"],
            "policyRef": r["policy_ref"],
            "status": r["status"],
            "confidence": r["confidence"],
            "confidenceTier": r["confidence_tier"],
            "reason": r["reason"],
            "detectedEvidence": r["detected_evidence"],
            "missingEvidence": r["missing_evidence"],
            "source": r["evidence_source"],
            "searchedSources": parse_json_col(r["searched_sources_json"], []),
            "recommendation": r["recommendation"],
        }
        for r in conn.execute(
            "SELECT * FROM audit_results WHERE audit_id = ? ORDER BY criterion_id ASC",
            (a["audit_id"],),
        ).fetchall()
    ]

    findings = [
        {
            "findingId": f["finding_id"],
            "criterionId": f["criterion_id"],
            "criterion": f["criterion_name"],
            "policyRef": f["policy_ref"],
            "severity": f["severity"],
            "aiStatus": f["ai_status"],
            "status": f["status"],
            "confidence": f["confidence"],
            "description": f["description"],
            "detectedEvidence": f["detected_evidence"],
            "missingEvidence": f["missing_evidence"],
            "recommendation": f["recommendation"],
            "humanDecision": f["human_decision"],
            "humanNote": f["human_note"],
            "decidedBy": f["decided_by"],
            "decidedAt": f["decided_at"],
        }
        for f in conn.execute(
            "SELECT * FROM findings WHERE audit_id = ? ORDER BY CASE severity WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END",
            (a["audit_id"],),
        ).fetchall()
    ]

    trail = [
        {
            "trailId": tr["trail_id"],
            "who": tr["who"],
            "role": tr["role"],
            "what": tr["what"],
            "timestamp": tr["timestamp"],
            "rule": tr["rule"],
            "evidence": tr["evidence"],
            "aiModel": tr["ai_model"],
            "confidence": tr["confidence"],
            "decision": tr["decision"],
            "humanOverride": bool(tr["human_override"]),
        }
        for tr in conn.execute(
            "SELECT * FROM audit_trail WHERE ticket_id = ? ORDER BY timestamp DESC LIMIT 40",
            (ticket_id,),
        ).fetchall()
    ]

    alerts = [
        dict(al)
        for al in conn.execute(
            "SELECT * FROM monitoring_alerts WHERE ticket_id = ? ORDER BY created_at DESC",
            (ticket_id,),
        ).fetchall()
    ]

    return {
        "id": t["ticket_id"],
        "type": t["ticket_type"],
        "shortDescription": t["short_description"],
        "description": t["description"],
        "priority": t["priority"],
        "category": t["category"],
        "businessUnit": t["business_unit"],
        "assignmentGroup": t["assignment_group"],
        "requester": t["requester"],
        "owner": t["owner"],
        "resolver": t["resolver"],
        "state": t["status"],
        "sla": t["sla_status"],
        "closureCode": t["closure_code"],
        "resolution": t["resolution"],
        "targetWindow": t["target_window"],
        "createdAt": t["created_at"],
        "updatedAt": t["updated_at"],
        "closedAt": t["closed_at"],
        "workNotes": parse_json_col(t["work_notes_json"], []),
        "approvals": parse_json_col(t["approvals_json"], []),
        "attachments": parse_json_col(t["attachments_json"], []),
        "relatedTickets": parse_json_col(t["related_tickets_json"], []),
        # Audit metrics
        "auditId": a["audit_id"],
        "compliance": a["audit_score"],
        "risk": a["risk_score"],
        "riskBand": a["risk_band"],
        "riskBreakdown": parse_json_col(a["risk_breakdown_json"], {}),
        "predictedFailureProb": a["predicted_failure_prob"],
        "predictiveFactors": parse_json_col(a["predictive_factors_json"], []),
        "decision": a["decision"],
        "samplingTier": a["sampling_tier"],
        "confidence": a["ai_confidence"],
        "aiSummary": a["ai_summary"],
        "auditStatus": a["status"],
        "auditor": a["auditor"],
        "qcStatus": a["qc_status"],
        "qcReviewer": a["qc_reviewer"],
        "qcNote": a["qc_note"],
        "agentTrace": parse_json_col(a["agent_trace_json"], []),
        "highlights": parse_json_col(a["highlights_json"], []),
        "lastEvaluated": a["updated_at"],
        "results": results,
        "findings": findings,
        "auditTrail": trail,
        "alerts": alerts,
    }


def ingest_ticket_records(
    conn: sqlite3.Connection,
    records: list[dict[str, Any]],
    *,
    actor: str = "Bulk Ingestion Pipeline",
) -> dict[str, Any]:
    """Ingests a batch of ticket dicts (from JSON or CSV upload) and runs multi-agent audits."""
    ingested_ids: list[str] = []
    high_risk = 0
    missing_approvals = 0
    sla_issues = 0
    now = utc_now()

    for idx, rec in enumerate(records):
        t_type = str(rec.get("ticket_type") or rec.get("type") or "INC").upper().strip()
        if t_type not in {"INC", "SR", "CR"}:
            t_type = "INC"
        tid = str(rec.get("ticket_id") or rec.get("id") or "").strip()
        if not tid:
            tid = f"{t_type}{uuid.uuid4().hex[:6].upper()}"

        work_notes = rec.get("work_notes")
        if isinstance(work_notes, str):
            work_notes = [
                {"timestamp": "12:00", "author": rec.get("owner", "Operations"), "text": part.strip()}
                for part in work_notes.split("|")
                if part.strip()
            ]
        elif not isinstance(work_notes, list):
            work_notes = []

        approvals = rec.get("approvals")
        if isinstance(approvals, str):
            approvals = [
                {
                    "type": "Technical" if "technical" in part.lower() else "Manager" if "manager" in part.lower() else "Business",
                    "approver": part.strip(),
                    "status": "Approved",
                    "timestamp": now,
                    "note": "",
                }
                for part in approvals.split("|")
                if part.strip()
            ]
        elif not isinstance(approvals, list):
            approvals = []

        attachments = rec.get("attachments")
        if not isinstance(attachments, list):
            attachments = []

        conn.execute(
            """
            INSERT OR REPLACE INTO tickets (
                ticket_id, ticket_type, short_description, description, priority, category,
                business_unit, assignment_group, requester, owner, resolver, status,
                sla_status, closure_code, resolution, work_notes_json, approvals_json,
                attachments_json, related_tickets_json, target_window,
                historical_group_risk, previous_audit_issues, created_at, updated_at, closed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tid,
                t_type,
                str(rec.get("short_description") or rec.get("shortDescription") or f"Imported {t_type} Ticket #{idx + 1}"),
                str(rec.get("description") or ""),
                str(rec.get("priority") or "P2"),
                str(rec.get("category") or "Infrastructure"),
                str(rec.get("business_unit") or rec.get("businessUnit") or "Enterprise IT"),
                str(rec.get("assignment_group") or rec.get("assignmentGroup") or "Infrastructure"),
                str(rec.get("requester") or "ITSM Importer"),
                str(rec.get("owner") or "Operations Team"),
                str(rec.get("resolver") or "L2 Support"),
                str(rec.get("status") or rec.get("state") or "Closed"),
                str(rec.get("sla_status") or rec.get("sla") or "Met"),
                str(rec.get("closure_code") or rec.get("closureCode") or ""),
                str(rec.get("resolution") or ""),
                json.dumps(work_notes),
                json.dumps(approvals),
                json.dumps(attachments),
                json.dumps(rec.get("related_tickets") or []),
                str(rec.get("target_window") or rec.get("targetWindow") or ""),
                float(rec.get("historical_group_risk", 10.0)),
                int(rec.get("previous_audit_issues", 0)),
                str(rec.get("created_at") or now),
                now,
                now if str(rec.get("status") or rec.get("state") or "Closed") == "Closed" else None,
            ),
        )

        detail = run_ticket_audit(conn, tid, actor=actor, actor_role="AI Agent", broadcast=False)
        ingested_ids.append(tid)
        if detail["riskBand"] in {"HIGH", "CRITICAL"}:
            high_risk += 1
        if any("approval" in f["criterion"].lower() or "authorization" in f["criterion"].lower() for f in detail["findings"]):
            missing_approvals += 1
        if detail["sla"] in {"At Risk", "Breached"}:
            sla_issues += 1

    ws_manager.broadcast_sync(
        "batch_ingested",
        {
            "processed": len(ingested_ids),
            "highRisk": high_risk,
            "missingApprovals": missing_approvals,
            "slaIssues": sla_issues,
        },
    )
    return {
        "processed": len(ingested_ids),
        "ticketIds": ingested_ids,
        "highRisk": high_risk,
        "missingApprovals": missing_approvals,
        "slaIssues": sla_issues,
    }


def parse_uploaded_tickets(filename: str, content_bytes: bytes) -> list[dict[str, Any]]:
    text = content_bytes.decode("utf-8-sig")
    if filename.lower().endswith(".json") or text.lstrip().startswith("[") or text.lstrip().startswith("{"):
        parsed = json.loads(text)
        if isinstance(parsed, dict) and "tickets" in parsed:
            return list(parsed["tickets"])
        if isinstance(parsed, list):
            return parsed
        return [parsed]
    reader = csv.DictReader(io.StringIO(text))
    return [dict(row) for row in reader if any(v.strip() for v in row.values() if isinstance(v, str))]
