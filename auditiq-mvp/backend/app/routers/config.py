"""Audit Configuration & Governance Administrator API (Proposal Sections 22, 23 & Screen 8)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.database import db_session
from app.schemas import CriterionCreate, CriterionUpdate, GovernanceConfigUpdate
from app.seed import seed_database
from app.services.audit_service import get_governance_config, run_ticket_audit, utc_now

router = APIRouter(prefix="/api/config", tags=["Governance Configuration"])


def _serialize_config(conn) -> dict:
    cfg = get_governance_config(conn)
    criteria_rows = conn.execute(
        "SELECT * FROM audit_criteria ORDER BY audit_type ASC, criterion_id ASC"
    ).fetchall()
    grouped: dict[str, list[dict]] = {"INC": [], "SR": [], "CR": []}
    for r in criteria_rows:
        d = dict(r)
        grouped.setdefault(d["audit_type"], []).append(
            {
                "criterionId": d["criterion_id"],
                "auditType": d["audit_type"],
                "criterionName": d["criterion_name"],
                "requirement": d["requirement"],
                "rule": d["rule"],
                "policyRef": d["policy_ref"],
                "method": d["method"],
                "weight": d["weight"],
                "severityIfFailed": d["severity_if_failed"],
                "active": bool(d["active"]),
            }
        )
    return {
        "confidenceAuto": cfg["confidence_auto"],
        "confidenceRecommend": cfg["confidence_recommend"],
        "criticalRisk": cfg["critical_risk_threshold"],
        "highRisk": cfg["high_risk_threshold"],
        "mediumRisk": cfg["medium_risk_threshold"],
        "sampling": cfg["medium_sampling_pct"],
        "proactiveAlertsEnabled": bool(cfg["proactive_alerts_enabled"]),
        "autoCloseLowRisk": bool(cfg["auto_close_low_risk"]),
        "updatedBy": cfg["updated_by"],
        "updatedAt": cfg["updated_at"],
        "aiEngine": {
            "llmEnabled": settings.llm_enabled,
            "modelLabel": settings.active_ai_model_label,
            "llmModel": settings.llm_model if settings.llm_enabled else "Local Deterministic + NLP Engine",
        },
        "rules": grouped,
    }


@router.get("")
def get_config():
    with db_session() as conn:
        return _serialize_config(conn)


@router.put("")
def update_config(payload: GovernanceConfigUpdate):
    if payload.confidence_recommend >= payload.confidence_auto:
        raise HTTPException(
            status_code=400,
            detail="AI Recommendation confidence threshold must be strictly lower than Auto Decision threshold.",
        )
    if not (payload.medium_risk_threshold < payload.high_risk_threshold < payload.critical_risk_threshold):
        raise HTTPException(
            status_code=400,
            detail="Risk thresholds must satisfy Medium < High < Critical.",
        )

    with db_session() as conn:
        now = utc_now()
        conn.execute(
            """
            UPDATE governance_config
            SET confidence_auto = ?, confidence_recommend = ?,
                critical_risk_threshold = ?, high_risk_threshold = ?,
                medium_risk_threshold = ?, medium_sampling_pct = ?,
                proactive_alerts_enabled = ?, auto_close_low_risk = ?,
                updated_by = ?, updated_at = ?
            WHERE id = 1
            """,
            (
                payload.confidence_auto,
                payload.confidence_recommend,
                payload.critical_risk_threshold,
                payload.high_risk_threshold,
                payload.medium_risk_threshold,
                payload.medium_sampling_pct,
                1 if payload.proactive_alerts_enabled else 0,
                1 if payload.auto_close_low_risk else 0,
                payload.updated_by,
                now,
            ),
        )
        re_eval_count = 0
        if payload.re_evaluate_all:
            rows = conn.execute("SELECT ticket_id FROM tickets").fetchall()
            for r in rows:
                run_ticket_audit(
                    conn,
                    r["ticket_id"],
                    actor=payload.updated_by,
                    actor_role="Governance Administrator",
                    broadcast=False,
                )
            re_eval_count = len(rows)

        msg = (
            f"Governance thresholds saved and {re_eval_count} tickets re-evaluated."
            if payload.re_evaluate_all
            else "Governance configuration saved."
        )
        return {"message": msg, "config": _serialize_config(conn)}


@router.post("/criteria", status_code=201)
def create_criterion(payload: CriterionCreate):
    with db_session() as conn:
        cid = (
            payload.criterion_id.strip().upper()
            if payload.criterion_id
            else f"{payload.audit_type}-{uuid.uuid4().hex[:4].upper()}"
        )
        exists = conn.execute("SELECT 1 FROM audit_criteria WHERE criterion_id = ?", (cid,)).fetchone()
        if exists:
            raise HTTPException(status_code=409, detail=f"Criterion {cid} already exists.")
        conn.execute(
            """
            INSERT INTO audit_criteria (
                criterion_id, audit_type, criterion_name, requirement, rule,
                policy_ref, method, weight, severity_if_failed, active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cid,
                payload.audit_type,
                payload.criterion_name,
                payload.requirement,
                payload.rule,
                payload.policy_ref,
                payload.method,
                payload.weight,
                payload.severity_if_failed,
                1 if payload.active else 0,
            ),
        )
        return {
            "message": f"Created audit criterion {cid} ({payload.criterion_name}).",
            "config": _serialize_config(conn),
        }


@router.patch("/criteria/{criterion_id}")
def update_criterion(criterion_id: str, payload: CriterionUpdate):
    with db_session() as conn:
        row = conn.execute(
            "SELECT * FROM audit_criteria WHERE criterion_id = ?",
            (criterion_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Criterion {criterion_id} not found.")
        cur = dict(row)
        conn.execute(
            """
            UPDATE audit_criteria
            SET requirement = ?, rule = ?, policy_ref = ?, method = ?,
                weight = ?, severity_if_failed = ?, active = ?
            WHERE criterion_id = ?
            """,
            (
                payload.requirement if payload.requirement is not None else cur["requirement"],
                payload.rule if payload.rule is not None else cur["rule"],
                payload.policy_ref if payload.policy_ref is not None else cur["policy_ref"],
                payload.method if payload.method is not None else cur["method"],
                payload.weight if payload.weight is not None else cur["weight"],
                payload.severity_if_failed if payload.severity_if_failed is not None else cur["severity_if_failed"],
                (1 if payload.active else 0) if payload.active is not None else cur["active"],
                criterion_id,
            ),
        )
        return {
            "message": f"Updated criterion {criterion_id}.",
            "config": _serialize_config(conn),
        }


@router.post("/reset-demo")
def reset_demo_dataset():
    """Resets the database to the clean 60-ticket demo dataset (great before live presentations)."""
    with db_session() as conn:
        result = seed_database(conn, force=True)
        return {
            "message": f"Demo environment reset cleanly ({result['tickets']} simulated tickets re-audited).",
            "tickets": result["tickets"],
        }
