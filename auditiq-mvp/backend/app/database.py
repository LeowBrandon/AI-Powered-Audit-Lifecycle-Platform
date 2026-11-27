"""SQLite relational database layer implementing Section 20 Data Model & Section 22 Governance Trail.

Designed with standard ANSI SQL so the schema maps 1:1 to schema/postgresql.sql
for enterprise PostgreSQL deployment.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from app.config import DEFAULT_DB_PATH, settings


def _resolve_sqlite_path() -> Path:
    url = settings.database_url
    if url.startswith("sqlite:///"):
        raw = url.replace("sqlite:///", "", 1)
        if raw == ":memory:":
            return Path(":memory:")
        return Path(raw)
    return DEFAULT_DB_PATH


DB_PATH: Path = _resolve_sqlite_path()


def set_db_path(path: Path | str) -> None:
    """Allow tests to point the database at an isolated temporary file."""
    global DB_PATH
    DB_PATH = Path(path)


def get_connection() -> sqlite3.Connection:
    path_str = str(DB_PATH)
    if path_str != ":memory:":
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path_str, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def db_session() -> Iterator[sqlite3.Connection]:
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id TEXT PRIMARY KEY,
    ticket_type TEXT NOT NULL CHECK (ticket_type IN ('INC', 'SR', 'CR')),
    short_description TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    priority TEXT NOT NULL DEFAULT 'P3',
    category TEXT NOT NULL DEFAULT 'General',
    business_unit TEXT NOT NULL DEFAULT 'Enterprise IT',
    assignment_group TEXT NOT NULL DEFAULT 'Service Desk',
    requester TEXT NOT NULL DEFAULT 'Operations User',
    owner TEXT NOT NULL DEFAULT 'Operations Team',
    resolver TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'Closed',
    sla_status TEXT NOT NULL DEFAULT 'Met',
    closure_code TEXT NOT NULL DEFAULT '',
    resolution TEXT NOT NULL DEFAULT '',
    work_notes_json TEXT NOT NULL DEFAULT '[]',
    approvals_json TEXT NOT NULL DEFAULT '[]',
    attachments_json TEXT NOT NULL DEFAULT '[]',
    related_tickets_json TEXT NOT NULL DEFAULT '[]',
    target_window TEXT NOT NULL DEFAULT '',
    historical_group_risk REAL NOT NULL DEFAULT 10.0,
    previous_audit_issues INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    closed_at TEXT
);

CREATE TABLE IF NOT EXISTS audit_criteria (
    criterion_id TEXT PRIMARY KEY,
    audit_type TEXT NOT NULL CHECK (audit_type IN ('INC', 'SR', 'CR')),
    criterion_name TEXT NOT NULL,
    requirement TEXT NOT NULL,
    rule TEXT NOT NULL,
    policy_ref TEXT NOT NULL DEFAULT 'Enterprise Audit Standard v1.0',
    method TEXT NOT NULL CHECK (method IN ('deterministic', 'ai')),
    weight REAL NOT NULL DEFAULT 1.0,
    severity_if_failed TEXT NOT NULL DEFAULT 'MEDIUM',
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS audits (
    audit_id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL UNIQUE REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    audit_type TEXT NOT NULL,
    audit_score REAL NOT NULL,
    risk_score REAL NOT NULL,
    risk_band TEXT NOT NULL,
    risk_breakdown_json TEXT NOT NULL DEFAULT '{}',
    predicted_failure_prob REAL NOT NULL DEFAULT 0.0,
    predictive_factors_json TEXT NOT NULL DEFAULT '[]',
    decision TEXT NOT NULL CHECK (decision IN ('PASS', 'FAIL', 'REVIEW')),
    sampling_tier TEXT NOT NULL DEFAULT 'Automated Audit',
    ai_confidence REAL NOT NULL DEFAULT 90.0,
    ai_summary TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'Auto-Closed',
    auditor TEXT NOT NULL DEFAULT 'Unassigned',
    qc_status TEXT NOT NULL DEFAULT 'Not Required',
    qc_reviewer TEXT NOT NULL DEFAULT '',
    qc_note TEXT NOT NULL DEFAULT '',
    agent_trace_json TEXT NOT NULL DEFAULT '[]',
    highlights_json TEXT NOT NULL DEFAULT '[]',
    audit_duration_min REAL NOT NULL DEFAULT 4.5,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_results (
    result_id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES audits(audit_id) ON DELETE CASCADE,
    criterion_id TEXT NOT NULL REFERENCES audit_criteria(criterion_id),
    criterion_name TEXT NOT NULL,
    requirement TEXT NOT NULL DEFAULT '',
    method TEXT NOT NULL,
    policy_ref TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL', 'REVIEW')),
    confidence REAL NOT NULL,
    confidence_tier TEXT NOT NULL,
    reason TEXT NOT NULL,
    detected_evidence TEXT NOT NULL DEFAULT '',
    missing_evidence TEXT NOT NULL DEFAULT '',
    evidence_source TEXT NOT NULL DEFAULT '',
    searched_sources_json TEXT NOT NULL DEFAULT '[]',
    recommendation TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS findings (
    finding_id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES audits(audit_id) ON DELETE CASCADE,
    ticket_id TEXT NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    criterion_id TEXT NOT NULL,
    criterion_name TEXT NOT NULL,
    policy_ref TEXT NOT NULL,
    severity TEXT NOT NULL,
    ai_status TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Open',
    confidence REAL NOT NULL,
    description TEXT NOT NULL,
    detected_evidence TEXT NOT NULL DEFAULT '',
    missing_evidence TEXT NOT NULL DEFAULT '',
    recommendation TEXT NOT NULL DEFAULT '',
    human_decision TEXT NOT NULL DEFAULT '',
    human_note TEXT NOT NULL DEFAULT '',
    decided_by TEXT NOT NULL DEFAULT '',
    decided_at TEXT
);

CREATE TABLE IF NOT EXISTS feedback (
    feedback_id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL REFERENCES audits(audit_id) ON DELETE CASCADE,
    ticket_id TEXT NOT NULL,
    criterion_name TEXT NOT NULL,
    ai_decision TEXT NOT NULL,
    auditor_decision TEXT NOT NULL,
    reason TEXT NOT NULL,
    improvement_target TEXT NOT NULL DEFAULT 'Audit Rules',
    auditor TEXT NOT NULL,
    applied_status TEXT NOT NULL DEFAULT 'Captured',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_trail (
    trail_id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL,
    audit_id TEXT NOT NULL DEFAULT '',
    who TEXT NOT NULL,
    role TEXT NOT NULL,
    what TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    rule TEXT NOT NULL DEFAULT '',
    evidence TEXT NOT NULL DEFAULT '',
    ai_model TEXT NOT NULL DEFAULT '',
    confidence REAL NOT NULL DEFAULT 100.0,
    decision TEXT NOT NULL DEFAULT '',
    human_override INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS policy_documents (
    policy_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    version TEXT NOT NULL,
    effective_date TEXT NOT NULL,
    owner TEXT NOT NULL,
    applies_to TEXT NOT NULL DEFAULT 'ALL',
    summary TEXT NOT NULL,
    content TEXT NOT NULL,
    tags_json TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS monitoring_alerts (
    alert_id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    predicted_risk REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'Active',
    created_at TEXT NOT NULL,
    resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS governance_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    confidence_auto INTEGER NOT NULL DEFAULT 95,
    confidence_recommend INTEGER NOT NULL DEFAULT 80,
    critical_risk_threshold INTEGER NOT NULL DEFAULT 80,
    high_risk_threshold INTEGER NOT NULL DEFAULT 60,
    medium_risk_threshold INTEGER NOT NULL DEFAULT 35,
    medium_sampling_pct INTEGER NOT NULL DEFAULT 25,
    proactive_alerts_enabled INTEGER NOT NULL DEFAULT 1,
    auto_close_low_risk INTEGER NOT NULL DEFAULT 1,
    updated_by TEXT NOT NULL DEFAULT 'Governance Admin',
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tickets_type ON tickets(ticket_type);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_audits_risk ON audits(risk_band, risk_score);
CREATE INDEX IF NOT EXISTS idx_findings_ticket ON findings(ticket_id);
CREATE INDEX IF NOT EXISTS idx_trail_ticket ON audit_trail(ticket_id);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON monitoring_alerts(status);
"""


def init_db() -> None:
    with db_session() as conn:
        conn.executescript(SCHEMA_SQL)


def reset_db_tables() -> None:
    with db_session() as conn:
        conn.executescript(
            """
            DELETE FROM monitoring_alerts;
            DELETE FROM audit_trail;
            DELETE FROM feedback;
            DELETE FROM findings;
            DELETE FROM audit_results;
            DELETE FROM audits;
            DELETE FROM tickets;
            DELETE FROM audit_criteria;
            DELETE FROM policy_documents;
            DELETE FROM governance_config;
            """
        )


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


def parse_json_col(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return fallback
