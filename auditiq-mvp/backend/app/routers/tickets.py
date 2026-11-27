"""Tickets, Filterable Audit Queue, Findings Actions, Remediation & Ingestion API."""

from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.database import db_session
from app.schemas import FindingActionRequest, RemediationRequest, TicketCreate
from app.services.audit_service import (
    apply_finding_action,
    apply_ticket_remediation,
    get_ticket_detail,
    ingest_ticket_records,
    parse_uploaded_tickets,
    run_ticket_audit,
    utc_now,
)

router = APIRouter(prefix="/api", tags=["Tickets & Audit Queue"])


@router.get("/tickets")
def list_tickets(
    ticket_type: str | None = Query(default=None),
    risk: str | None = Query(default=None),
    business_unit: str | None = Query(default=None),
    assignment_group: str | None = Query(default=None),
    auditor: str | None = Query(default=None),
    audit_status: str | None = Query(default=None),
    violation_type: str | None = Query(default=None),
    confidence_tier: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    search: str | None = Query(default=None),
    only_attention: bool = Query(default=False),
):
    """Returns audit queue with all 9 Proposal Section 9 filters + auditor workload."""
    with db_session() as conn:
        clauses: list[str] = ["1 = 1"]
        params: list[Any] = []

        if ticket_type and ticket_type != "ALL":
            clauses.append("t.ticket_type = ?")
            params.append(ticket_type)
        if risk and risk != "ALL":
            clauses.append("a.risk_band = ?")
            params.append(risk)
        if business_unit and business_unit != "ALL":
            clauses.append("t.business_unit = ?")
            params.append(business_unit)
        if assignment_group and assignment_group != "ALL":
            clauses.append("t.assignment_group = ?")
            params.append(assignment_group)
        if auditor and auditor != "ALL":
            clauses.append("a.auditor = ?")
            params.append(auditor)
        if audit_status and audit_status != "ALL":
            clauses.append("a.status = ?")
            params.append(audit_status)
        if date_from:
            clauses.append("SUBSTR(t.created_at, 1, 10) >= ?")
            params.append(date_from[:10])
        if date_to:
            clauses.append("SUBSTR(t.created_at, 1, 10) <= ?")
            params.append(date_to[:10])
        if search:
            like = f"%{search.strip().lower()}%"
            clauses.append(
                "(LOWER(t.ticket_id) LIKE ? OR LOWER(t.short_description) LIKE ? OR LOWER(t.assignment_group) LIKE ?)"
            )
            params.extend([like, like, like])
        if only_attention:
            clauses.append("a.status IN ('Needs Review', 'Escalated', 'In Review', 'Evidence Requested')")
        if confidence_tier and confidence_tier != "ALL":
            if confidence_tier == "AUTO":
                clauses.append("a.ai_confidence >= 95")
            elif confidence_tier == "RECOMMEND":
                clauses.append("a.ai_confidence >= 80 AND a.ai_confidence < 95")
            elif confidence_tier == "REVIEW":
                clauses.append("a.ai_confidence < 80")
        if violation_type and violation_type != "ALL":
            clauses.append(
                """
                EXISTS (
                    SELECT 1 FROM findings f
                    WHERE f.audit_id = a.audit_id
                      AND f.status != 'Resolved'
                      AND LOWER(f.criterion_name) LIKE ?
                )
                """
            )
            params.append(f"%{violation_type.lower()}%")

        sql = f"""
            SELECT t.ticket_id, t.ticket_type, t.short_description, t.priority,
                   t.category, t.business_unit, t.assignment_group, t.owner,
                   t.status AS ticket_status, t.sla_status, t.created_at,
                   a.audit_id, a.audit_score, a.risk_score, a.risk_band,
                   a.decision, a.sampling_tier, a.ai_confidence, a.status AS audit_status,
                   a.auditor, a.qc_status, a.predicted_failure_prob,
                   (SELECT COUNT(*) FROM findings f WHERE f.audit_id = a.audit_id AND f.status IN ('Open', 'Evidence Requested')) AS open_findings,
                   (SELECT GROUP_CONCAT(f.criterion_name, ', ') FROM findings f WHERE f.audit_id = a.audit_id AND f.status != 'Resolved') AS violations
            FROM tickets t
            JOIN audits a ON a.ticket_id = t.ticket_id
            WHERE {' AND '.join(clauses)}
            ORDER BY
                CASE a.risk_band WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END,
                a.risk_score DESC,
                t.created_at DESC
        """
        rows = conn.execute(sql, params).fetchall()

        # Filter facets & auditor workload summary (from full dataset)
        facets = {
            "businessUnits": [
                r["business_unit"]
                for r in conn.execute("SELECT DISTINCT business_unit FROM tickets ORDER BY business_unit").fetchall()
            ],
            "assignmentGroups": [
                r["assignment_group"]
                for r in conn.execute("SELECT DISTINCT assignment_group FROM tickets ORDER BY assignment_group").fetchall()
            ],
            "auditors": [
                r["auditor"]
                for r in conn.execute("SELECT DISTINCT auditor FROM audits WHERE auditor != 'Unassigned' ORDER BY auditor").fetchall()
            ],
            "auditStatuses": [
                r["status"]
                for r in conn.execute("SELECT DISTINCT status FROM audits ORDER BY status").fetchall()
            ],
            "violationTypes": [
                r["criterion_name"]
                for r in conn.execute(
                    "SELECT DISTINCT criterion_name FROM findings WHERE status != 'Resolved' ORDER BY criterion_name"
                ).fetchall()
            ],
        }

        workload = [
            dict(w)
            for w in conn.execute(
                """
                SELECT auditor,
                       COUNT(*) AS total,
                       SUM(CASE WHEN status IN ('Needs Review', 'Escalated', 'In Review', 'Evidence Requested') THEN 1 ELSE 0 END) AS pending,
                       SUM(CASE WHEN risk_band IN ('CRITICAL', 'HIGH') THEN 1 ELSE 0 END) AS highRisk
                FROM audits
                WHERE auditor != 'Unassigned'
                GROUP BY auditor
                ORDER BY pending DESC, total DESC
                """
            ).fetchall()
        ]

        items = [
            {
                "id": r["ticket_id"],
                "type": r["ticket_type"],
                "shortDescription": r["short_description"],
                "priority": r["priority"],
                "category": r["category"],
                "businessUnit": r["business_unit"],
                "assignmentGroup": r["assignment_group"],
                "owner": r["owner"],
                "state": r["ticket_status"],
                "sla": r["sla_status"],
                "createdAt": r["created_at"],
                "auditId": r["audit_id"],
                "compliance": r["audit_score"],
                "risk": r["risk_score"],
                "riskBand": r["risk_band"],
                "decision": r["decision"],
                "samplingTier": r["sampling_tier"],
                "confidence": r["ai_confidence"],
                "auditStatus": r["audit_status"],
                "auditor": r["auditor"],
                "qcStatus": r["qc_status"],
                "predictedFailureProb": r["predicted_failure_prob"],
                "openFindings": r["open_findings"] or 0,
                "violations": r["violations"] or "",
            }
            for r in rows
        ]

        return {
            "items": items,
            "total": len(items),
            "facets": facets,
            "workload": workload,
        }


