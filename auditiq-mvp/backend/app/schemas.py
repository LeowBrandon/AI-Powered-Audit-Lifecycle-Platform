"""Pydantic v2 request and response schemas for AuditIQ API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class WorkNoteInput(BaseModel):
    timestamp: str | None = None
    author: str = "Operations Engineer"
    text: str = Field(..., min_length=2)


class ApprovalInput(BaseModel):
    type: Literal["Business", "Technical", "Manager", "CAB"] = "Business"
    approver: str = Field(..., min_length=2)
    status: Literal["Approved", "Pending", "Rejected"] = "Approved"
    note: str = ""


class AttachmentInput(BaseModel):
    name: str = Field(..., min_length=2)
    section: str = "Document"
    content_summary: str = Field(..., min_length=2)


class TicketCreate(BaseModel):
    ticket_id: str | None = None
    ticket_type: Literal["INC", "SR", "CR"]
    short_description: str = Field(..., min_length=4)
    description: str = ""
    priority: Literal["P1", "P2", "P3", "P4"] = "P2"
    category: str = "Infrastructure"
    business_unit: str = "Enterprise IT"
    assignment_group: str = "Infrastructure"
    requester: str = "Operations User"
    owner: str = "Operations Lead"
    resolver: str = ""
    status: Literal["In Progress", "Pending Approval", "Scheduled", "Resolved", "Closed"] = "Scheduled"
    sla_status: Literal["Met", "Within SLA", "At Risk", "Breached"] = "Within SLA"
    closure_code: str = ""
    resolution: str = ""
    target_window: str = ""
    work_notes: list[WorkNoteInput] = Field(default_factory=list)
    approvals: list[ApprovalInput] = Field(default_factory=list)
    attachments: list[AttachmentInput] = Field(default_factory=list)
    related_tickets: list[str] = Field(default_factory=list)


class RemediationRequest(BaseModel):
    action_type: Literal[
        "business_approval",
        "technical_approval",
        "rollback_plan",
        "post_validation",
        "root_cause",
        "customer_communication",
        "work_note",
        "close_ticket",
    ]
    actor: str = "Demo Auditor"
    role: str = "Auditor"
    approver: str = "VP Finance Operations"
    note: str = ""
    closure_code: str = "Successful - Validated"


class FindingActionRequest(BaseModel):
    decision: Literal["APPROVE_FINDING", "OVERRIDE_PASS", "OVERRIDE_FAIL", "REQUEST_EVIDENCE"]
    note: str = Field(..., min_length=3)
    auditor: str = "A. Rahman"
    role: str = "Auditor"
    improvement_target: Literal[
        "Audit Rules",
        "Prompts",
        "RAG Retrieval",
        "Evidence Extraction",
        "Confidence Thresholds",
    ] = "Audit Rules"


class QCReviewRequest(BaseModel):
    qc_status: Literal["Verified", "Disputed"]
    qc_reviewer: str = "L. Chen (QC Lead)"
    qc_note: str = Field(..., min_length=3)


class FeedbackStatusUpdate(BaseModel):
    applied_status: Literal["Captured", "Queued for Tuning", "Applied"]


class CopilotMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class CopilotRequest(BaseModel):
    ticket_id: str | None = None
    question: str = Field(..., min_length=2)
    history: list[CopilotMessage] = Field(default_factory=list)
    user_role: str = "Auditor"


class PolicyCreateRequest(BaseModel):
    policy_id: str | None = None
    title: str = Field(..., min_length=4)
    category: str = "Audit SOP"
    version: str = "v1.0"
    owner: str = "Operations Governance"
    applies_to: Literal["INC", "SR", "CR", "ALL"] = "ALL"
    summary: str = Field(..., min_length=10)
    content: str = Field(..., min_length=20)
    tags: list[str] = Field(default_factory=list)


class GovernanceConfigUpdate(BaseModel):
    confidence_auto: int = Field(95, ge=80, le=100)
    confidence_recommend: int = Field(80, ge=50, le=95)
    critical_risk_threshold: int = Field(80, ge=50, le=99)
    high_risk_threshold: int = Field(60, ge=30, le=90)
    medium_risk_threshold: int = Field(35, ge=10, le=75)
    medium_sampling_pct: int = Field(25, ge=5, le=100)
    proactive_alerts_enabled: bool = True
    auto_close_low_risk: bool = True
    updated_by: str = "Governance Administrator"
    re_evaluate_all: bool = False


class CriterionUpdate(BaseModel):
    requirement: str | None = None
    rule: str | None = None
    policy_ref: str | None = None
    method: Literal["deterministic", "ai"] | None = None
    weight: float | None = Field(default=None, ge=0.2, le=5.0)
    severity_if_failed: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] | None = None
    active: bool | None = None


class CriterionCreate(BaseModel):
    criterion_id: str | None = None
    audit_type: Literal["INC", "SR", "CR"]
    criterion_name: str = Field(..., min_length=3)
    requirement: str = Field(..., min_length=2)
    rule: str = Field(..., min_length=5)
    policy_ref: str = "Enterprise Governance Policy v3.2"
    method: Literal["deterministic", "ai"] = "ai"
    weight: float = Field(1.0, ge=0.2, le=5.0)
    severity_if_failed: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = "MEDIUM"
    active: bool = True
