"""Real-Time Continuous Monitoring & Predictive Audit API (Sections 13 & 15)."""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import db_session, parse_json_col
from app.services.audit_service import run_ticket_audit, utc_now
from app.services.websocket_manager import ws_manager

router = APIRouter(prefix="/api/monitoring", tags=["Live Monitoring & Predictive Audit"])


class AlertStatusUpdate(BaseModel):
    status: str  # "Acknowledged" | "Resolved"


@router.get("")
def get_live_monitoring():
    with db_session() as conn:
        active_tickets = [
            dict(r)
            for r in conn.execute(
                """
                SELECT t.ticket_id, t.ticket_type, t.short_description, t.priority,
                       t.assignment_group, t.business_unit, t.status AS ticket_status,
                       t.sla_status, t.target_window,
                       a.audit_score, a.risk_score, a.risk_band,
                       a.predicted_failure_prob, a.predictive_factors_json, a.ai_summary
                FROM tickets t
                JOIN audits a ON a.ticket_id = t.ticket_id
                WHERE t.status IN ('In Progress', 'Pending Approval', 'Scheduled')
                ORDER BY a.predicted_failure_prob DESC, a.risk_score DESC
                """
            ).fetchall()
        ]

        risk_summary = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        predictive_list = []
        for t in active_tickets:
            risk_summary[t["risk_band"]] = risk_summary.get(t["risk_band"], 0) + 1
            predictive_list.append(
                {
                    "ticketId": t["ticket_id"],
                    "ticketType": t["ticket_type"],
                    "shortDescription": t["short_description"],
                    "priority": t["priority"],
                    "assignmentGroup": t["assignment_group"],
                    "state": t["ticket_status"],
                    "sla": t["sla_status"],
                    "targetWindow": t["target_window"],
                    "compliance": t["audit_score"],
                    "riskScore": t["risk_score"],
                    "riskBand": t["risk_band"],
                    "predictedAuditRisk": t["predicted_failure_prob"],
                    "factors": parse_json_col(t["predictive_factors_json"], []),
                    "summary": t["ai_summary"],
                }
            )

        alerts = [
            {
                "alertId": r["alert_id"],
                "ticketId": r["ticket_id"],
                "ticketType": r["ticket_type"],
                "shortDescription": r["short_description"],
                "assignmentGroup": r["assignment_group"],
                "ticketState": r["ticket_status"],
                "severity": r["severity"],
                "title": r["title"],
                "message": r["message"],
                "recommendation": r["recommendation"],
                "predictedRisk": r["predicted_risk"],
                "status": r["status"],
                "createdAt": r["created_at"],
            }
            for r in conn.execute(
                """
                SELECT m.*, t.ticket_type, t.short_description, t.assignment_group, t.status AS ticket_status
                FROM monitoring_alerts m
                JOIN tickets t ON t.ticket_id = m.ticket_id
                WHERE m.status IN ('Active', 'Acknowledged')
                ORDER BY CASE m.severity WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END,
                         m.predicted_risk DESC
                """
            ).fetchall()
        ]

        resolved_count = conn.execute(
            "SELECT COUNT(*) AS c FROM monitoring_alerts WHERE status = 'Resolved'"
        ).fetchone()["c"]

        return {
            "activeTicketCount": len(active_tickets),
            "riskSummary": risk_summary,
            "alerts": alerts,
            "resolvedAlertsCount": resolved_count,
            "predictiveAudits": predictive_list,
            "wsClients": ws_manager.active_connections,
            "recentEvents": ws_manager.recent_events[-12:],
        }


@router.post("/alerts/{alert_id}/status")
def update_alert_status(alert_id: str, payload: AlertStatusUpdate):
    if payload.status not in {"Acknowledged", "Resolved"}:
        raise HTTPException(status_code=400, detail="Status must be Acknowledged or Resolved.")
    with db_session() as conn:
        row = conn.execute("SELECT * FROM monitoring_alerts WHERE alert_id = ?", (alert_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Alert not found.")
        now = utc_now()
        conn.execute(
            "UPDATE monitoring_alerts SET status = ?, resolved_at = ? WHERE alert_id = ?",
            (payload.status, now if payload.status == "Resolved" else None, alert_id),
        )
        ws_manager.broadcast_sync(
            "alert_status_changed",
            {"alertId": alert_id, "ticketId": row["ticket_id"], "status": payload.status},
        )
        return {"message": f"Alert marked {payload.status}.", "alertId": alert_id, "status": payload.status}


@router.post("/simulate")
def simulate_live_event():
    """Simulates an incoming high-risk ITSM change ticket to demonstrate real-time Agent 6 alerting."""
    now = utc_now()
    tid = f"CR{uuid.uuid4().hex[:5].upper()}"
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO tickets (
                ticket_id, ticket_type, short_description, description, priority, category,
                business_unit, assignment_group, requester, owner, resolver, status,
                sla_status, closure_code, resolution, work_notes_json, approvals_json,
                attachments_json, related_tickets_json, target_window,
                historical_group_risk, previous_audit_issues, created_at, updated_at
            ) VALUES (?, 'CR', ?, ?, 'P1', 'Security', 'Digital Channels', 'Security',
                      'ITSM Webhook', 'Security Operations', 'Live Ops', 'Scheduled',
                      'At Risk', '', '', ?, ?, ?, '[]', 'Tonight 23:00 UTC', 14.0, 2, ?, ?)
            """,
            (
                tid,
                "Emergency WAF & API rate-limit policy change — production ingress",
                "Urgent production ingress security policy adjustment scheduled ahead of peak traffic event.",
                json.dumps(
                    [
                        {
                            "timestamp": now[11:16],
                            "author": "Security Ops",
                            "text": "Implementation scheduled soon for 23:00 UTC. Business approval pending and no rollback plan detected.",
                        }
                    ]
                ),
                json.dumps(
                    [
                        {
                            "type": "Technical",
                            "approver": "SecOps Duty Lead",
                            "status": "Approved",
                            "timestamp": now,
                            "note": "Rule syntax checked.",
                        }
                    ]
                ),
                json.dumps(
                    [
                        {
                            "name": "WAF Risk Assessment.pdf",
                            "section": "Section 1",
                            "content_summary": "High-impact ingress risk assessment logged.",
                        }
                    ]
                ),
                now,
                now,
            ),
        )
        detail = run_ticket_audit(conn, tid, actor="ITSM Live Webhook", actor_role="AI Agent", broadcast=True)
        return {
            "message": f"Simulated incoming live ticket {tid} — Monitoring Agent detected proactive compliance risk.",
            "ticket": detail,
        }
