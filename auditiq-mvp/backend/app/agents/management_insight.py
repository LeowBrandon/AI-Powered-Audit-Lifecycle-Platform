"""Agent 9 — Management Insight Agent (Proposal Section 4 Page 15, Section 14 & Section 25).

Synthesizes business-level intelligence directly from live database audit records:
compliance trends, top risk areas, top root causes, department / business unit
performance, proactive prevention metrics, and executive narratives.
"""

from __future__ import annotations

import sqlite3
from collections import Counter, defaultdict
from typing import Any


class ManagementInsightAgent:
    """Produces dynamic executive summaries and operational intelligence from live audit data."""

    def generate_analytics(self, conn: sqlite3.Connection) -> dict[str, Any]:
        rows = [
            dict(r)
            for r in conn.execute(
                """
                SELECT t.ticket_id, t.ticket_type, t.assignment_group, t.business_unit,
                       t.status AS ticket_status, t.sla_status, t.created_at,
                       a.audit_id, a.audit_score, a.risk_score, a.risk_band,
                       a.decision, a.sampling_tier, a.status AS audit_status,
                       a.audit_duration_min, a.ai_confidence
                FROM tickets t
                JOIN audits a ON a.ticket_id = t.ticket_id
                """
            ).fetchall()
        ]
        findings = [
            dict(f)
            for f in conn.execute(
                "SELECT criterion_name, severity, status, ticket_id FROM findings WHERE status != 'Resolved'"
            ).fetchall()
        ]
        alerts = [
            dict(al)
            for al in conn.execute("SELECT status, severity FROM monitoring_alerts").fetchall()
        ]
        feedback_cnt = conn.execute("SELECT COUNT(*) AS c FROM feedback").fetchone()["c"]

        total = len(rows) or 1
        avg_compliance = round(sum(r["audit_score"] for r in rows) / total, 1)
        high_critical = sum(1 for r in rows if r["risk_band"] in {"HIGH", "CRITICAL"})
        sla_violations = sum(1 for r in rows if r["sla_status"] in {"At Risk", "Breached"})
        auto_audited = sum(1 for r in rows if r["sampling_tier"] == "Automated Audit")
        auto_pct = round((auto_audited / total) * 100.0, 1)
        avg_audit_min = round(sum(r["audit_duration_min"] for r in rows) / total, 1)

        # Compliance by Ticket Type
        type_groups: dict[str, list[float]] = defaultdict(list)
        dept_groups: dict[str, list[float]] = defaultdict(list)
        bu_groups: dict[str, list[float]] = defaultdict(list)
        month_groups: dict[str, list[float]] = defaultdict(list)
        risk_counts = Counter(r["risk_band"] for r in rows)
        sampling_counts = Counter(r["sampling_tier"] for r in rows)

        for r in rows:
            type_groups[r["ticket_type"]].append(r["audit_score"])
            dept_groups[r["assignment_group"]].append(r["audit_score"])
            bu_groups[r["business_unit"]].append(r["audit_score"])
            ym = (r["created_at"] or "2026-09")[:7]
            month_groups[ym].append(r["audit_score"])

        ticket_type_stats = [
            {
                "label": t_type,
                "value": round(sum(vals) / len(vals), 1) if vals else 0.0,
                "count": len(vals),
            }
            for t_type in ("INC", "SR", "CR")
            for vals in [type_groups.get(t_type, [])]
        ]

        dept_stats = sorted(
            [
                {
                    "label": dept,
                    "value": round(sum(vals) / len(vals), 1),
                    "count": len(vals),
                    "highRisk": sum(
                        1
                        for r in rows
                        if r["assignment_group"] == dept and r["risk_band"] in {"HIGH", "CRITICAL"}
                    ),
                }
                for dept, vals in dept_groups.items()
            ],
            key=lambda x: x["value"],
        )

        bu_stats = sorted(
            [
                {
                    "label": bu,
                    "value": round(sum(vals) / len(vals), 1),
                    "count": len(vals),
                }
                for bu, vals in bu_groups.items()
            ],
            key=lambda x: x["value"],
        )

        # Normalize failure categories (Proposal Page 25)
        cat_counts: Counter[str] = Counter()
        for f in findings:
            cname = f["criterion_name"].lower()
            if "approval" in cname or "authorization" in cname:
                cat_counts["Missing approval"] += 1
            elif "rollback" in cname or "documentation" in cname or "root cause" in cname or "resolution" in cname or "implementation" in cname:
                cat_counts["Incomplete documentation"] += 1
            elif "categor" in cname or "classification" in cname or "priority" in cname:
                cat_counts["Incorrect categorization"] += 1
            elif "sla" in cname:
                cat_counts["SLA violations"] += 1
            elif "validation" in cname or "post-implementation" in cname or "testing" in cname:
                cat_counts["Missing validation"] += 1
            else:
                cat_counts["Other governance gaps"] += 1

        total_failures = sum(cat_counts.values()) or 1
        failure_categories = [
            {
                "label": label,
                "count": count,
                "value": round((count / total_failures) * 100.0, 1),
            }
            for label, count in cat_counts.most_common(6)
        ]

        # Monthly compliance trend
        month_names = {
            "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr", "05": "May", "06": "Jun",
            "07": "Jul", "08": "Aug", "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec",
        }
        trend = []
        for ym in sorted(month_groups.keys())[-6:]:
            vals = month_groups[ym]
            m_label = month_names.get(ym[5:7], ym)
            trend.append(
                {
                    "period": ym,
                    "month": m_label,
                    "value": round(sum(vals) / len(vals), 1),
                    "count": len(vals),
                }
            )

        trend_delta = (
            round(trend[-1]["value"] - trend[0]["value"], 1) if len(trend) >= 2 else 0.0
        )

        # Executive Narrative (Proposal Page 15)
        lowest_type = min(
            (x for x in ticket_type_stats if x["count"] > 0),
            key=lambda x: x["value"],
            default={"label": "CR", "value": avg_compliance},
        )
        lowest_dept = dept_stats[0] if dept_stats else {"label": "Infrastructure", "value": avg_compliance}
        top_root_cause = failure_categories[0]["label"] if failure_categories else "None detected"
        top_risk_area = (
            "Change Management"
            if lowest_type["label"] == "CR"
            else "Incident Management"
            if lowest_type["label"] == "INC"
            else "Service Request Fulfillment"
        )
        active_preclosure_alerts = sum(1 for al in alerts if al["status"] == "Active")
        resolved_alerts = sum(1 for al in alerts if al["status"] == "Resolved")

        narrative = (
            f"Overall compliance across {len(rows)} audited demo tickets stands at {avg_compliance}% "
            f"({'up' if trend_delta >= 0 else 'down'} {abs(trend_delta)}% across the reporting window). "
            f"{top_risk_area} ({lowest_type['label']} at {lowest_type['value']}%) and the {lowest_dept['label']} "
            f"group ({lowest_dept['value']}%) represent the highest compliance exposure, driven primarily by "
            f"{top_root_cause.lower()}."
        )

        # Target KPIs (Proposal Section 25 Page 38 — clearly framed as target KPIs vs demo metrics)
        target_kpis = [
            {
                "category": "Efficiency",
                "metric": "Average Audit Time",
                "before": "20–30 min",
                "target": "<5–10 min",
                "demoCurrent": f"{avg_audit_min} min",
            },
            {
                "category": "Automation",
                "metric": "% Automatically Audited",
                "before": "0% (Manual)",
                "target": "70–90%",
                "demoCurrent": f"{auto_pct}%",
            },
            {
                "category": "Proactive Detection",
                "metric": "Pre-Closure Issues Caught",
                "before": "0% (Post-closure only)",
                "target": "Increasing over time",
                "demoCurrent": f"{active_preclosure_alerts} active / {resolved_alerts} remediated",
            },
            {
                "category": "Quality",
                "metric": "Closed-Loop Feedback Captured",
                "before": "Ad-hoc spreadsheets",
                "target": "Continuous tuning",
                "demoCurrent": f"{feedback_cnt} overrides logged",
            },
            {
                "category": "Management",
                "metric": "Overall Compliance Rate",
                "before": "Sampled visibility",
                "target": ">95% sustained",
                "demoCurrent": f"{avg_compliance}%",
            },
        ]

        return {
            "summary": {
                "ticketsAudited": len(rows),
                "complianceRate": avg_compliance,
                "highRiskTickets": high_critical,
                "slaViolations": sla_violations,
                "approvalViolations": cat_counts.get("Missing approval", 0),
                "documentationIssues": cat_counts.get("Incomplete documentation", 0),
                "trendDelta": trend_delta,
                "topRiskArea": top_risk_area,
                "topRootCause": top_root_cause,
                "narrative": narrative,
            },
            "ticketType": ticket_type_stats,
            "department": dept_stats,
            "businessUnit": bu_stats,
            "failureCategories": failure_categories,
            "trend": trend,
            "riskDistribution": {
                "CRITICAL": risk_counts.get("CRITICAL", 0),
                "HIGH": risk_counts.get("HIGH", 0),
                "MEDIUM": risk_counts.get("MEDIUM", 0),
                "LOW": risk_counts.get("LOW", 0),
            },
            "samplingDistribution": [
                {"tier": "Automated Audit", "risk": "Low Risk", "count": sampling_counts.get("Automated Audit", 0)},
                {"tier": "Sampled Review", "risk": "Medium Risk", "count": sampling_counts.get("Sampled Review", 0)},
                {"tier": "Mandatory Audit", "risk": "High Risk", "count": sampling_counts.get("Mandatory Audit", 0)},
                {"tier": "Immediate Escalation", "risk": "Critical", "count": sampling_counts.get("Immediate Escalation", 0)},
            ],
            "targetKpis": target_kpis,
        }
