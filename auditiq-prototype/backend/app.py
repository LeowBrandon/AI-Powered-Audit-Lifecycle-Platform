from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="AuditIQ Prototype API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

now = datetime.now(timezone.utc).isoformat()

RULES = {
    "INC": [
        ("Categorization", "Correct category", "deterministic"),
        ("Priority", "Correct severity", "deterministic"),
        ("SLA", "Within SLA", "deterministic"),
        ("Root Cause", "Documented", "ai"),
        ("Resolution", "Clearly documented", "ai"),
        ("Customer Communication", "Required", "ai"),
        ("Closure Code", "Correct", "deterministic"),
    ],
    "SR": [
        ("Request classification", "Correct", "deterministic"),
        ("Authorization", "Required approval", "deterministic"),
        ("Fulfillment", "Completed", "deterministic"),
        ("SLA", "Met", "deterministic"),
        ("Documentation", "Complete", "ai"),
        ("Closure", "Correct", "deterministic"),
    ],
    "CR": [
        ("Risk assessment", "Required", "deterministic"),
        ("Business approval", "Required", "deterministic"),
        ("Technical approval", "Required", "deterministic"),
        ("Implementation plan", "Required", "ai"),
        ("Rollback plan", "Required", "ai"),
        ("Testing", "Required", "ai"),
        ("Post-implementation review", "Required", "ai"),
    ],
}

