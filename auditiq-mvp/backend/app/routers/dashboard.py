"""Executive Dashboard API (Proposal Section 8 & Screen 1)."""

from __future__ import annotations

from fastapi import APIRouter

from app.agents.management_insight import ManagementInsightAgent
from app.database import db_session

router = APIRouter(prefix="/api", tags=["Dashboard"])
insight_agent = ManagementInsightAgent()


@router.get("/dashboard")
def get_dashboard():
    with db_session() as conn:
        analytics = insight_agent.generate_analytics(conn)
        summary = analytics["summary"]

        total = summary["ticketsAudited"] or 1
        auto_closed = conn.execute(
            "SELECT COUNT(*) AS c FROM audits WHERE sampling_tier = 'Automated Audit'"
        ).fetchone()["c"]
        completed_or_auto = conn.execute(
            "SELECT COUNT(*) AS c FROM audits WHERE status IN ('Auto-Closed', 'Approved')"
        ).fetchone()["c"]
        active_alerts = [
            dict(r)
            for r in conn.execute(
                """
                SELECT m.alert_id, m.ticket_id, m.severity, m.title, m.message,
                       m.recommendation, m.predicted_risk, m.status, m.created_at,
                       t.ticket_type, t.short_description, t.assignment_group
                FROM monitoring_alerts m
                JOIN tickets t ON t.ticket_id = m.ticket_id
                WHERE m.status IN ('Active', 'Acknowledged')
                ORDER BY CASE m.severity WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END,
                         m.predicted_risk DESC
                LIMIT 6
                """
            ).fetchall()
        ]
        avg_time = conn.execute(
            "SELECT ROUND(AVG(audit_duration_min), 1) AS avg_t FROM audits"
        ).fetchone()["avg_t"] or 4.8

        return {
            "total": summary["ticketsAudited"],
            "auditCompletion": round((completed_or_auto / total) * 100.0, 1),
            "compliance": summary["complianceRate"],
            "highRisk": summary["highRiskTickets"],
            "aiAlerts": len(active_alerts),
            "avgAuditTime": avg_time,
            "autoAudited": round((auto_closed / total) * 100.0, 1),
            "riskDistribution": analytics["riskDistribution"],
            "samplingDistribution": analytics["samplingDistribution"],
            "trend": analytics["trend"],
            "trendDelta": summary["trendDelta"],
            "managementInsight": {
                "narrative": summary["narrative"],
                "topRiskArea": summary["topRiskArea"],
                "topRootCause": summary["topRootCause"],
                "slaViolations": summary["slaViolations"],
                "approvalViolations": summary["approvalViolations"],
                "documentationIssues": summary["documentationIssues"],
            },
            "recentAlerts": active_alerts,
            "isDemoData": True,
        }
