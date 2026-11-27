"""Agent 1 — Ticket Intelligence Agent (Proposal Section 4, Pages 5-6).

Extracts and normalizes all 14 core ticket attributes, detects active vs closed
lifecycle stage, classifies audit scope, and scores intrinsic ticket complexity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.agents.base import AgentStepTrace, elapsed_ms, timer_start
from app.database import parse_json_col


@dataclass
class TicketContext:
    ticket_id: str
    ticket_type: str
    short_description: str
    description: str
    priority: str
    category: str
    business_unit: str
    assignment_group: str
    requester: str
    owner: str
    resolver: str
    status: str
    sla_status: str
    closure_code: str
    resolution: str
    work_notes: list[dict[str, Any]]
    approvals: list[dict[str, Any]]
    attachments: list[dict[str, Any]]
    related_tickets: list[str]
    target_window: str
    created_at: str
    updated_at: str
    closed_at: str | None
    historical_group_risk: float
    previous_audit_issues: int
    is_active: bool = False
    is_production_scope: bool = False
    complexity_score: float = 0.0
    combined_corpus: str = ""
    extracted_summary_flags: list[dict[str, Any]] = field(default_factory=list)


PROD_KEYWORDS = (
    "production",
    "prod",
    "core",
    "cluster",
    "firewall",
    "payment",
    "banking",
    "database",
    "active directory",
    "tls",
    "load balancer",
    "security",
)


class TicketIntelligenceAgent:
    """Normalizes raw ITSM ticket records into structured audit context."""

    def extract(self, raw_ticket: dict[str, Any]) -> tuple[TicketContext, AgentStepTrace]:
        start = timer_start()
        work_notes = (
            raw_ticket["work_notes"]
            if isinstance(raw_ticket.get("work_notes"), list)
            else parse_json_col(raw_ticket.get("work_notes_json"), [])
        )
        approvals = (
            raw_ticket["approvals"]
            if isinstance(raw_ticket.get("approvals"), list)
            else parse_json_col(raw_ticket.get("approvals_json"), [])
        )
        attachments = (
            raw_ticket["attachments"]
            if isinstance(raw_ticket.get("attachments"), list)
            else parse_json_col(raw_ticket.get("attachments_json"), [])
        )
        related_tickets = (
            raw_ticket["related_tickets"]
            if isinstance(raw_ticket.get("related_tickets"), list)
            else parse_json_col(raw_ticket.get("related_tickets_json"), [])
        )

        # Normalize legacy string work notes / approvals cleanly
        norm_notes: list[dict[str, Any]] = []
        for idx, note in enumerate(work_notes):
            if isinstance(note, dict):
                norm_notes.append(
                    {
                        "timestamp": note.get("timestamp") or f"Note #{idx + 1}",
                        "author": note.get("author") or raw_ticket.get("owner", "Operations"),
                        "text": str(note.get("text", "")).strip(),
                    }
                )
            elif str(note).strip():
                norm_notes.append(
                    {
                        "timestamp": f"Note #{idx + 1}",
                        "author": raw_ticket.get("owner", "Operations"),
                        "text": str(note).strip(),
                    }
                )

        norm_approvals: list[dict[str, Any]] = []
        for appr in approvals:
            if isinstance(appr, dict):
                norm_approvals.append(
                    {
                        "type": appr.get("type", "Business"),
                        "approver": appr.get("approver", "Unknown Approver"),
                        "status": appr.get("status", "Approved"),
                        "timestamp": appr.get("timestamp", raw_ticket.get("updated_at", "")),
                        "note": appr.get("note", ""),
                    }
                )
            elif str(appr).strip():
                low = str(appr).lower()
                a_type = "Technical" if "technical" in low else "Manager" if "manager" in low else "Business"
                norm_approvals.append(
                    {
                        "type": a_type,
                        "approver": str(appr),
                        "status": "Approved",
                        "timestamp": raw_ticket.get("updated_at", ""),
                        "note": "",
                    }
                )

        norm_attachments: list[dict[str, Any]] = []
        for att in attachments:
            if isinstance(att, dict):
                norm_attachments.append(
                    {
                        "name": att.get("name", "Attachment"),
                        "section": att.get("section", "Document"),
                        "content_summary": att.get("content_summary", ""),
                    }
                )

        corpus_parts = [
            raw_ticket.get("short_description", ""),
            raw_ticket.get("description", ""),
            raw_ticket.get("resolution", ""),
            raw_ticket.get("closure_code", ""),
            " ".join(n["text"] for n in norm_notes),
            " ".join(f"{a['type']} {a['approver']} {a['status']} {a['note']}" for a in norm_approvals),
            " ".join(f"{a['name']} {a['section']} {a['content_summary']}" for a in norm_attachments),
        ]
        combined_corpus = "\n".join(p for p in corpus_parts if p).strip()
        low_corpus = combined_corpus.lower()

        status = raw_ticket.get("status", "Closed")
        is_active = status in {"In Progress", "Pending Approval", "Scheduled"}
        is_prod = any(k in low_corpus for k in PROD_KEYWORDS)

        priority = raw_ticket.get("priority", "P3")
        ticket_type = raw_ticket.get("ticket_type", "INC")
        complexity = 3.0
        if ticket_type == "CR":
            complexity += 5.0
        elif ticket_type == "INC":
            complexity += 3.0
        if priority == "P1":
            complexity += 6.0
        elif priority == "P2":
            complexity += 3.5
        if is_prod:
            complexity += 3.0
        if is_active:
            complexity += 1.5
        complexity = min(15.0, round(complexity, 1))

        ctx = TicketContext(
            ticket_id=raw_ticket["ticket_id"],
            ticket_type=ticket_type,
            short_description=raw_ticket.get("short_description", ""),
            description=raw_ticket.get("description", ""),
            priority=priority,
            category=raw_ticket.get("category", "General"),
            business_unit=raw_ticket.get("business_unit", "Enterprise IT"),
            assignment_group=raw_ticket.get("assignment_group", "Service Desk"),
            requester=raw_ticket.get("requester", "Operations User"),
            owner=raw_ticket.get("owner", "Operations Team"),
            resolver=raw_ticket.get("resolver", ""),
            status=status,
            sla_status=raw_ticket.get("sla_status", "Met"),
            closure_code=raw_ticket.get("closure_code", ""),
            resolution=raw_ticket.get("resolution", ""),
            work_notes=norm_notes,
            approvals=norm_approvals,
            attachments=norm_attachments,
            related_tickets=[str(r) for r in related_tickets],
            target_window=raw_ticket.get("target_window", ""),
            created_at=raw_ticket.get("created_at", ""),
            updated_at=raw_ticket.get("updated_at", ""),
            closed_at=raw_ticket.get("closed_at"),
            historical_group_risk=float(raw_ticket.get("historical_group_risk", 8.0)),
            previous_audit_issues=int(raw_ticket.get("previous_audit_issues", 0)),
            is_active=is_active,
            is_production_scope=is_prod,
            complexity_score=complexity,
            combined_corpus=combined_corpus,
        )

        trace = AgentStepTrace(
            agent_number=1,
            agent_name="Ticket Intelligence Agent",
            phase="Phase 1 — Intake & Classification",
            status="completed",
            duration_ms=elapsed_ms(start),
            summary=(
                f"Normalized {ctx.ticket_id} ({ctx.ticket_type}, {ctx.priority}, {ctx.assignment_group}); "
                f"extracted {len(ctx.work_notes)} work notes, {len(ctx.approvals)} approval records, "
                f"{len(ctx.attachments)} attachments."
            ),
            metrics={
                "ticketType": ctx.ticket_type,
                "lifecycleState": "Active / Pre-Closure" if ctx.is_active else "Closed / Resolved",
                "complexityScore": ctx.complexity_score,
                "productionScope": ctx.is_production_scope,
            },
        )
        return ctx, trace