TICKETS: list[dict[str, Any]] = [
    {
        "id": "CR001992", "type": "CR", "shortDescription": "Database upgrade - production cluster",
        "priority": "P1", "assignmentGroup": "Infrastructure", "owner": "Database Operations",
        "state": "Scheduled", "risk": 62, "riskBand": "HIGH", "compliance": 62, "confidence": 96,
        "sla": "At risk", "businessApproval": False, "technicalApproval": True,
        "rollbackPlan": "partial", "testing": True, "riskAssessment": True, "implementationPlan": True,
        "postValidation": False, "customerCommunication": True, "category": "Database",
        "updated": now, "target": "2026-09-23 19:00",
        "description": "Upgrade PostgreSQL cluster from 14.x to 16.x to address security and capacity requirements.",
        "workNotes": [
            "Technical review completed by Database Operations.",
            "Production change window reserved for 19:00.",
            "Rollback section says previous configuration will be restored if deployment fails, but rollback steps are incomplete.",
        ],
        "approvals": ["Technical approval — Database Operations"],
        "evidence": {
            "Risk assessment": {"status": "PASS", "confidence": 99, "source": "Change risk assessment", "text": "High-risk classification documented with impact analysis."},
            "Business approval": {"status": "FAIL", "confidence": 98, "source": "Approval records", "text": "No business owner approval detected before scheduled implementation."},
            "Technical approval": {"status": "PASS", "confidence": 99, "source": "Approval records", "text": "Technical approval recorded from Database Operations."},
            "Implementation plan": {"status": "PASS", "confidence": 94, "source": "Implementation Plan → Section 2", "text": "Steps, owner and planned implementation window are documented."},
            "Rollback plan": {"status": "REVIEW", "confidence": 71, "source": "Implementation Plan → Section 4", "text": "Intent to restore the previous configuration is documented, but detailed rollback steps are incomplete."},
            "Testing": {"status": "PASS", "confidence": 95, "source": "Validation checklist", "text": "Pre-production validation evidence is attached."},
            "Post-implementation review": {"status": "FAIL", "confidence": 93, "source": "Closure controls", "text": "No post-implementation validation evidence has been recorded yet."},
        },
        "findings": [
            {"criterion": "Business approval", "status": "FAIL", "severity": "HIGH", "confidence": 98, "reason": "Required business owner approval is missing."},
            {"criterion": "Rollback plan", "status": "REVIEW", "severity": "MEDIUM", "confidence": 71, "reason": "Rollback intent is present, but execution steps are incomplete."},
            {"criterion": "Post-implementation review", "status": "FAIL", "severity": "HIGH", "confidence": 93, "reason": "Validation evidence will be required after implementation."},
        ],
    },
    {
        "id": "INC0045821", "type": "INC", "shortDescription": "Branch network outage",
        "priority": "P2", "assignmentGroup": "Network Operations", "owner": "L2 Network",
        "state": "Closed", "risk": 18, "riskBand": "LOW", "compliance": 96, "confidence": 97,
        "sla": "Met", "businessApproval": None, "technicalApproval": None,
        "rollbackPlan": None, "testing": None, "riskAssessment": None,
        "implementationPlan": None, "postValidation": True, "customerCommunication": True, "category": "Network",
        "updated": now, "target": "Closed",
        "description": "Intermittent connectivity affecting branch users.",
        "workNotes": ["Root cause identified as failed switch module.", "Customer confirmed service recovery at 14:35."],
        "approvals": [],
        "evidence": {
            "Categorization": {"status": "PASS", "confidence": 99, "source": "Ticket fields", "text": "Network incident category aligns with service impact."},
            "Priority": {"status": "PASS", "confidence": 97, "source": "Ticket fields", "text": "P2 severity aligns with impact and urgency."},
            "SLA": {"status": "PASS", "confidence": 99, "source": "SLA record", "text": "Resolution completed within target SLA."},
            "Root Cause": {"status": "PASS", "confidence": 96, "source": "Work notes", "text": "Failed switch module documented as root cause."},
            "Resolution": {"status": "PASS", "confidence": 98, "source": "Work notes", "text": "Switch module replaced and connectivity restored."},
            "Customer Communication": {"status": "PASS", "confidence": 95, "source": "Closure notes", "text": "Customer confirmation recorded."},
            "Closure Code": {"status": "PASS", "confidence": 99, "source": "Ticket fields", "text": "Closure code matches incident resolution."},
        },
        "findings": [],
    },
    {
        "id": "SR002134", "type": "SR", "shortDescription": "Laptop replacement request",
        "priority": "P3", "assignmentGroup": "Service Desk", "owner": "EU Workplace",
        "state": "Closed", "risk": 28, "riskBand": "LOW", "compliance": 94, "confidence": 94,
        "sla": "Met", "businessApproval": True, "technicalApproval": None,
        "rollbackPlan": None, "testing": None, "riskAssessment": None, "implementationPlan": None,
        "postValidation": True, "customerCommunication": True, "category": "End User",
        "updated": now, "target": "Closed",
        "description": "Standard laptop replacement request for an employee.",
        "workNotes": ["Manager authorization validated.", "Device issued and old device returned."],
        "approvals": ["Manager approval"],
        "evidence": {}, "findings": [],
    },
    {
        "id": "CR002010", "type": "CR", "shortDescription": "Firewall rule update - remote access",
        "priority": "P2", "assignmentGroup": "Security", "owner": "Security Operations",
        "state": "Pending approval", "risk": 87, "riskBand": "CRITICAL", "compliance": 49, "confidence": 91,
        "sla": "At risk", "businessApproval": False, "technicalApproval": True,
        "rollbackPlan": False, "testing": False, "riskAssessment": True, "implementationPlan": True,
        "postValidation": False, "customerCommunication": False, "category": "Security",
        "updated": now, "target": "2026-09-23 16:30",
        "description": "Firewall rule change to support remote access routing.",
        "workNotes": ["Approval pending.", "Implementation scheduled soon.", "No rollback plan detected."],
        "approvals": ["Technical approval — Security Operations"],
        "evidence": {},
        "findings": [
            {"criterion": "Business approval", "status": "FAIL", "severity": "HIGH", "confidence": 97, "reason": "Approval pending before scheduled implementation."},
            {"criterion": "Rollback plan", "status": "FAIL", "severity": "HIGH", "confidence": 95, "reason": "No rollback plan detected."},
        ],
    },
    {
        "id": "INC0045810", "type": "INC", "shortDescription": "Batch job failed overnight",
        "priority": "P2", "assignmentGroup": "Applications", "owner": "Batch Operations",
        "state": "Closed", "risk": 34, "riskBand": "LOW", "compliance": 91, "confidence": 88,
        "sla": "Met", "businessApproval": None, "technicalApproval": None,
        "rollbackPlan": None, "testing": None, "riskAssessment": None, "implementationPlan": None,
        "postValidation": True, "customerCommunication": True, "category": "Applications",
        "updated": now, "target": "Closed",
        "description": "Overnight batch job failure caused delayed downstream processing.",
        "workNotes": ["Job restarted successfully.", "Root cause note is brief; similar ticket history may help."],
        "approvals": [], "evidence": {},
        "findings": [{"criterion": "Root Cause", "status": "REVIEW", "severity": "MEDIUM", "confidence": 72, "reason": "Root cause documentation is brief and needs auditor confirmation."}],
    },
]


