-- AuditIQ — Enterprise PostgreSQL Schema (Proposal Section 20 & Section 22)
-- Run this script when deploying AuditIQ against PostgreSQL (e.g. via docker-compose.yml).

CREATE TABLE IF NOT EXISTS tickets (
    ticket_id VARCHAR(32) PRIMARY KEY,
    ticket_type VARCHAR(8) NOT NULL CHECK (ticket_type IN ('INC', 'SR', 'CR')),
    short_description TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    priority VARCHAR(8) NOT NULL DEFAULT 'P3',
    category VARCHAR(64) NOT NULL DEFAULT 'General',
    business_unit VARCHAR(64) NOT NULL DEFAULT 'Enterprise IT',
    assignment_group VARCHAR(64) NOT NULL DEFAULT 'Service Desk',
    requester VARCHAR(128) NOT NULL DEFAULT 'Operations User',
    owner VARCHAR(128) NOT NULL DEFAULT 'Operations Team',
    resolver VARCHAR(128) NOT NULL DEFAULT '',
    status VARCHAR(32) NOT NULL DEFAULT 'Closed',
    sla_status VARCHAR(32) NOT NULL DEFAULT 'Met',
    closure_code VARCHAR(64) NOT NULL DEFAULT '',
    resolution TEXT NOT NULL DEFAULT '',
    work_notes_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    approvals_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    attachments_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    related_tickets_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    target_window VARCHAR(64) NOT NULL DEFAULT '',
    historical_group_risk DOUBLE PRECISION NOT NULL DEFAULT 10.0,
    previous_audit_issues INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS audit_criteria (
    criterion_id VARCHAR(32) PRIMARY KEY,
    audit_type VARCHAR(8) NOT NULL CHECK (audit_type IN ('INC', 'SR', 'CR')),
    criterion_name VARCHAR(128) NOT NULL,
    requirement VARCHAR(128) NOT NULL,
    rule TEXT NOT NULL,
    policy_ref VARCHAR(128) NOT NULL DEFAULT 'Enterprise Audit Standard v1.0',
    method VARCHAR(24) NOT NULL CHECK (method IN ('deterministic', 'ai')),
    weight DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    severity_if_failed VARCHAR(16) NOT NULL DEFAULT 'MEDIUM',
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS audits (
    audit_id VARCHAR(32) PRIMARY KEY,
    ticket_id VARCHAR(32) NOT NULL UNIQUE REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    audit_type VARCHAR(8) NOT NULL,
    audit_score DOUBLE PRECISION NOT NULL,
    risk_score DOUBLE PRECISION NOT NULL,
    risk_band VARCHAR(16) NOT NULL,
    risk_breakdown_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    predicted_failure_prob DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    predictive_factors_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    decision VARCHAR(16) NOT NULL CHECK (decision IN ('PASS', 'FAIL', 'REVIEW')),
    sampling_tier VARCHAR(32) NOT NULL DEFAULT 'Automated Audit',
    ai_confidence DOUBLE PRECISION NOT NULL DEFAULT 90.0,
    ai_summary TEXT NOT NULL DEFAULT '',
    status VARCHAR(32) NOT NULL DEFAULT 'Auto-Closed',
    auditor VARCHAR(128) NOT NULL DEFAULT 'Unassigned',
    qc_status VARCHAR(32) NOT NULL DEFAULT 'Not Required',
    qc_reviewer VARCHAR(128) NOT NULL DEFAULT '',
    qc_note TEXT NOT NULL DEFAULT '',
    agent_trace_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    highlights_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    audit_duration_min DOUBLE PRECISION NOT NULL DEFAULT 4.5,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_results (
    result_id VARCHAR(48) PRIMARY KEY,
    audit_id VARCHAR(32) NOT NULL REFERENCES audits(audit_id) ON DELETE CASCADE,
    criterion_id VARCHAR(32) NOT NULL REFERENCES audit_criteria(criterion_id),
    criterion_name VARCHAR(128) NOT NULL,
    requirement VARCHAR(128) NOT NULL DEFAULT '',
    method VARCHAR(24) NOT NULL,
    policy_ref VARCHAR(128) NOT NULL,
    status VARCHAR(16) NOT NULL CHECK (status IN ('PASS', 'FAIL', 'REVIEW')),
    confidence DOUBLE PRECISION NOT NULL,
    confidence_tier VARCHAR(32) NOT NULL,
    reason TEXT NOT NULL,
    detected_evidence TEXT NOT NULL DEFAULT '',
    missing_evidence TEXT NOT NULL DEFAULT '',
    evidence_source VARCHAR(128) NOT NULL DEFAULT '',
    searched_sources_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    recommendation TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS findings (
    finding_id VARCHAR(48) PRIMARY KEY,
    audit_id VARCHAR(32) NOT NULL REFERENCES audits(audit_id) ON DELETE CASCADE,
    ticket_id VARCHAR(32) NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    criterion_id VARCHAR(32) NOT NULL,
    criterion_name VARCHAR(128) NOT NULL,
    policy_ref VARCHAR(128) NOT NULL,
    severity VARCHAR(16) NOT NULL,
    ai_status VARCHAR(16) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'Open',
    confidence DOUBLE PRECISION NOT NULL,
    description TEXT NOT NULL,
    detected_evidence TEXT NOT NULL DEFAULT '',
    missing_evidence TEXT NOT NULL DEFAULT '',
    recommendation TEXT NOT NULL DEFAULT '',
    human_decision VARCHAR(32) NOT NULL DEFAULT '',
    human_note TEXT NOT NULL DEFAULT '',
    decided_by VARCHAR(128) NOT NULL DEFAULT '',
    decided_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS feedback (
    feedback_id VARCHAR(48) PRIMARY KEY,
    audit_id VARCHAR(32) NOT NULL REFERENCES audits(audit_id) ON DELETE CASCADE,
    ticket_id VARCHAR(32) NOT NULL,
    criterion_name VARCHAR(128) NOT NULL,
    ai_decision VARCHAR(32) NOT NULL,
    auditor_decision VARCHAR(32) NOT NULL,
    reason TEXT NOT NULL,
    improvement_target VARCHAR(64) NOT NULL DEFAULT 'Audit Rules',
    auditor VARCHAR(128) NOT NULL,
    applied_status VARCHAR(32) NOT NULL DEFAULT 'Captured',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_trail (
    trail_id VARCHAR(48) PRIMARY KEY,
    ticket_id VARCHAR(32) NOT NULL,
    audit_id VARCHAR(32) NOT NULL DEFAULT '',
    who VARCHAR(128) NOT NULL,
    role VARCHAR(64) NOT NULL,
    what TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    rule VARCHAR(128) NOT NULL DEFAULT '',
    evidence TEXT NOT NULL DEFAULT '',
    ai_model VARCHAR(128) NOT NULL DEFAULT '',
    confidence DOUBLE PRECISION NOT NULL DEFAULT 100.0,
    decision VARCHAR(32) NOT NULL DEFAULT '',
    human_override BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS policy_documents (
    policy_id VARCHAR(32) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    category VARCHAR(64) NOT NULL,
    version VARCHAR(32) NOT NULL,
    effective_date VARCHAR(32) NOT NULL,
    owner VARCHAR(128) NOT NULL,
    applies_to VARCHAR(16) NOT NULL DEFAULT 'ALL',
    summary TEXT NOT NULL,
    content TEXT NOT NULL,
    tags_json JSONB NOT NULL DEFAULT '[]'::jsonb
);

CREATE TABLE IF NOT EXISTS monitoring_alerts (
    alert_id VARCHAR(48) PRIMARY KEY,
    ticket_id VARCHAR(32) NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    severity VARCHAR(16) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    predicted_risk DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    status VARCHAR(32) NOT NULL DEFAULT 'Active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS governance_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    confidence_auto INTEGER NOT NULL DEFAULT 95,
    confidence_recommend INTEGER NOT NULL DEFAULT 80,
    critical_risk_threshold INTEGER NOT NULL DEFAULT 80,
    high_risk_threshold INTEGER NOT NULL DEFAULT 60,
    medium_risk_threshold INTEGER NOT NULL DEFAULT 35,
    medium_sampling_pct INTEGER NOT NULL DEFAULT 25,
    proactive_alerts_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    auto_close_low_risk BOOLEAN NOT NULL DEFAULT TRUE,
    updated_by VARCHAR(128) NOT NULL DEFAULT 'Governance Admin',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