@router.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str):
    with db_session() as conn:
        try:
            return get_ticket_detail(conn, ticket_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/tickets", status_code=201)
def create_ticket(payload: TicketCreate):
    with db_session() as conn:
        now = utc_now()
        tid = payload.ticket_id.strip().upper() if payload.ticket_id else f"{payload.ticket_type}{uuid.uuid4().hex[:6].upper()}"
        exists = conn.execute("SELECT 1 FROM tickets WHERE ticket_id = ?", (tid,)).fetchone()
        if exists:
            raise HTTPException(status_code=409, detail=f"Ticket {tid} already exists.")

        notes = [
            {
                "timestamp": n.timestamp or now[11:16],
                "author": n.author,
                "text": n.text,
            }
            for n in payload.work_notes
        ]
        approvals = [
            {
                "type": a.type,
                "approver": a.approver,
                "status": a.status,
                "timestamp": now,
                "note": a.note,
            }
            for a in payload.approvals
        ]
        attachments = [a.model_dump() for a in payload.attachments]

        conn.execute(
            """
            INSERT INTO tickets (
                ticket_id, ticket_type, short_description, description, priority, category,
                business_unit, assignment_group, requester, owner, resolver, status,
                sla_status, closure_code, resolution, work_notes_json, approvals_json,
                attachments_json, related_tickets_json, target_window,
                historical_group_risk, previous_audit_issues, created_at, updated_at, closed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tid,
                payload.ticket_type,
                payload.short_description,
                payload.description,
                payload.priority,
                payload.category,
                payload.business_unit,
                payload.assignment_group,
                payload.requester,
                payload.owner,
                payload.resolver or payload.owner,
                payload.status,
                payload.sla_status,
                payload.closure_code,
                payload.resolution,
                json.dumps(notes),
                json.dumps(approvals),
                json.dumps(attachments),
                json.dumps(payload.related_tickets),
                payload.target_window,
                10.0,
                0,
                now,
                now,
                now if payload.status == "Closed" else None,
            ),
        )
        detail = run_ticket_audit(conn, tid, actor="ITSM Intake Pipeline", broadcast=True)
        return {"message": f"Ticket {tid} ingested and audited by 6-agent pipeline.", "ticket": detail}


@router.post("/tickets/upload")
async def upload_tickets(file: UploadFile = File(...)):
    """Uploads CSV or JSON ticket dataset and runs automated multi-agent audits."""
    raw = await file.read()
    try:
        records = parse_uploaded_tickets(file.filename or "tickets.json", raw)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse ticket file: {exc}") from exc
    if not records:
        raise HTTPException(status_code=400, detail="Uploaded file contained no ticket rows.")

    with db_session() as conn:
        result = ingest_ticket_records(conn, records[:200], actor=f"File Upload ({file.filename})")
        return {
            "message": f"Ingested and audited {result['processed']} tickets from {file.filename}.",
            **result,
        }


@router.post("/tickets/batch-audit")
def batch_audit_all():
    """Re-evaluates every ticket in the database through the Multi-Agent Orchestrator."""
    with db_session() as conn:
        rows = conn.execute("SELECT ticket_id FROM tickets").fetchall()
        high_risk = 0
        for row in rows:
            detail = run_ticket_audit(conn, row["ticket_id"], actor="Batch Audit Runner", broadcast=False)
            if detail["riskBand"] in {"HIGH", "CRITICAL"}:
                high_risk += 1
        return {
            "message": f"Re-audited {len(rows)} tickets across active governance rules.",
            "processed": len(rows),
            "highRisk": high_risk,
        }


@router.post("/tickets/{ticket_id}/remediate")
def remediate_ticket(ticket_id: str, payload: RemediationRequest):
    with db_session() as conn:
        try:
            return apply_ticket_remediation(
                conn,
                ticket_id,
                action_type=payload.action_type,
                actor=payload.actor,
                role=payload.role,
                approver=payload.approver,
                note=payload.note,
                closure_code=payload.closure_code,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/tickets/{ticket_id}/approve-business")
def approve_business_compat(ticket_id: str):
    """Backward-compatible endpoint from prototype for quick business approval upload."""
    with db_session() as conn:
        try:
            return apply_ticket_remediation(
                conn,
                ticket_id,
                action_type="business_approval",
                actor="Business Owner",
                role="Auditor",
                approver="VP Finance Applications",
                note="Business owner approval uploaded and timestamped prior to production implementation.",
                closure_code="",
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/reanalyze/{ticket_id}")
def reanalyze_ticket(ticket_id: str):
    with db_session() as conn:
        try:
            detail = run_ticket_audit(conn, ticket_id, actor="Manual Re-Audit", actor_role="Auditor", broadcast=True)
            return {"message": f"Multi-agent audit re-evaluated {ticket_id}.", "ticket": detail}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/tickets/{ticket_id}/findings/{finding_id}/action")
def finding_action(ticket_id: str, finding_id: str, payload: FindingActionRequest):
    with db_session() as conn:
        try:
            return apply_finding_action(
                conn,
                ticket_id,
                finding_id,
                decision=payload.decision,
                note=payload.note,
                auditor=payload.auditor,
                role=payload.role,
                improvement_target=payload.improvement_target,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/audit-trail")
def get_global_audit_trail(limit: int = Query(default=40, ge=5, le=200)):
    with db_session() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_trail ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {
                "trailId": r["trail_id"],
                "ticketId": r["ticket_id"],
                "auditId": r["audit_id"],
                "who": r["who"],
                "role": r["role"],
                "what": r["what"],
                "timestamp": r["timestamp"],
                "rule": r["rule"],
                "evidence": r["evidence"],
                "aiModel": r["ai_model"],
                "confidence": r["confidence"],
                "decision": r["decision"],
                "humanOverride": bool(r["human_override"]),
            }
            for r in rows
        ]
