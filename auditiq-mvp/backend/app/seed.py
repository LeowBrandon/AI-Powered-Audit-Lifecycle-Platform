"""Seed realistic simulated ITSM dataset (60 tickets, 20 criteria, 8 policies, QC feedback).

Explicitly includes all flagship tickets referenced in the AuditIQ Proposal PDF
and prototype (CR001992, CR002010, CR001990, CR00201, CR00203, INC0045821,
INC004582, INC00422, INC0045810, SR002134, SR21348, SR00119) plus 48 additional
simulated tickets spanning April–September 2026 so every chart, queue filter,
QC metric, and RAG search runs on real relational database records.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from app.database import db_session, reset_db_tables
from app.services.audit_service import (
    apply_finding_action,
    get_governance_config,
    refresh_rag_index,
    run_ticket_audit,
    utc_now,
)

DEFAULT_CRITERIA: list[dict[str, Any]] = [
    # INC audit criteria (Proposal Page 8)
    {
        "criterion_id": "INC-01",
        "audit_type": "INC",
        "criterion_name": "Categorization",
        "requirement": "Correct category",
        "rule": "Incident must be categorized accurately to the impacted ITIL service domain.",
        "policy_ref": "Incident Governance Standard v2.4 §3.1",
        "method": "deterministic",
        "weight": 1.0,
        "severity_if_failed": "MEDIUM",
    },
    {
        "criterion_id": "INC-02",
        "audit_type": "INC",
        "criterion_name": "Priority",
        "requirement": "Correct severity",
        "rule": "Priority level (P1–P4) must align with documented operational impact and urgency.",
        "policy_ref": "Incident Governance Standard v2.4 §3.2",
        "method": "deterministic",
        "weight": 1.1,
        "severity_if_failed": "HIGH",
    },
    {
        "criterion_id": "INC-03",
        "audit_type": "INC",
        "criterion_name": "SLA",
        "requirement": "Within SLA",
        "rule": "Incident must be resolved within contractual SLA target or have approved exception.",
        "policy_ref": "ITIL SLA Governance Policy v3.0 §2.1",
        "method": "deterministic",
        "weight": 1.4,
        "severity_if_failed": "HIGH",
    },
    {
        "criterion_id": "INC-04",
        "audit_type": "INC",
        "criterion_name": "Root Cause",
        "requirement": "Documented",
        "rule": "Technical root cause must be clearly documented in work notes or resolution prior to closure.",
        "policy_ref": "Incident Governance Standard v2.4 §5.1",
        "method": "ai",
        "weight": 1.5,
        "severity_if_failed": "HIGH",
    },
    {
        "criterion_id": "INC-05",
        "audit_type": "INC",
        "criterion_name": "Resolution",
        "requirement": "Clearly documented",
        "rule": "Resolution steps restoring service must be clearly documented and verifiable.",
        "policy_ref": "Incident Governance Standard v2.4 §5.2",
        "method": "ai",
        "weight": 1.4,
        "severity_if_failed": "HIGH",
    },
    {
        "criterion_id": "INC-06",
        "audit_type": "INC",
        "criterion_name": "Customer Communication",
        "requirement": "Required",
        "rule": "Stakeholder update and customer confirmation of service recovery must be recorded.",
        "policy_ref": "Incident Governance Standard v2.4 §5.4",
        "method": "ai",
        "weight": 1.2,
        "severity_if_failed": "MEDIUM",
    },
    {
        "criterion_id": "INC-07",
        "audit_type": "INC",
        "criterion_name": "Closure Code",
        "requirement": "Correct",
        "rule": "Standardized ITIL closure code must match the documented resolution outcome.",
        "policy_ref": "Incident Governance Standard v2.4 §6.1",
        "method": "deterministic",
        "weight": 1.0,
        "severity_if_failed": "MEDIUM",
    },
    # SR audit criteria (Proposal Page 8)
    {
        "criterion_id": "SR-01",
        "audit_type": "SR",
        "criterion_name": "Request classification",
        "requirement": "Correct",
        "rule": "Service request must be classified under the correct catalog item and domain.",
        "policy_ref": "Service Request SOP v2.1 §2.2",
        "method": "deterministic",
        "weight": 1.0,
        "severity_if_failed": "MEDIUM",
    },
    {
        "criterion_id": "SR-02",
        "audit_type": "SR",
        "criterion_name": "Authorization",
        "requirement": "Required approval",
        "rule": "Documented line-manager or resource-owner authorization is mandatory before fulfillment.",
        "policy_ref": "Service Request SOP v2.1 §3.1",
        "method": "deterministic",
        "weight": 1.8,
        "severity_if_failed": "HIGH",
    },
    {
        "criterion_id": "SR-03",
        "audit_type": "SR",
        "criterion_name": "Fulfillment",
        "requirement": "Completed",
        "rule": "Fulfillment actions (provisioning, hardware issuance, access grant) must be verified complete.",
        "policy_ref": "Service Request SOP v2.1 §4.1",
        "method": "deterministic",
        "weight": 1.3,
        "severity_if_failed": "HIGH",
    },
    {
        "criterion_id": "SR-04",
        "audit_type": "SR",
        "criterion_name": "SLA",
        "requirement": "Met",
        "rule": "Service request must meet catalog fulfillment SLA target.",
        "policy_ref": "ITIL SLA Governance Policy v3.0 §2.3",
        "method": "deterministic",
        "weight": 1.1,
        "severity_if_failed": "MEDIUM",
    },
    {
        "criterion_id": "SR-05",
        "audit_type": "SR",
        "criterion_name": "Documentation",
        "requirement": "Complete",
        "rule": "Complete work notes and fulfillment handoff documentation must be captured.",
        "policy_ref": "Service Request SOP v2.1 §4.3",
        "method": "ai",
        "weight": 1.2,
        "severity_if_failed": "MEDIUM",
    },
    {
        "criterion_id": "SR-06",
        "audit_type": "SR",
        "criterion_name": "Closure",
        "requirement": "Correct",
        "rule": "Request closure code and requester confirmation must be accurately populated.",
        "policy_ref": "Service Request SOP v2.1 §5.1",
        "method": "deterministic",
        "weight": 1.0,
        "severity_if_failed": "MEDIUM",
    },
    # CR audit criteria (Proposal Page 8)
    {
        "criterion_id": "CR-01",
        "audit_type": "CR",
        "criterion_name": "Risk assessment",
        "requirement": "Required",
        "rule": "Formal change risk and service impact assessment must be documented before CAB review.",
        "policy_ref": "Change Governance Policy v3.2 §3.1",
        "method": "deterministic",
        "weight": 1.3,
        "severity_if_failed": "HIGH",
    },
    {
        "criterion_id": "CR-02",
        "audit_type": "CR",
        "criterion_name": "Business approval",
        "requirement": "Required",
        "rule": "Documented business owner or CAB approval must exist before production implementation.",
        "policy_ref": "Change Governance Policy v3.2 §4.2",
        "method": "deterministic",
        "weight": 2.0,
        "severity_if_failed": "HIGH",
    },
    {
        "criterion_id": "CR-03",
        "audit_type": "CR",
        "criterion_name": "Technical approval",
        "requirement": "Required",
        "rule": "Peer technical review and architecture approval must be recorded prior to execution.",
        "policy_ref": "Change Governance Policy v3.2 §4.1",
        "method": "deterministic",
        "weight": 1.5,
        "severity_if_failed": "HIGH",
    },
    {
        "criterion_id": "CR-04",
        "audit_type": "CR",
        "criterion_name": "Implementation plan",
        "requirement": "Required",
        "rule": "Step-by-step execution runbook, owner assignment, and maintenance window must be documented.",
        "policy_ref": "Change Governance Policy v3.2 §5.1",
        "method": "ai",
        "weight": 1.3,
        "severity_if_failed": "MEDIUM",
    },
    {
        "criterion_id": "CR-05",
        "audit_type": "CR",
        "criterion_name": "Rollback plan",
        "requirement": "Required",
        "rule": "Executable rollback steps, trigger thresholds, and recovery verification must be documented.",
        "policy_ref": "Change Governance Policy v3.2 §5.3",
        "method": "ai",
        "weight": 1.6,
        "severity_if_failed": "HIGH",
    },
    {
        "criterion_id": "CR-06",
        "audit_type": "CR",
        "criterion_name": "Testing",
        "requirement": "Required",
        "rule": "Pre-production testing or staging validation checklist must be completed and attached.",
        "policy_ref": "Change Governance Policy v3.2 §5.4",
        "method": "ai",
        "weight": 1.2,
        "severity_if_failed": "MEDIUM",
    },
    {
        "criterion_id": "CR-07",
        "audit_type": "CR",
        "criterion_name": "Post-implementation review",
        "requirement": "Required",
        "rule": "Post-implementation validation, health check outcomes, and PIR sign-off are mandatory.",
        "policy_ref": "Change Governance Policy v3.2 §6.2",
        "method": "ai",
        "weight": 1.6,
        "severity_if_failed": "HIGH",
    },
]

DEFAULT_POLICIES: list[dict[str, Any]] = [
    {
        "policy_id": "POL-CHG-3.2",
        "title": "Change Governance Policy v3.2",
        "category": "Change Management",
        "version": "v3.2",
        "effective_date": "2026-01-15",
        "owner": "Operations Governance Board",
        "applies_to": "CR",
        "summary": "Defines mandatory authorization, risk assessment, rollback readiness, and post-implementation review controls for all production changes.",
        "content": (
            "Section 3.1 Risk Assessment: Every normal or emergency change impacting production infrastructure must document a formal risk and service impact assessment.\n"
            "Section 4.1 Technical Approval: Technical peer review by the owning engineering group is required before scheduling a change window.\n"
            "Section 4.2 Business Approval: Business owner authorization MUST exist and be timestamped in the ITSM record before production implementation begins. Technical approval alone does NOT satisfy business authorization.\n"
            "Section 5.1 Implementation Plan: Changes must specify execution sequence, named implementer, and reserved maintenance window.\n"
            "Section 5.3 Rollback Plan: Statements of general intent (e.g. 'restore previous config') without executable step-by-step rollback instructions, trigger criteria, and RTO estimates are considered incomplete and must be routed for auditor review.\n"
            "Section 6.2 Post-Implementation Review (PIR): Following execution, the owner must record smoke test results, service health verification, and stakeholder confirmation prior to ticket closure."
        ),
        "tags": ["change", "approval", "rollback", "pir", "cab", "business approval", "cr"],
    },
    {
        "policy_id": "POL-INC-2.4",
        "title": "Incident Governance Standard v2.4",
        "category": "Incident Management",
        "version": "v2.4",
        "effective_date": "2026-02-01",
        "owner": "IT Service Operations",
        "applies_to": "INC",
        "summary": "Sets audit requirements for incident categorization, severity alignment, root cause documentation, resolution clarity, and customer confirmation.",
        "content": (
            "Section 3.1 Categorization: Incident records must accurately reflect the affected ITIL service category (Network, Database, Applications, Security, Infrastructure, End User).\n"
            "Section 3.2 Priority Matrix: High-impact production outages affecting core banking, payments, or enterprise connectivity must be classified as P1 or P2.\n"
            "Section 5.1 Root Cause Documentation: All P1 and P2 incidents require a clear technical root cause statement and problem management linkage before closure. Brief notes without technical diagnosis trigger REVIEW.\n"
            "Section 5.2 Resolution Clarity: Resolution notes must state the exact restorative actions taken and verification timestamp.\n"
            "Section 5.4 Customer Communication: Evidence of customer notification and recovery confirmation is mandatory prior to closing incident tickets.\n"
            "Section 6.1 Closure Code: Closure codes must match the documented permanent fix or workaround."
        ),
        "tags": ["incident", "root cause", "resolution", "customer communication", "closure code", "inc"],
    },
    {
        "policy_id": "POL-SR-2.1",
        "title": "Service Request Governance SOP v2.1",
        "category": "Service Request",
        "version": "v2.1",
        "effective_date": "2026-01-20",
        "owner": "Workplace & Access Governance",
        "applies_to": "SR",
        "summary": "Governs service request classification, manager authorization, fulfillment verification, and closure documentation.",
        "content": (
            "Section 2.2 Classification: Service requests must use the approved enterprise catalog category matching the provisioned asset or privilege.\n"
            "Section 3.1 Authorization Control: Privileged access, hardware issuance, and software license requests require explicit documented line-manager or data-owner approval before fulfillment.\n"
            "Section 4.1 Fulfillment Verification: Engineers must record concrete delivery evidence (asset tag, account provisioned, license assigned).\n"
            "Section 4.3 Documentation Completeness: Incomplete closure checklists or single-line notes without requester verification fail documentation audit criteria."
        ),
        "tags": ["service request", "authorization", "manager approval", "fulfillment", "sr"],
    },
    {
        "policy_id": "POL-SLA-3.0",
        "title": "ITIL SLA Governance Policy v3.0",
        "category": "ITIL Procedures",
        "version": "v3.0",
        "effective_date": "2026-03-01",
        "owner": "Service Level Management",
        "applies_to": "ALL",
        "summary": "Establishes P1–P4 SLA targets, pre-breach alerting thresholds, and exception documentation standards.",
        "content": (
            "Section 2.1 Incident Targets: P1 critical incidents target 4-hour restoration; P2 high incidents target 8 hours; P3 standard incidents target 24 hours.\n"
            "Section 2.3 Service Request Targets: Standard catalog requests must be fulfilled within 3 business days.\n"
            "Section 3.1 Proactive SLA Risk Monitoring: Active tickets entering 'At Risk' status (>75% elapsed SLA) must trigger proactive monitoring alerts before closure."
        ),
        "tags": ["sla", "breach", "at risk", "itil", "monitoring"],
    },
    {
        "policy_id": "POL-AI-1.0",
        "title": "Enterprise AI Audit Governance & Confidence Framework v1.0",
        "category": "Audit Policies",
        "version": "v1.0",
        "effective_date": "2026-04-01",
        "owner": "AI Governance & Internal Audit",
        "applies_to": "ALL",
        "summary": "Mandates policy supremacy over AI, Three-Way Decision routing (PASS/FAIL/REVIEW), confidence thresholds, and immutable audit trails.",
        "content": (
            "Section 1 Policy Hierarchy: AI does not directly override enterprise audit policy. Control flow follows Enterprise Policy -> Rules Engine -> AI Interpretation -> Evidence -> Human Oversight.\n"
            "Section 2 Three-Way Decision Model: AI must never force ambiguous evidence into binary PASS/FAIL. Clear compliance = PASS; clear violation = FAIL; ambiguous or low-confidence evidence = REVIEW.\n"
            "Section 3 Confidence Thresholds: 95–100% enables automated decisioning; 80–94% surfaces AI recommendation; <80% mandates human auditor review.\n"
            "Section 4 Immutable Audit Trail: Every AI decision and human override must record Who, What, When, Rule, Evidence, AI Model, Confidence, Decision, and Human Override status."
        ),
        "tags": ["ai governance", "confidence", "audit trail", "human-in-the-loop", "three-way"],
    },
    {
        "policy_id": "POL-QC-2.0",
        "title": "Quality Control & Closed-Loop Calibration SOP v2.0",
        "category": "Quality Standards",
        "version": "v2.0",
        "effective_date": "2026-03-15",
        "owner": "Audit Quality Control Team",
        "applies_to": "ALL",
        "summary": "Defines exception-based QC sampling, auditor scoring variance thresholds, and feedback-driven rule refinement.",
        "content": (
            "Section 1 Exception-Based QC: QC Reviewers prioritize high-risk audits, low-confidence AI reviews, disputed findings, and auditors with >10% scoring variance.\n"
            "Section 2 Closed-Loop Learning: Every auditor override captures why AI differed and routes refinement tasks to Audit Rules, Prompts, RAG Retrieval, Evidence Extraction, or Confidence Thresholds."
        ),
        "tags": ["qc", "variance", "calibration", "closed-loop", "feedback", "override"],
    },
    {
        "policy_id": "POL-SMP-1.5",
        "title": "Intelligent Risk-Based Audit Sampling Standard v1.5",
        "category": "Audit SOP",
        "version": "v1.5",
        "effective_date": "2026-02-20",
        "owner": "Operations Governance Audit",
        "applies_to": "ALL",
        "summary": "Replaces static random sampling with dynamic 4-tier AI risk-based routing.",
        "content": (
            "Tier 1 Low Risk (<35): Automated AI Audit with auto-closure.\n"
            "Tier 2 Medium Risk (35–59): Dynamic Sampled Review (default 25% human validation).\n"
            "Tier 3 High Risk (60–79): Mandatory Human Auditor Review.\n"
            "Tier 4 Critical Risk (>=80): Immediate Escalation and proactive owner alerting."
        ),
        "tags": ["sampling", "risk scoring", "escalation", "automated audit"],
    },
    {
        "policy_id": "POL-HST-2026",
        "title": "Historical Audit Findings & Recurring Root Cause Compendium (2026)",
        "category": "Historical Audit Findings",
        "version": "2026-Q3",
        "effective_date": "2026-08-01",
        "owner": "Operations Governance Audit",
        "applies_to": "ALL",
        "summary": "Synthesizes top recurring operational compliance gaps across Infrastructure, Security, Network, and Applications.",
        "content": (
            "Finding Pattern #1 (31%): Production Change Requests scheduled or executed with technical approval only, missing documented business owner sign-off.\n"
            "Finding Pattern #2 (27%): Incomplete rollback plans stating general restoration intent without step-by-step commands or RTO validation.\n"
            "Finding Pattern #3 (16%): High-impact network or application incidents logged under generic categories or brief root cause statements.\n"
            "Finding Pattern #4 (14%): Active P1/P2 incidents breaching SLA without proactive escalation.\n"
            "Finding Pattern #5 (12%): Post-implementation validation omitted prior to change closure."
        ),
        "tags": ["historical", "findings", "recurring", "root cause", "change", "approval"],
    },
]


def _build_flagship_tickets() -> list[dict[str, Any]]:
    """Exact signature tickets from Proposal PDF & Prototype."""
    return [
        # 1. Hero Ticket for Section 29 End-to-End Demo (CR001992)
        {
            "ticket_id": "CR001992",
            "ticket_type": "CR",
            "short_description": "Database upgrade — production PostgreSQL cluster",
            "description": "Upgrade production PostgreSQL cluster from 14.x to 16.x to address security compliance and capacity growth requirements.",
            "priority": "P1",
            "category": "Database",
            "business_unit": "Core Operations",
            "assignment_group": "Infrastructure",
            "requester": "Marcus Lim",
            "owner": "Database Operations",
            "resolver": "D. Subramaniam",
            "status": "Scheduled",
            "sla_status": "At Risk",
            "closure_code": "",
            "resolution": "",
            "target_window": "2026-09-23 19:00 UTC",
            "historical_group_risk": 12.0,
            "previous_audit_issues": 1,
            "created_at": "2026-09-21T08:15:00+00:00",
            "work_notes": [
                {"timestamp": "09:10", "author": "John Tan (DB Lead)", "text": "Technical review completed by Database Operations. Risk assessment and impact analysis finalized."},
                {"timestamp": "11:25", "author": "Marcus Lim", "text": "Production change window reserved for 19:00 UTC. Implementation plan steps and owner confirmed."},
                {"timestamp": "14:05", "author": "D. Subramaniam", "text": "Implementation will restore previous configuration if deployment fails, but detailed rollback steps are incomplete."},
                {"timestamp": "15:18", "author": "QA Automation", "text": "Pre-production test passed on staging replica cluster; validation checklist uploaded."},
            ],
            "approvals": [
                {"type": "Technical", "approver": "John Tan (Database Operations)", "status": "Approved", "timestamp": "2026-09-21T09:15:00+00:00", "note": "Architecture and upgrade runbook technically verified."},
            ],
            "attachments": [
                {"name": "Change Risk Assessment.pdf", "section": "Section 1 — Impact Matrix", "content_summary": "High-risk production cluster risk assessment and impact analysis documented."},
                {"name": "Implementation Plan v1.4.pdf", "section": "Section 2 — Execution Steps", "content_summary": "Implementation plan with phased upgrade steps, owner, and reserved change window."},
                {"name": "Implementation Plan v1.4.pdf", "section": "Section 4 — Rollback Notes", "content_summary": "Rollback intent stated ('restore previous configuration'), but step-by-step rollback procedure is incomplete."},
                {"name": "Pre-Prod Validation Checklist.xlsx", "section": "QA Sign-off", "content_summary": "Pre-production staging test plan executed and passed."},
            ],
            "related_tickets": ["PRB001042"],
        },
        # 2. Predictive Audit Hero Ticket (CR002010 — PDF Page 26!)
        {
            "ticket_id": "CR002010",
            "ticket_type": "CR",
            "short_description": "Firewall rule update — remote access routing",
            "description": "Modify perimeter firewall ACL rules to support new enterprise remote access routing policy.",
            "priority": "P1",
            "category": "Security",
            "business_unit": "Enterprise IT",
            "assignment_group": "Security",
            "requester": "Priya Nair",
            "owner": "Security Operations",
            "resolver": "K. Wong",
            "status": "Pending Approval",
            "sla_status": "At Risk",
            "closure_code": "",
            "resolution": "",
            "target_window": "2026-09-23 16:30 UTC",
            "historical_group_risk": 15.0,
            "previous_audit_issues": 3,
            "created_at": "2026-09-22T07:40:00+00:00",
            "work_notes": [
                {"timestamp": "08:30", "author": "K. Wong", "text": "Implementation scheduled soon for 16:30 UTC window; business approval pending."},
                {"timestamp": "09:12", "author": "Security Ops", "text": "No rollback plan detected yet for ACL rule revert. Pre-prod testing skipped due to urgency."},
            ],
            "approvals": [
                {"type": "Technical", "approver": "Security Operations Lead", "status": "Approved", "timestamp": "2026-09-22T08:00:00+00:00", "note": "Rule syntax validated."},
                {"type": "Business", "approver": "CISO Delegate", "status": "Pending", "timestamp": "2026-09-22T08:10:00+00:00", "note": "Awaiting executive approval."},
            ],
            "attachments": [
                {"name": "Firewall Risk Assessment.pdf", "section": "Section 1", "content_summary": "High-risk external firewall change risk assessment documented."},
                {"name": "Firewall Implementation Plan.docx", "section": "Section 2", "content_summary": "Implementation steps and change window documented."},
            ],
            "related_tickets": ["INC004582"],
        },
        # 3. Live Monitor Ticket (CR00201 — PDF Page 24!)
        {
            "ticket_id": "CR00201",
            "ticket_type": "CR",
            "short_description": "Production load balancer failover policy update",
            "description": "Update active-active load balancer health probe thresholds for digital banking ingress.",
            "priority": "P1",
            "category": "Infrastructure",
            "business_unit": "Digital Channels",
            "assignment_group": "Network Operations",
            "requester": "Wei Jie",
            "owner": "Network Engineering",
            "resolver": "R. Mendoza",
            "status": "Scheduled",
            "sla_status": "Within SLA",
            "closure_code": "",
            "resolution": "",
            "target_window": "2026-09-24 01:00 UTC",
            "historical_group_risk": 13.0,
            "previous_audit_issues": 2,
            "created_at": "2026-09-22T10:15:00+00:00",
            "work_notes": [
                {"timestamp": "10:45", "author": "R. Mendoza", "text": "Technical approval completed. Awaiting business approval prior to maintenance window."},
                {"timestamp": "11:20", "author": "R. Mendoza", "text": "Rollback plan verified: revert VIP pool config from versioned Git backup in under 5 minutes."},
                {"timestamp": "12:05", "author": "QA Team", "text": "Staging test passed with zero dropped sessions."},
            ],
            "approvals": [
                {"type": "Technical", "approver": "Network Principal", "status": "Approved", "timestamp": "2026-09-22T10:40:00+00:00", "note": "Peer reviewed."},
            ],
            "attachments": [
                {"name": "LB Risk Assessment.pdf", "section": "Impact", "content_summary": "Risk assessment completed for ingress pool update."},
                {"name": "LB Runbook.md", "section": "Section 2", "content_summary": "Implementation plan and rollback script included."},
            ],
            "related_tickets": [],
        },
        # 4. Live Monitor Ticket (CR00203 — PDF Page 24!)
        {
            "ticket_id": "CR00203",
            "ticket_type": "CR",
            "short_description": "Active Directory schema extension for SSO",
            "description": "Extend enterprise Active Directory schema attributes to enable passwordless SSO federation.",
            "priority": "P2",
            "category": "Security",
            "business_unit": "Enterprise IT",
            "assignment_group": "Infrastructure",
            "requester": "H. Patel",
            "owner": "Identity Engineering",
            "resolver": "H. Patel",
            "status": "Scheduled",
            "sla_status": "Within SLA",
            "closure_code": "",
            "resolution": "",
            "target_window": "2026-09-24 22:00 UTC",
            "historical_group_risk": 11.0,
            "previous_audit_issues": 1,
            "created_at": "2026-09-22T13:00:00+00:00",
            "work_notes": [
                {"timestamp": "13:30", "author": "H. Patel", "text": "Business and technical approvals captured. Implementation window confirmed."},
                {"timestamp": "14:15", "author": "H. Patel", "text": "No rollback plan attached — AD schema extensions require documented authoritative restore procedure."},
                {"timestamp": "15:00", "author": "Identity QA", "text": "Pre-production test passed in isolated forest lab."},
            ],
            "approvals": [
                {"type": "Business", "approver": "VP Enterprise Identity", "status": "Approved", "timestamp": "2026-09-22T13:15:00+00:00", "note": "Approved."},
                {"type": "Technical", "approver": "Directory Architect", "status": "Approved", "timestamp": "2026-09-22T13:20:00+00:00", "note": "Approved."},
            ],
            "attachments": [
                {"name": "AD Risk Assessment.pdf", "section": "Section 1", "content_summary": "Risk assessment and forest impact analysis completed."},
                {"name": "AD Implementation Plan.pdf", "section": "Section 2", "content_summary": "Implementation steps documented."},
            ],
            "related_tickets": [],
        },
        # 5. Audit Queue Medium Risk CR (CR001990 — PDF Page 20!)
        {
            "ticket_id": "CR001990",
            "ticket_type": "CR",
            "short_description": "Core payment gateway TLS certificate rotation",
            "description": "Rotate expiring TLS wildcard certificates on external payment API gateway nodes.",
            "priority": "P2",
            "category": "Applications",
            "business_unit": "Digital Channels",
            "assignment_group": "Applications",
            "requester": "S. Kowalski",
            "owner": "Payments SRE",
            "resolver": "S. Kowalski",
            "status": "Closed",
            "sla_status": "Met",
            "closure_code": "Successful - Validated",
            "resolution": "TLS certificates rotated across all 4 gateway nodes; post-implementation validation smoke tests passed.",
            "target_window": "2026-09-18 02:00 UTC",
            "historical_group_risk": 9.0,
            "previous_audit_issues": 1,
            "created_at": "2026-09-17T09:00:00+00:00",
            "closed_at": "2026-09-18T03:15:00+00:00",
            "work_notes": [
                {"timestamp": "01:45", "author": "S. Kowalski", "text": "Deployment completed successfully across gateway nodes."},
                {"timestamp": "02:15", "author": "S. Kowalski", "text": "Rollback steps were partial in change plan; previous cert bundle archived locally."},
                {"timestamp": "02:40", "author": "S. Kowalski", "text": "Post-implementation validation passed; customer notified of completed maintenance."},
            ],
            "approvals": [
                {"type": "Business", "approver": "Head of Digital Payments", "status": "Approved", "timestamp": "2026-09-17T14:00:00+00:00", "note": "Approved."},
                {"type": "Technical", "approver": "AppSec Lead", "status": "Approved", "timestamp": "2026-09-17T13:30:00+00:00", "note": "Verified."},
            ],
            "attachments": [
                {"name": "TLS Risk Assessment.pdf", "section": "Section 1", "content_summary": "Risk assessment documented."},
                {"name": "Cert Rotation Runbook.pdf", "section": "Section 2", "content_summary": "Implementation plan with node sequence."},
                {"name": "Staging Test Results.pdf", "section": "QA", "content_summary": "Pre-production test passed."},
            ],
            "related_tickets": [],
        },
        # 6. Incident Flagship Ticket (INC0045821 — PDF Pages 6-7!)
        {
            "ticket_id": "INC0045821",
            "ticket_type": "INC",
            "short_description": "Branch network outage — switch hardware failure",
            "description": "Intermittent network connectivity affecting 120 branch users due to core distribution switch module fault.",
            "priority": "P2",
            "category": "Network",
            "business_unit": "Retail Banking",
            "assignment_group": "Network Operations",
            "requester": "Branch Operations Desk",
            "owner": "L2 Network",
            "resolver": "M. Yusof",
            "status": "Closed",
            "sla_status": "Met",
            "closure_code": "Solved (Permanently)",
            "resolution": "Root cause identified as failed optical line card on distribution switch. Network switch module was replaced after approval from network manager; service restored at 14:35 and customer confirmed service recovery.",
            "target_window": "Closed",
            "historical_group_risk": 7.0,
            "previous_audit_issues": 0,
            "created_at": "2026-09-19T11:20:00+00:00",
            "closed_at": "2026-09-19T15:10:00+00:00",
            "work_notes": [
                {"timestamp": "12:05", "author": "M. Yusof", "text": "Root cause identified as failed switch module on SW-BR-04 causing packet loss."},
                {"timestamp": "14:35", "author": "M. Yusof", "text": "Network switch was replaced after approval from network manager. Service restored at 14:35. Customer confirmed service recovery."},
                {"timestamp": "15:02", "author": "M. Yusof", "text": "Deployment completed successfully. Rollback not required after hardware verification."},
            ],
            "approvals": [
                {"type": "Manager", "approver": "Network Manager", "status": "Approved", "timestamp": "2026-09-19T13:10:00+00:00", "note": "Emergency hardware swap authorized."},
            ],
            "attachments": [],
            "related_tickets": [],
        },
        # 7. Critical Active Incident (INC004582 — PDF Pages 11 & 19!)
        {
            "ticket_id": "INC004582",
            "ticket_type": "INC",
            "short_description": "Core banking API latency spike & SLA breach risk",
            "description": "Critical P1 latency degradation on core banking transaction API affecting retail transfers and mobile login.",
            "priority": "P1",
            "category": "Applications",
            "business_unit": "Retail Banking",
            "assignment_group": "Applications",
            "requester": "NOC Monitoring",
            "owner": "Core Banking SRE",
            "resolver": "A. Chen",
            "status": "In Progress",
            "sla_status": "Breached",
            "closure_code": "",
            "resolution": "",
            "target_window": "SLA Breach Active",
            "historical_group_risk": 14.0,
            "previous_audit_issues": 3,
            "created_at": "2026-09-22T14:00:00+00:00",
            "work_notes": [
                {"timestamp": "14:22", "author": "A. Chen", "text": "Investigating elevated p99 latency on payment orchestration microservice."},
                {"timestamp": "16:40", "author": "NOC", "text": "SLA threshold exceeded; no customer communication logged yet and root cause still unknown."},
            ],
            "approvals": [],
            "attachments": [],
            "related_tickets": ["CR002010"],
        },
        # 8. Live Monitor Active Incident (INC00422 — PDF Page 24!)
        {
            "ticket_id": "INC00422",
            "ticket_type": "INC",
            "short_description": "VPN concentrator intermittent session drops",
            "description": "Remote workforce experiencing periodic VPN tunnel disconnects across APAC gateway.",
            "priority": "P2",
            "category": "Network",
            "business_unit": "Corporate Services",
            "assignment_group": "Network Operations",
            "requester": "Service Desk Escalation",
            "owner": "Network Security",
            "resolver": "T. Nguyen",
            "status": "In Progress",
            "sla_status": "At Risk",
            "closure_code": "",
            "resolution": "",
            "target_window": "SLA At Risk (<45m)",
            "historical_group_risk": 12.0,
            "previous_audit_issues": 1,
            "created_at": "2026-09-22T15:10:00+00:00",
            "work_notes": [
                {"timestamp": "15:45", "author": "T. Nguyen", "text": "Identified elevated CPU on VPN-APAC-02; root cause investigation is brief pending packet capture."},
            ],
            "approvals": [],
            "attachments": [],
            "related_tickets": [],
        },
        # 9. Prototype REVIEW Incident (INC0045810)
        {
            "ticket_id": "INC0045810",
            "ticket_type": "INC",
            "short_description": "Batch job failed overnight — settlement feed",
            "description": "Overnight settlement batch job failed with exit code 137 causing delayed downstream reporting.",
            "priority": "P2",
            "category": "Applications",
            "business_unit": "Core Operations",
            "assignment_group": "Applications",
            "requester": "Batch Control",
            "owner": "Batch Operations",
            "resolver": "V. Rao",
            "status": "Closed",
            "sla_status": "Met",
            "closure_code": "Solved (Workaround)",
            "resolution": "Batch job restarted manually and downstream files caught up within morning SLA.",
            "target_window": "Closed",
            "historical_group_risk": 10.0,
            "previous_audit_issues": 1,
            "created_at": "2026-09-20T05:30:00+00:00",
            "closed_at": "2026-09-20T07:50:00+00:00",
            "work_notes": [
                {"timestamp": "06:15", "author": "V. Rao", "text": "Job restarted successfully and settlement file delivered."},
                {"timestamp": "06:40", "author": "V. Rao", "text": "Root cause note is brief and unclear; container OOM suspected but not confirmed."},
                {"timestamp": "07:20", "author": "V. Rao", "text": "Customer notified of successful recovery and file receipt confirmed."},
            ],
            "approvals": [],
            "attachments": [],
            "related_tickets": [],
        },
        # 10. Service Request (SR002134 — Prototype + PDF Page 19!)
        {
            "ticket_id": "SR002134",
            "ticket_type": "SR",
            "short_description": "Executive laptop replacement & data migration",
            "description": "Standard encrypted laptop replacement request with profile migration and asset return.",
            "priority": "P3",
            "category": "End User",
            "business_unit": "Corporate Services",
            "assignment_group": "Service Desk",
            "requester": "Elena Gomez",
            "owner": "EU Workplace",
            "resolver": "F. Hassan",
            "status": "Closed",
            "sla_status": "Met",
            "closure_code": "Fulfilled - Verified",
            "resolution": "Manager authorization verified; encrypted workstation issued and legacy asset collected.",
            "target_window": "Closed",
            "historical_group_risk": 5.0,
            "previous_audit_issues": 0,
            "created_at": "2026-09-18T09:30:00+00:00",
            "closed_at": "2026-09-19T16:00:00+00:00",
            "work_notes": [
                {"timestamp": "10:15", "author": "F. Hassan", "text": "Manager authorization validated from Department Head."},
                {"timestamp": "15:40", "author": "F. Hassan", "text": "Device issued and old device returned. User confirmed workstation readiness."},
            ],
            "approvals": [
                {"type": "Manager", "approver": "Director Corporate Services", "status": "Approved", "timestamp": "2026-09-18T10:00:00+00:00", "note": "Standard refresh approved."},
            ],
            "attachments": [],
            "related_tickets": [],
        },
        # 11. Auto-Pass Service Request (SR21348 — PDF Page 20!)
        {
            "ticket_id": "SR21348",
            "ticket_type": "SR",
            "short_description": "Enterprise BI analytics license provisioning",
            "description": "Provision standard PowerBI Pro viewer license for financial reporting analyst.",
            "priority": "P3",
            "category": "End User",
            "business_unit": "Retail Banking",
            "assignment_group": "Service Desk",
            "requester": "C. Ong",
            "owner": "License Management",
            "resolver": "N. Zainal",
            "status": "Closed",
            "sla_status": "Met",
            "closure_code": "Fulfilled - Verified",
            "resolution": "License assigned after manager authorization; user confirmed dashboard access.",
            "target_window": "Closed",
            "historical_group_risk": 4.0,
            "previous_audit_issues": 0,
            "created_at": "2026-09-20T10:00:00+00:00",
            "closed_at": "2026-09-20T13:30:00+00:00",
            "work_notes": [
                {"timestamp": "10:40", "author": "N. Zainal", "text": "Manager authorization confirmed in IAM portal."},
                {"timestamp": "13:15", "author": "N. Zainal", "text": "License assigned and requester notified; user confirmed successful sign-in."},
            ],
            "approvals": [
                {"type": "Manager", "approver": "VP Retail Analytics", "status": "Approved", "timestamp": "2026-09-20T10:20:00+00:00", "note": "Approved."},
            ],
            "attachments": [],
            "related_tickets": [],
        },
        # 12. Live Monitor Service Request (SR00119 — PDF Page 24!)
        {
            "ticket_id": "SR00119",
            "ticket_type": "SR",
            "short_description": "Production read-only database access request",
            "description": "Grant temporary read-only query access on reporting database replica for reconciliation audit.",
            "priority": "P2",
            "category": "Security",
            "business_unit": "Core Operations",
            "assignment_group": "Security",
            "requester": "Finance Reconciliation",
            "owner": "IAM Operations",
            "resolver": "E. Tan",
            "status": "In Progress",
            "sla_status": "Within SLA",
            "closure_code": "",
            "resolution": "",
            "target_window": "2026-09-23 18:00 UTC",
            "historical_group_risk": 11.0,
            "previous_audit_issues": 1,
            "created_at": "2026-09-22T11:00:00+00:00",
            "work_notes": [
                {"timestamp": "11:45", "author": "E. Tan", "text": "Access provisioned in staging; closure documentation incomplete and data owner approval missing."},
            ],
            "approvals": [],
            "attachments": [],
            "related_tickets": [],
        },
    ]


def _build_synthetic_fleet() -> list[dict[str, Any]]:
    """Generates 48 additional realistic INC/SR/CR tickets across Apr–Sep 2026 for 60 total."""
    months = ["2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09"]
    bus = ["Retail Banking", "Enterprise IT", "Digital Channels", "Core Operations", "Corporate Services"]
    groups = ["Infrastructure", "Applications", "Security", "Network Operations", "Service Desk"]

    inc_templates = [
        ("DNS resolution failure on internal app subnet", "Network", "Network Operations", "Root cause identified as corrupted DNS forwarder cache after patch.", "Cleared forwarder cache and synced secondary zone; service restored."),
        ("ERP invoice export timeout for regional branch", "Applications", "Applications", "Root cause confirmed as database deadlock in nightly lock table.", "Cleared blocking session and optimized index; service restored cleanly."),
        ("Storage array latency warning on VM cluster", "Infrastructure", "Infrastructure", "Root cause traced to degraded NVMe drive triggering rebuild.", "Replaced faulty drive and verified SAN latency returned to normal."),
        ("SSO token validation error on mobile portal", "Security", "Security", "Root cause traced to clock skew on secondary federation node.", "Resynchronized NTP daemon across cluster; login flow verified."),
        ("Core switch uplink flap at data center B", "Network", "Network Operations", "Root cause confirmed as faulty SFP transceiver on port Gi1/0/48.", "Replaced SFP transceiver and validated stable BGP session."),
        ("API gateway 502 errors during peak checkout", "Applications", "Applications", "Root cause identified as memory leak in upstream worker pool.", "Recycled worker pods and patched connection limit; p99 normalized."),
        ("Backup job failure on core ledger server", "Infrastructure", "Infrastructure", "Root cause identified as stale VSS snapshot lock.", "Cleared shadow copy lock and completed incremental backup verification."),
        ("Email relay delay affecting external alerts", "Infrastructure", "Service Desk", "Root cause confirmed as TLS cipher mismatch on partner relay.", "Updated outbound connector cipher suite and drained mail queue cleanly."),
    ]
    sr_templates = [
        ("New joiner standard IT onboarding bundle", "End User", "Service Desk", "Hardware, mailbox, and SSO account provisioned per onboarding checklist."),
        ("Privileged PAM vault access for DBA", "Security", "Security", "Time-bound PAM role provisioned and verified with vault audit logging."),
        ("Cloud sandbox Kubernetes namespace creation", "Infrastructure", "Infrastructure", "Namespace provisioned with RBAC quotas and cost allocation tags."),
        ("CRM sales license upgrade — Enterprise tier", "End User", "Service Desk", "License assigned in identity directory and confirmed with requester."),
        ("Firewall port opening for internal QA runner", "Security", "Network Operations", "Restricted internal ACL rule provisioned and validated via telnet probe."),
        ("Shared mailbox creation for compliance team", "End User", "Service Desk", "Shared mailbox created with delegated permissions and retention policy."),
        ("Production SFTP service account renewal", "Applications", "Applications", "SSH key rotated and service account credentials vaulted securely."),
        ("Virtual desktop VDI pool expansion request", "Infrastructure", "Infrastructure", "Additional VDI images provisioned and user group entitlements verified."),
    ]
    cr_templates = [
        ("Kubernetes control plane minor upgrade v1.30", "Infrastructure", "Infrastructure"),
        ("Core payment API microservice release v4.8", "Applications", "Applications"),
        ("Zero-trust WAF rule tuning on public ingress", "Security", "Security"),
        ("MPLS WAN circuit cutover for regional hub", "Network", "Network Operations"),
        ("Oracle standby database failover drill", "Database", "Infrastructure"),
        ("Enterprise IAM MFA policy enforcement rollout", "Security", "Security"),
        ("Customer portal Redis cache cluster scaling", "Applications", "Applications"),
        ("Core router firmware security patching", "Network", "Network Operations"),
    ]

    tickets: list[dict[str, Any]] = []
    # 16 INC tickets across 6 months (earlier months have slightly higher defect rate to show realistic compliance improvement trend!)
    for i in range(16):
        m_idx = i % len(months)
        month = months[m_idx]
        day = 4 + (i * 3) % 22
        title, cat, grp, rc, res = inc_templates[i % len(inc_templates)]
        bu = bus[i % len(bus)]
        tid = f"INC0046{10 + i:02d}"

        # Introduce controlled, realistic defects (more in Apr/May, fewer in Aug/Sep -> upward compliance trend)
        missing_rc = (i in {0, 6})
        brief_rc = (i in {1, 7})
        missing_comm = (i in {2, 8})
        sla_breach = (i == 0)
        sla_risk = (i == 13)
        miscat = (i == 3)

        notes = []
        if missing_rc:
            notes.append({"timestamp": "10:15", "author": "L2 Engineer", "text": "Service restarted quickly to restore availability."})
        elif brief_rc:
            notes.append({"timestamp": "10:15", "author": "L2 Engineer", "text": "Root cause note is brief and tbd pending deeper log analysis."})
        else:
            notes.append({"timestamp": "10:15", "author": "L2 Engineer", "text": rc})

        notes.append({"timestamp": "11:30", "author": "L2 Engineer", "text": res})
        if not missing_comm:
            notes.append({"timestamp": "11:45", "author": "L2 Engineer", "text": "Customer notified and customer confirmed service recovery."})

        tickets.append(
            {
                "ticket_id": tid,
                "ticket_type": "INC",
                "short_description": f"{title} #{i + 1}",
                "description": f"Operational incident reported for {bu}: {title}.",
                "priority": "P2" if i % 3 == 0 else "P3",
                "category": "General" if miscat else cat,
                "business_unit": bu,
                "assignment_group": grp,
                "requester": "Enterprise Monitoring",
                "owner": f"{grp} L2",
                "resolver": f"Engineer {(i % 6) + 1}",
                "status": "In Progress" if i == 13 else "Closed",
                "sla_status": "Breached" if sla_breach else ("At Risk" if sla_risk else "Met"),
                "closure_code": "" if i == 13 else "Solved (Permanently)",
                "resolution": "" if i == 13 else res,
                "target_window": "SLA Monitoring" if i == 13 else "Closed",
                "historical_group_risk": 11.0 if grp in {"Network Operations", "Security"} else 7.0,
                "previous_audit_issues": 2 if (missing_rc or sla_breach) else 0,
                "created_at": f"{month}-{day:02d}T09:00:00+00:00",
                "closed_at": None if i == 13 else f"{month}-{day:02d}T12:30:00+00:00",
                "work_notes": notes,
                "approvals": [],
                "attachments": [],
                "related_tickets": [f"PRB001{100 + i}"] if not missing_rc else [],
            }
        )

    # 16 SR tickets across 6 months
    for i in range(16):
        m_idx = i % len(months)
        month = months[m_idx]
        day = 5 + (i * 2) % 21
        title, cat, grp, fulfillment_note = sr_templates[i % len(sr_templates)]
        bu = bus[(i + 1) % len(bus)]
        tid = f"SR0022{10 + i:02d}"

        missing_auth = (i in {0, 6})
        incomplete_doc = (i in {1, 7, 12})
        sla_breach = (i == 2)

        notes = [
            {"timestamp": "09:40", "author": "Fulfillment Specialist", "text": fulfillment_note},
        ]
        if incomplete_doc:
            notes.append({"timestamp": "11:00", "author": "Fulfillment Specialist", "text": "Closure documentation incomplete pending asset checklist."})
        else:
            notes.append({"timestamp": "11:00", "author": "Fulfillment Specialist", "text": "Request fulfilled and requester confirmed completion."})

        approvals = (
            []
            if missing_auth
            else [
                {
                    "type": "Manager",
                    "approver": f"Manager {bu}",
                    "status": "Approved",
                    "timestamp": f"{month}-{day:02d}T08:45:00+00:00",
                    "note": "Authorization approved.",
                }
            ]
        )

        tickets.append(
            {
                "ticket_id": tid,
                "ticket_type": "SR",
                "short_description": f"{title} ({bu})",
                "description": f"Catalog service request submitted by {bu} for {title.lower()}.",
                "priority": "P3" if i % 4 != 0 else "P2",
                "category": cat,
                "business_unit": bu,
                "assignment_group": grp,
                "requester": f"Staff Member {i + 1}",
                "owner": grp,
                "resolver": f"Analyst {(i % 5) + 1}",
                "status": "Closed",
                "sla_status": "Breached" if sla_breach else "Met",
                "closure_code": "Fulfilled - Verified",
                "resolution": fulfillment_note,
                "target_window": "Closed",
                "historical_group_risk": 9.0 if grp == "Security" else 5.0,
                "previous_audit_issues": 1 if missing_auth else 0,
                "created_at": f"{month}-{day:02d}T08:30:00+00:00",
                "closed_at": f"{month}-{day:02d}T14:20:00+00:00",
                "work_notes": notes,
                "approvals": approvals,
                "attachments": [],
                "related_tickets": [],
            }
        )

    # 16 CR tickets across 6 months
    for i in range(16):
        m_idx = i % len(months)
        month = months[m_idx]
        day = 6 + (i * 2) % 20
        title, cat, grp = cr_templates[i % len(cr_templates)]
        bu = bus[(i + 2) % len(bus)]
        tid = f"CR0018{10 + i:02d}"

        missing_biz = (i in {0, 2, 6})
        partial_rollback = (i in {1, 7, 13})
        missing_pir = (i in {0, 3})
        is_scheduled = (i == 14)

        approvals = [
            {
                "type": "Technical",
                "approver": f"{grp} Principal",
                "status": "Approved",
                "timestamp": f"{month}-{day:02d}T09:00:00+00:00",
                "note": "Technical review completed.",
            }
        ]
        if not missing_biz:
            approvals.append(
                {
                    "type": "Business",
                    "approver": f"VP {bu}",
                    "status": "Approved",
                    "timestamp": f"{month}-{day:02d}T10:30:00+00:00",
                    "note": "Business approval granted.",
                }
            )

        attachments = [
            {"name": "Risk Assessment.pdf", "section": "Section 1", "content_summary": f"Risk assessment and impact analysis for {title}."},
            {"name": "Implementation Plan.pdf", "section": "Section 2", "content_summary": "Detailed change steps, owner, and maintenance window documented."},
            {
                "name": "Implementation Plan.pdf",
                "section": "Section 4 — Rollback",
                "content_summary": (
                    "Rollback plan intent noted but detailed steps are incomplete."
                    if partial_rollback
                    else "Complete rollback plan with verified restore script and 10-minute RTO."
                ),
            },
            {"name": "Pre-Prod Test Checklist.pdf", "section": "QA", "content_summary": "Pre-production staging validation passed with zero regressions."},
        ]
        notes = [
            {"timestamp": "19:00", "author": f"{grp} Lead", "text": "Implementation window started; deployment completed successfully."},
        ]
        if not missing_pir and not is_scheduled:
            notes.append({"timestamp": "20:15", "author": f"{grp} Lead", "text": "Post-implementation validation passed; smoke tests green and customer notified."})

        tickets.append(
            {
                "ticket_id": tid,
                "ticket_type": "CR",
                "short_description": f"{title} — Wave {(i % 4) + 1}",
                "description": f"Scheduled production change for {bu}: {title}.",
                "priority": "P1" if i % 4 == 0 else "P2",
                "category": cat,
                "business_unit": bu,
                "assignment_group": grp,
                "requester": f"Change Lead {i + 1}",
                "owner": grp,
                "resolver": f"SRE {(i % 5) + 1}",
                "status": "Scheduled" if is_scheduled else "Closed",
                "sla_status": "Within SLA" if is_scheduled else "Met",
                "closure_code": "" if is_scheduled else "Successful - Validated",
                "resolution": "" if (missing_pir or is_scheduled) else "Change deployed and post-implementation validation completed cleanly.",
                "target_window": f"{month}-{day + 1:02d} 20:00 UTC" if is_scheduled else "Closed",
                "historical_group_risk": 12.0 if grp in {"Security", "Network Operations"} else 8.0,
                "previous_audit_issues": 2 if missing_biz else 0,
                "created_at": f"{month}-{day:02d}T08:00:00+00:00",
                "closed_at": None if is_scheduled else f"{month}-{day:02d}T21:00:00+00:00",
                "work_notes": notes,
                "approvals": approvals,
                "attachments": attachments,
                "related_tickets": [],
            }
        )

    return tickets


def seed_database(conn: sqlite3.Connection, force: bool = False) -> dict[str, int]:
    """Populates database with criteria, policies, 60 tickets, AI audits, and sample QC history."""
    existing = conn.execute("SELECT COUNT(*) AS c FROM tickets").fetchone()["c"]
    if existing > 0 and not force:
        refresh_rag_index(conn)
        return {"tickets": existing, "seeded": 0}

    if force:
        reset_db_tables()

    get_governance_config(conn)

    # 1. Seed Audit Criteria
    for c in DEFAULT_CRITERIA:
        conn.execute(
            """
            INSERT OR REPLACE INTO audit_criteria (
                criterion_id, audit_type, criterion_name, requirement, rule,
                policy_ref, method, weight, severity_if_failed, active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                c["criterion_id"],
                c["audit_type"],
                c["criterion_name"],
                c["requirement"],
                c["rule"],
                c["policy_ref"],
                c["method"],
                c["weight"],
                c["severity_if_failed"],
            ),
        )

    # 2. Seed Policy Knowledge Base & Build RAG Index
    for p in DEFAULT_POLICIES:
        conn.execute(
            """
            INSERT OR REPLACE INTO policy_documents (
                policy_id, title, category, version, effective_date, owner,
                applies_to, summary, content, tags_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                p["policy_id"],
                p["title"],
                p["category"],
                p["version"],
                p["effective_date"],
                p["owner"],
                p["applies_to"],
                p["summary"],
                p["content"],
                json.dumps(p["tags"]),
            ),
        )
    refresh_rag_index(conn)

    # 3. Seed 60 Tickets & Audit Each Through the Multi-Agent Orchestrator
    all_tickets = _build_flagship_tickets() + _build_synthetic_fleet()
    now = utc_now()
    for t in all_tickets:
        conn.execute(
            """
            INSERT OR REPLACE INTO tickets (
                ticket_id, ticket_type, short_description, description, priority, category,
                business_unit, assignment_group, requester, owner, resolver, status,
                sla_status, closure_code, resolution, work_notes_json, approvals_json,
                attachments_json, related_tickets_json, target_window,
                historical_group_risk, previous_audit_issues, created_at, updated_at, closed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                t["ticket_id"],
                t["ticket_type"],
                t["short_description"],
                t["description"],
                t["priority"],
                t["category"],
                t["business_unit"],
                t["assignment_group"],
                t["requester"],
                t["owner"],
                t["resolver"],
                t["status"],
                t["sla_status"],
                t["closure_code"],
                t["resolution"],
                json.dumps(t["work_notes"]),
                json.dumps(t["approvals"]),
                json.dumps(t["attachments"]),
                json.dumps(t["related_tickets"]),
                t["target_window"],
                t["historical_group_risk"],
                t["previous_audit_issues"],
                t["created_at"],
                now,
                t.get("closed_at"),
            ),
        )
        run_ticket_audit(conn, t["ticket_id"], actor="AuditIQ Initial Seed", broadcast=False)

    # 4. Seed realistic Closed-Loop Learning overrides & QC reviews on non-demo historical tickets
    _seed_qc_and_feedback(conn)

    return {"tickets": len(all_tickets), "seeded": 1}


