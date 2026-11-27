"""Agent 8 — QC Intelligence Agent (Proposal Section 4 Page 14 & Section 24 Closed-Loop Learning).

Analyzes auditor consistency, scoring variance, outlier patterns, AI-human
agreement, disputed decisions, and low-confidence AI reviews so QC reviewers
focus on high-impact exceptions rather than checking every audit equally.
"""

from __future__ import annotations

import math
import sqlite3
from typing import Any


class QCIntelligenceAgent:
    """Computes live QC metrics, auditor variance, exception queues, and closed-loop feedback stats."""

    def analyze(self, conn: sqlite3.Connection) -> dict[str, Any]:
        audits = [
            dict(r)
            for r in conn.execute(
                """
                SELECT a.*, t.short_description, t.assignment_group, t.priority, t.status AS ticket_status
                FROM audits a
                JOIN tickets t ON t.ticket_id = a.ticket_id
                ORDER BY a.risk_score DESC
                """
            ).fetchall()
        ]
        feedback_rows = [
            dict(r)
            for r in conn.execute("SELECT * FROM feedback ORDER BY created_at DESC").fetchall()
        ]
        findings_rows = [
            dict(r)
            for r in conn.execute("SELECT * FROM findings").fetchall()
        ]
        cfg = conn.execute("SELECT confidence_recommend FROM governance_config WHERE id = 1").fetchone()
        conf_rec = int(cfg["confidence_recommend"]) if cfg else 80

        # Group audits by assigned auditor
        auditor_map: dict[str, list[dict[str, Any]]] = {}
        for a in audits:
            name = a["auditor"]
            if name and name != "Unassigned":
                auditor_map.setdefault(name, []).append(a)

        feedback_by_auditor: dict[str, int] = {}
        for fb in feedback_rows:
            feedback_by_auditor[fb["auditor"]] = feedback_by_auditor.get(fb["auditor"], 0) + 1

        global_scores = [a["audit_score"] for a in audits] or [90.0]
        global_mean = sum(global_scores) / len(global_scores)

        auditor_stats: list[dict[str, Any]] = []
        for name, items in sorted(auditor_map.items()):
            n = len(items)
            overrides = feedback_by_auditor.get(name, 0)
            disputed_cnt = sum(1 for x in items if x["qc_status"] == "Disputed")
            agreement = round(max(68.0, min(99.5, ((max(n, 1) - overrides * 0.85) / max(n, 1)) * 100.0)), 1)
            mean_score = sum(x["audit_score"] for x in items) / n
            # Scoring variance blends deviation from fleet average and override frequency
            spread = math.sqrt(sum((x["audit_score"] - mean_score) ** 2 for x in items) / n)
            variance = round(min(18.5, abs(mean_score - global_mean) * 0.45 + (overrides / max(n, 1)) * 14.0 + spread * 0.12), 1)
            status = "OUTLIER" if (variance >= 10.0 or agreement < 88.0) else "REVIEW" if disputed_cnt > 0 else "STABLE"
            auditor_stats.append(
                {
                    "name": name,
                    "audits": n,
                    "avgScore": round(mean_score, 1),
                    "overrides": overrides,
                    "disputed": disputed_cnt,
                    "agreement": agreement,
                    "variance": variance,
                    "status": status,
                }
            )

        auditor_stats.sort(key=lambda x: x["variance"], reverse=True)

        avg_variance = (
            round(sum(a["variance"] for a in auditor_stats) / len(auditor_stats), 1)
            if auditor_stats
            else 0.0
        )
        avg_agreement = (
            round(sum(a["agreement"] for a in auditor_stats) / len(auditor_stats), 1)
            if auditor_stats
            else 95.0
        )
        disputed_total = sum(1 for a in audits if a["qc_status"] == "Disputed")

        # Identify targeted QC exceptions (PDF Page 14)
        exceptions: list[dict[str, Any]] = []
        overridden_audit_ids = {fb["audit_id"] for fb in feedback_rows}
        low_conf_audit_ids = {
            f["audit_id"] for f in findings_rows if f["confidence"] < conf_rec and f["status"] != "Resolved"
        }

        for a in audits:
            reasons: list[str] = []
            if a["qc_status"] == "Disputed":
                reasons.append("Disputed QC finding")
            if a["audit_id"] in overridden_audit_ids:
                reasons.append("AI-human override recorded")
            if a["audit_id"] in low_conf_audit_ids or a["ai_confidence"] < conf_rec:
                reasons.append(f"Low AI confidence ({int(a['ai_confidence'])}%)")
            if a["risk_band"] == "CRITICAL":
                reasons.append("Critical-risk mandatory QC check")

            if reasons:
                exceptions.append(
                    {
                        "auditId": a["audit_id"],
                        "ticketId": a["ticket_id"],
                        "ticketType": a["audit_type"],
                        "shortDescription": a["short_description"],
                        "assignmentGroup": a["assignment_group"],
                        "auditor": a["auditor"],
                        "auditScore": a["audit_score"],
                        "riskScore": a["risk_score"],
                        "riskBand": a["risk_band"],
                        "aiConfidence": a["ai_confidence"],
                        "qcStatus": a["qc_status"],
                        "qcReviewer": a["qc_reviewer"],
                        "qcNote": a["qc_note"],
                        "exceptionReasons": reasons,
                    }
                )

        focus_buckets = [
            {
                "title": "Low-Confidence AI Decisions",
                "count": sum(1 for e in exceptions if any("Low AI confidence" in r for r in e["exceptionReasons"])),
                "description": f"AI findings below {conf_rec}% confidence routed for human confirmation.",
            },
            {
                "title": "AI-Human Disagreements",
                "count": len(feedback_rows),
                "description": "Auditor overrides captured into Closed-Loop Learning feedback store.",
            },
            {
                "title": "Disputed QC Outcomes",
                "count": disputed_total,
                "description": "Audits flagged by QC Reviewers for inconsistency or scoring re-calibration.",
            },
            {
                "title": "Outlier Auditors",
                "count": sum(1 for s in auditor_stats if s["status"] == "OUTLIER"),
                "description": "Auditors exhibiting elevated scoring variance vs. governance baseline.",
            },
        ]

        return {
            "auditorVariance": avg_variance,
            "disputed": disputed_total,
            "aiHumanAgreement": avg_agreement,
            "exceptionsCount": len(exceptions),
            "feedbackCount": len(feedback_rows),
            "auditors": auditor_stats,
            "exceptions": exceptions[:15],
            "focusBuckets": focus_buckets,
            "feedbackLoop": feedback_rows[:25],
        }
