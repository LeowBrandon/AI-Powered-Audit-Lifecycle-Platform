"""QC Intelligence & Closed-Loop Learning API (Proposal Section 4 Agent 8 & Section 24)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.agents.qc_intelligence import QCIntelligenceAgent
from app.database import db_session
from app.schemas import FeedbackStatusUpdate, QCReviewRequest
from app.services.audit_service import log_audit_trail, utc_now

router = APIRouter(prefix="/api/qc", tags=["QC Intelligence & Closed-Loop Learning"])
qc_agent = QCIntelligenceAgent()


@router.get("")
def get_qc_dashboard():
    with db_session() as conn:
        return qc_agent.analyze(conn)


@router.post("/reviews/{audit_id}")
def submit_qc_review(audit_id: str, payload: QCReviewRequest):
    with db_session() as conn:
        row = conn.execute("SELECT * FROM audits WHERE audit_id = ?", (audit_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Audit {audit_id} not found.")
        now = utc_now()
        new_audit_status = "QC Disputed" if payload.qc_status == "Disputed" else "Approved"
        conn.execute(
            """
            UPDATE audits
            SET qc_status = ?, qc_reviewer = ?, qc_note = ?, status = ?, updated_at = ?
            WHERE audit_id = ?
            """,
            (payload.qc_status, payload.qc_reviewer, payload.qc_note, new_audit_status, now, audit_id),
        )
        log_audit_trail(
            conn,
            ticket_id=row["ticket_id"],
            audit_id=audit_id,
            who=payload.qc_reviewer,
            role="QC Reviewer",
            what=f"QC Review marked {payload.qc_status}: {payload.qc_note}",
            rule="Quality Control & Calibration SOP v2.0",
            evidence=f"Audit score {row['audit_score']}%, risk {row['risk_score']} ({row['risk_band']})",
            confidence=100.0,
            decision=payload.qc_status.upper(),
            human_override=payload.qc_status == "Disputed",
        )
        return {
            "message": f"QC outcome saved as {payload.qc_status} for {row['ticket_id']}.",
            "qc": qc_agent.analyze(conn),
        }


@router.patch("/feedback/{feedback_id}")
def update_feedback_status(feedback_id: str, payload: FeedbackStatusUpdate):
    with db_session() as conn:
        row = conn.execute("SELECT * FROM feedback WHERE feedback_id = ?", (feedback_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Feedback record not found.")
        conn.execute(
            "UPDATE feedback SET applied_status = ? WHERE feedback_id = ?",
            (payload.applied_status, feedback_id),
        )
        return {
            "message": f"Feedback {feedback_id} updated to '{payload.applied_status}'.",
            "feedbackId": feedback_id,
            "appliedStatus": payload.applied_status,
        }