def get_ticket(ticket_id: str) -> dict[str, Any]:
    for t in TICKETS:
        if t["id"] == ticket_id:
            return t
    raise HTTPException(status_code=404, detail="Ticket not found")


def calculate_score(t: dict[str, Any]) -> int:
    base = 100
    penalties = 0
    for f in t.get("findings", []):
        if f["status"] == "FAIL":
            penalties += 22 if f["severity"] == "HIGH" else 14
        elif f["status"] == "REVIEW":
            penalties += 9
    if t["sla"] == "At risk": penalties += 8
    if t["risk"] >= 80: penalties += 4
    return max(0, min(100, base - penalties))


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "AuditIQ Prototype API"}


@app.get("/api/dashboard")
def dashboard():
    total = len(TICKETS)
    avg_compliance = round(sum(t["compliance"] for t in TICKETS) / total, 1)
    high = sum(t["risk"] >= 60 for t in TICKETS)
    alerts = sum(t["state"] in {"Pending approval", "Scheduled"} and t["risk"] >= 60 for t in TICKETS)
    return {"total": total, "auditCompletion": 82, "compliance": avg_compliance, "highRisk": high, "aiAlerts": alerts, "avgAuditTime": 7.4, "autoAudited": 76}


@app.get("/api/tickets")
def tickets():
    return [{k: t[k] for k in ["id", "type", "shortDescription", "priority", "assignmentGroup", "state", "risk", "riskBand", "compliance", "confidence", "sla", "owner"]} for t in TICKETS]


@app.get("/api/tickets/{ticket_id}")
def ticket(ticket_id: str):
    t = get_ticket(ticket_id)
    rules = [{"criterion": x[0], "requirement": x[1], "method": x[2]} for x in RULES[t["type"]]]
    return {**t, "rules": rules, "score": calculate_score(t), "lastEvaluated": now}


@app.post("/api/tickets/{ticket_id}/approve-business")
def approve_business(ticket_id: str):
    t = get_ticket(ticket_id)
    t["businessApproval"] = True
    t["approvals"] = list(dict.fromkeys(t.get("approvals", []) + ["Business owner approval — Finance Applications"]))
    if t["id"] == "CR001992":
        t["findings"] = [f for f in t["findings"] if f["criterion"] != "Business approval"]
        t["risk"] = 41
        t["riskBand"] = "LOW"
        t["compliance"] = 91
        t["confidence"] = 97
        t["evidence"]["Business approval"] = {"status": "PASS", "confidence": 99, "source": "Approval records", "text": "Business owner approval received and timestamped before implementation."}
    return {"message": "Business approval received", "ticket": t}


class Override(BaseModel):
    criterion: str
    decision: str
    note: str
    auditor: str = "Demo Auditor"


@app.post("/api/tickets/{ticket_id}/override")
def override(ticket_id: str, override: Override):
    t = get_ticket(ticket_id)
    found = next((f for f in t.get("findings", []) if f["criterion"] == override.criterion), None)
    if found:
        found["status"] = override.decision
        found["reason"] = f"Human override by {override.auditor}: {override.note}"
    if override.decision == "PASS":
        t["compliance"] = min(100, t["compliance"] + 6)
    return {"message": "Override recorded", "ticket": t, "auditTrail": {"who": override.auditor, "what": override.decision, "when": datetime.now(timezone.utc).isoformat(), "criterion": override.criterion, "note": override.note}}


@app.get("/api/analytics")
def analytics():
    return {
        "ticketType": [{"label": "INC", "value": 96}, {"label": "SR", "value": 94}, {"label": "CR", "value": 88}],
        "department": [{"label": "Infrastructure", "value": 96}, {"label": "Applications", "value": 94}, {"label": "Security", "value": 91}, {"label": "Network", "value": 89}, {"label": "Service Desk", "value": 97}],
        "failureCategories": [
            {"label": "Missing approval", "value": 31}, {"label": "Incomplete documentation", "value": 27}, {"label": "Incorrect categorization", "value": 16}, {"label": "SLA violations", "value": 14}, {"label": "Missing validation", "value": 12}
        ],
        "trend": [{"month": "Apr", "value": 88.1}, {"month": "May", "value": 89.4}, {"month": "Jun", "value": 91.2}, {"month": "Jul", "value": 92.1}, {"month": "Aug", "value": 93.0}, {"month": "Sep", "value": 94.2}],
    }