def _seed_qc_and_feedback(conn: sqlite3.Connection) -> None:
    """Seeds realistic auditor overrides and QC reviews so QC Intelligence & Closed-Loop Learning are rich."""
    # Find open findings on historical tickets (never touch CR001992 or CR002010 so demos remain clean!)
    sample_overrides = [
        ("CR001990", "S. Tan", "Rollback certificate bundle was verified in GitOps vault outside ServiceNow attachment.", "Evidence Extraction"),
        ("INC004611", "S. Tan", "Root cause analysis was linked inside external APM incident report; verified acceptable.", "RAG Retrieval"),
        ("SR002211", "M. Lee", "Requester email confirmation existed in Service Desk thread; updated extraction rule target.", "Evidence Extraction"),
        ("CR001811", "S. Tan", "Emergency patch rollback verified via automated blue/green switch.", "Audit Rules"),
        ("INC004617", "J. Lim", "Root cause confirmed via vendor advisory attached post-closure.", "Prompts"),
    ]
    for tid, auditor, reason, target in sample_overrides:
        f_row = conn.execute(
            "SELECT finding_id FROM findings WHERE ticket_id = ? AND status = 'Open' LIMIT 1",
            (tid,),
        ).fetchone()
        if f_row:
            apply_finding_action(
                conn,
                tid,
                f_row["finding_id"],
                decision="OVERRIDE_PASS",
                note=reason,
                auditor=auditor,
                role="Auditor",
                improvement_target=target,
            )

    # Mark two audits as QC Disputed and several as QC Verified
    disputed_tickets = [
        ("CR001990", "L. Chen (QC Lead)", "External GitOps rollback proof must be attached inside the ITSM ticket per Change Policy v3.2 §5.3."),
        ("CR001811", "L. Chen (QC Lead)", "Override granted without citing automated blue/green verification timestamp; re-calibration needed."),
    ]
    for tid, reviewer, note in disputed_tickets:
        conn.execute(
            "UPDATE audits SET qc_status = 'Disputed', qc_reviewer = ?, qc_note = ? WHERE ticket_id = ?",
            (reviewer, note, tid),
        )

    verified_tickets = ["INC0045821", "SR002134", "SR21348", "CR001812", "CR001814"]
    for tid in verified_tickets:
        conn.execute(
            "UPDATE audits SET qc_status = 'Verified', qc_reviewer = 'L. Chen (QC Lead)', qc_note = 'Audit evidence and scoring verified.' WHERE ticket_id = ?",
            (tid,),
        )


def ensure_seeded() -> dict[str, int]:
    with db_session() as conn:
        return seed_database(conn, force=False)