@app.get("/api/qc")
def qc():
    return {
        "auditorVariance": 8.4,
        "disputed": 12,
        "aiHumanAgreement": 92.6,
        "exceptions": 7,
        "auditors": [
            {"name": "A. Rahman", "audits": 126, "agreement": 96, "variance": 4.1},
            {"name": "J. Lim", "audits": 118, "agreement": 94, "variance": 6.2},
            {"name": "S. Tan", "audits": 101, "agreement": 89, "variance": 11.8},
            {"name": "M. Lee", "audits": 132, "agreement": 93, "variance": 7.0},
        ],
        "focus": ["Low-confidence AI decisions", "Disputed findings", "Unusual scoring patterns", "Potential auditor inconsistencies"],
    }


@app.get("/api/monitoring")
def monitoring():
    return [
        {"id": "CR002010", "status": "CRITICAL", "message": "Approval pending before scheduled implementation.", "action": "Obtain business approval", "time": "8 min ago"},
        {"id": "CR001992", "status": "HIGH", "message": "Business approval missing and rollback evidence incomplete.", "action": "Resolve before implementation", "time": "14 min ago"},
        {"id": "INC0045810", "status": "REVIEW", "message": "Root cause documentation is brief.", "action": "Auditor confirmation", "time": "27 min ago"},
    ]


class CopilotRequest(BaseModel):
    ticket_id: str
    question: str


@app.post("/api/copilot")
def copilot(req: CopilotRequest):
    t = get_ticket(req.ticket_id)
    q = req.question.lower()
    findings = t.get("findings", [])
    if "why" in q and ("fail" in q or "risk" in q):
        reasons = "; ".join([f"{f['criterion']}: {f['reason']}" for f in findings]) or "No failing criteria were detected."
        answer = f"{t['id']} is currently {t['riskBand']} risk with a compliance score of {t['compliance']}%. {reasons}"
    elif "evidence" in q:
        lines = []
        for k, v in t.get("evidence", {}).items():
            if v["status"] != "PASS": lines.append(f"{k}: {v['status']} — {v['text']} ({v['confidence']}% confidence)")
        answer = "Relevant non-pass evidence: " + (" | ".join(lines) if lines else "None; all available evidence is passing.")
    elif "similar" in q:
        answer = "The closest mock comparators are other CR tickets in the same risk band. Similar historical failures most often involve missing approval, rollback evidence, or validation evidence."
    elif "rule" in q:
        answer = "The main score drivers are the audit rules for required approvals, rollback plan, and post-implementation review, combined with the risk and SLA state."
    elif "summary" in q:
        answer = f"Management summary: {t['id']} ({t['type']}) is {t['riskBand']} risk, compliance {t['compliance']}%, with {len(findings)} findings. Recommended action: resolve the high-risk evidence gaps before closure/implementation."
    else:
        answer = "I can explain findings, show evidence, compare similar tickets, identify score drivers, or create a management summary."
    return {"answer": answer, "sources": ["Audit Rules", "Ticket Evidence", "Historical Audit Patterns"]}


@app.get("/api/config")
def config():
    return {
        "confidenceAuto": 95,
        "confidenceRecommend": 80,
        "criticalRisk": 80,
        "highRisk": 60,
        "sampling": 25,
        "rules": RULES,
    }


@app.post("/api/reanalyze/{ticket_id}")
def reanalyze(ticket_id: str):
    t = get_ticket(ticket_id)
    if t["id"] == "CR001992":
        t["risk"] = 41 if t.get("businessApproval") else 62
        t["riskBand"] = "LOW" if t["risk"] < 60 else "HIGH"
        t["compliance"] = 91 if t.get("businessApproval") else 62
    return {"message": "Audit re-evaluated", "ticket": t, "score": calculate_score(t)}
