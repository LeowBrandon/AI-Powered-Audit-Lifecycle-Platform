"""Agent 7 — Auditor Copilot (Proposal Section 4 Page 13 & Section 17 RAG).

Augments auditors with grounded, evidence-backed answers for both single-ticket
investigations and fleet-wide compliance queries, citing exact rules, evidence,
comparable historical tickets, and enterprise policy documents via RAG.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from app.agents.base import llm_client
from app.config import settings
from app.services.rag_knowledge import RAGKnowledgeBase


class AuditorCopilotAgent:
    """Grounded AI assistant for auditors, QC reviewers, and operations managers."""

    def answer(
        self,
        conn: sqlite3.Connection,
        question: str,
        ticket_id: str | None,
        rag: RAGKnowledgeBase,
        user_role: str = "Auditor",
    ) -> dict[str, Any]:
        q = question.strip()
        ql = q.lower()
        sources: list[dict[str, str]] = []
        referenced_tickets: list[str] = []

        # Allow asking about a specific ticket mentioned directly inside the question
        if not ticket_id:
            ticket_row = self._detect_ticket_in_question(conn, q)
            if ticket_row:
                ticket_id = ticket_row["ticket_id"]

        ticket_ctx = self._load_ticket_bundle(conn, ticket_id) if ticket_id else None
        policy_hits = rag.search(q, ticket_type=ticket_ctx["ticket"]["ticket_type"] if ticket_ctx else None, top_k=2)

        for hit in policy_hits:
            sources.append(
                {
                    "type": "policy",
                    "label": f"{hit.title} ({hit.version})",
                    "ref": hit.policy_id,
                    "detail": hit.excerpt[:160],
                }
            )

        # Intent 1: Fleet-wide query — tickets missing approval / high risk / failing
        if any(p in ql for p in ("all tickets", "show me", "which tickets", "list tickets", "missing approval")):
            answer_text, extra_tickets = self._answer_fleet_query(conn, ql)
            referenced_tickets.extend(extra_tickets)
            sources.insert(
                0,
                {
                    "type": "database",
                    "label": "Live Audit Findings Store",
                    "ref": "FINDINGS",
                    "detail": f"Queried active findings across all audited tickets ({len(extra_tickets)} matches).",
                },
            )
            return self._finalize(answer_text, sources, referenced_tickets, ticket_id, q, user_role)

        # Intent 2: Policy-specific question when no ticket selected or policy explicitly asked
        if ("policy" in ql or "sop" in ql or "itil" in ql or "standard" in ql) and (not ticket_ctx or "require" in ql):
            if policy_hits:
                lines = [
                    f"Based on the Audit Policy Knowledge Base, here are the governing requirements for your question:\n"
                ]
                for idx, h in enumerate(policy_hits, 1):
                    lines.append(f"{idx}. **{h.title} ({h.version})** — {h.excerpt}")
                return self._finalize("\n".join(lines), sources, referenced_tickets, ticket_id, q, user_role)

        # Ticket-scoped intents (require ticket context; fall back to CR001992 if none)
        if not ticket_ctx:
            ticket_ctx = self._load_ticket_bundle(conn, "CR001992")
            ticket_id = ticket_ctx["ticket"]["ticket_id"] if ticket_ctx else None

        if not ticket_ctx:
            return {
                "answer": "No tickets are currently loaded in AuditIQ. Ingest or seed tickets to begin analysis.",
                "sources": sources,
                "referencedTickets": [],
                "model": settings.active_ai_model_label,
            }

        t = ticket_ctx["ticket"]
        a = ticket_ctx["audit"]
        results = ticket_ctx["results"]
        findings = ticket_ctx["findings"]
        referenced_tickets.append(t["ticket_id"])

        sources.insert(
            0,
            {
                "type": "ticket",
                "label": f"Ticket {t['ticket_id']} ({t['ticket_type']})",
                "ref": t["ticket_id"],
                "detail": f"Compliance {a['audit_score']}% · Risk {a['risk_score']}/100 ({a['risk_band']})",
            },
        )

        if "why" in ql and ("fail" in ql or "risk" in ql or "review" in ql or "flag" in ql):
            if not findings:
                answer_text = (
                    f"**{t['ticket_id']}** ({t['short_description']}) currently has **no failing audit criteria** "
                    f"(Compliance: **{a['audit_score']}%**, Risk: **{a['risk_score']}/100 {a['risk_band']}**). "
                    f"All {len(results)} applicable {t['ticket_type']} rules passed with {a['ai_confidence']}% AI confidence."
                )
            else:
                high_count = sum(1 for f in findings if f["severity"] in {"HIGH", "CRITICAL"})
                bullets = "\n".join(
                    f"{i}. **{f['criterion_name']}** — `{f['ai_status']}` ({f['severity']} severity, {int(f['confidence'])}% confidence): {f['description']}"
                    for i, f in enumerate(findings, 1)
                )
                answer_text = (
                    f"**{t['ticket_id']}** failed or triggered review on **{len(findings)} criteria**:\n\n"
                    f"{bullets}\n\n"
                    f"**Overall Score:** {a['audit_score']}/100 · **Risk Score:** {a['risk_score']}/100 ({a['risk_band']}). "
                    f"{high_count} finding(s) are classified as High/Critical risk."
                )
                sources.append(
                    {
                        "type": "rules",
                        "label": f"{t['ticket_type']} Audit Ruleset",
                        "ref": t["ticket_type"],
                        "detail": f"{len(findings)} active findings evaluated across {len(results)} criteria.",
                    }
                )

        elif "evidence" in ql or "proof" in ql or "source" in ql or "where" in ql:
            non_pass = [r for r in results if r["status"] != "PASS"]
            target_rows = non_pass if non_pass else results[:4]
            lines = [
                f"- **{r['criterion_name']}** (`{r['status']}`, {int(r['confidence'])}% confidence) — "
                f"*Source: {r['evidence_source']}*\n  Detected: {r['detected_evidence']}"
                + (f"\n  Missing: {r['missing_evidence']}" if r["missing_evidence"] else "")
                for r in target_rows
            ]
            heading = (
                f"Evidence supporting open findings on **{t['ticket_id']}**:"
                if non_pass
                else f"Verified passing evidence on **{t['ticket_id']}**:"
            )
            answer_text = heading + "\n\n" + "\n".join(lines)
            sources.append(
                {
                    "type": "evidence",
                    "label": "AI Evidence Extraction Store",
                    "ref": t["ticket_id"],
                    "detail": f"Inspected {len(results)} criterion evidence mappings.",
                }
            )

        elif "similar" in ql or "compare" in ql or "benchmark" in ql:
            sim_rows = conn.execute(
                """
                SELECT t.ticket_id, t.short_description, t.assignment_group, a.audit_score, a.risk_score, a.risk_band
                FROM tickets t
                JOIN audits a ON a.ticket_id = t.ticket_id
                WHERE t.ticket_type = ? AND t.ticket_id != ?
                ORDER BY ABS(a.risk_score - ?) ASC
                LIMIT 4
                """,
                (t["ticket_type"], t["ticket_id"], a["risk_score"]),
            ).fetchall()
            comp_lines = []
            for r in sim_rows:
                referenced_tickets.append(r["ticket_id"])
                comp_lines.append(
                    f"- **{r['ticket_id']}** ({r['assignment_group']}): Compliance **{r['audit_score']}%**, "
                    f"Risk **{r['risk_score']} ({r['risk_band']})** — {r['short_description']}"
                )
            avg_type = conn.execute(
                "SELECT ROUND(AVG(audit_score), 1) AS avg_s, ROUND(AVG(risk_score), 1) AS avg_r FROM audits WHERE audit_type = ?",
                (t["ticket_type"],),
            ).fetchone()
            answer_text = (
                f"Comparison for **{t['ticket_id']}** (Compliance {a['audit_score']}%, Risk {a['risk_score']}) "
                f"against {t['ticket_type']} fleet baseline (Avg Compliance **{avg_type['avg_s']}%**, Avg Risk **{avg_type['avg_r']}**):\n\n"
                + ("\n".join(comp_lines) if comp_lines else "No comparable tickets found.")
            )
            sources.append(
                {
                    "type": "historical",
                    "label": f"Historical {t['ticket_type']} Benchmark",
                    "ref": t["ticket_type"],
                    "detail": f"Compared against {len(sim_rows)} closest risk-band peer tickets.",
                }
            )

        elif "rule" in ql or "score" in ql or "drop" in ql or "driver" in ql:
            impacted = [r for r in results if r["status"] != "PASS"]
            if impacted:
                lines = [
                    f"- **{r['criterion_name']}** ({r['method']} · Policy `{r['policy_ref']}`): "
                    f"marked `{r['status']}` at {int(r['confidence'])}% confidence — {r['reason']}"
                    for r in impacted
                ]
                answer_text = (
                    f"Score drivers reducing **{t['ticket_id']}** to **{a['audit_score']}/100** "
                    f"(Risk {a['risk_score']}/100 {a['risk_band']}):\n\n"
                    + "\n".join(lines)
                )
            else:
                answer_text = (
                    f"No rules penalized **{t['ticket_id']}** — all {len(results)} {t['ticket_type']} rules "
                    f"passed, yielding a **{a['audit_score']}/100** compliance score."
                )

        elif "summary" in ql or "management" in ql or "executive" in ql or "brief" in ql:
            recs = [f["recommendation"] for f in findings[:2]] or ["No remediation required; ready for auto-closure."]
            answer_text = (
                f"**Management Executive Brief — {t['ticket_id']} ({t['ticket_type']} · {t['priority']})**\n\n"
                f"- **Scope:** {t['short_description']} ({t['assignment_group']} / {t['business_unit']})\n"
                f"- **Governance Standing:** Compliance **{a['audit_score']}%** · Risk **{a['risk_score']}/100 ({a['risk_band']})** · Status `{a['status']}`\n"
                f"- **AI Assessment:** {a['ai_summary']}\n"
                f"- **Recommended Action:** {' '.join(recs)}"
            )

        else:
            answer_text = (
                f"**{t['ticket_id']}** ({t['type'] if 'type' in t else t['ticket_type']}, {t['priority']}, {t['assignment_group']}) "
                f"has Compliance **{a['audit_score']}%**, Risk **{a['risk_score']}/100 ({a['risk_band']})**, "
                f"and **{len(findings)} active finding(s)**. {a['ai_summary']}\n\n"
                f"You can ask me why this ticket failed, inspect supporting evidence, compare similar tickets, "
                f"list all tickets missing approvals, check governing policies, or generate a management summary."
            )

        return self._finalize(answer_text, sources, referenced_tickets, ticket_id, q, user_role)

    def _finalize(
        self,
        deterministic_answer: str,
        sources: list[dict[str, str]],
        referenced_tickets: list[str],
        ticket_id: str | None,
        question: str,
        user_role: str,
    ) -> dict[str, Any]:
        final_answer = deterministic_answer
        if settings.llm_enabled:
            refined = llm_client.chat_completion(
                system_prompt=(
                    f"You are AuditIQ Auditor Copilot assisting a {user_role}. "
                    "Refine the grounded draft answer clearly and concisely without inventing any facts, "
                    "ticket IDs, or metrics not present in the draft."
                ),
                user_prompt=f"Question: {question}\n\nGrounded Audit Data:\n{deterministic_answer}",
                max_tokens=360,
            )
            if refined:
                final_answer = refined

        return {
            "answer": final_answer,
            "sources": sources,
            "referencedTickets": list(dict.fromkeys(referenced_tickets)),
            "ticketId": ticket_id,
            "model": settings.active_ai_model_label,
        }

    @staticmethod
    def _detect_ticket_in_question(conn: sqlite3.Connection, question: str) -> dict[str, Any] | None:
        upper = question.upper()
        rows = conn.execute("SELECT ticket_id FROM tickets").fetchall()
        for row in rows:
            if row["ticket_id"].upper() in upper:
                return dict(row)
        return None

    @staticmethod
    def _load_ticket_bundle(conn: sqlite3.Connection, ticket_id: str) -> dict[str, Any] | None:
        t = conn.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)).fetchone()
        if not t:
            return None
        a = conn.execute("SELECT * FROM audits WHERE ticket_id = ?", (ticket_id,)).fetchone()
        if not a:
            return None
        results = conn.execute(
            "SELECT * FROM audit_results WHERE audit_id = ? ORDER BY criterion_id ASC",
            (a["audit_id"],),
        ).fetchall()
        findings = conn.execute(
            "SELECT * FROM findings WHERE audit_id = ? AND status != 'Resolved'",
            (a["audit_id"],),
        ).fetchall()
        return {
            "ticket": dict(t),
            "audit": dict(a),
            "results": [dict(r) for r in results],
            "findings": [dict(f) for f in findings],
        }

    @staticmethod
    def _answer_fleet_query(conn: sqlite3.Connection, ql: str) -> tuple[str, list[str]]:
        if "approval" in ql or "authorization" in ql:
            rows = conn.execute(
                """
                SELECT DISTINCT t.ticket_id, t.ticket_type, t.short_description, t.assignment_group,
                       a.risk_score, a.risk_band, f.criterion_name, f.description
                FROM findings f
                JOIN tickets t ON t.ticket_id = f.ticket_id
                JOIN audits a ON a.audit_id = f.audit_id
                WHERE (LOWER(f.criterion_name) LIKE '%approval%' OR LOWER(f.criterion_name) LIKE '%authorization%')
                  AND f.status NOT IN ('Resolved', 'Overridden')
                ORDER BY a.risk_score DESC
                LIMIT 10
                """
            ).fetchall()
            label = "missing required approval / authorization"
        elif "rollback" in ql:
            rows = conn.execute(
                """
                SELECT DISTINCT t.ticket_id, t.ticket_type, t.short_description, t.assignment_group,
                       a.risk_score, a.risk_band, f.criterion_name, f.description
                FROM findings f
                JOIN tickets t ON t.ticket_id = f.ticket_id
                JOIN audits a ON a.audit_id = f.audit_id
                WHERE LOWER(f.criterion_name) LIKE '%rollback%'
                  AND f.status NOT IN ('Resolved', 'Overridden')
                ORDER BY a.risk_score DESC
                LIMIT 10
                """
            ).fetchall()
            label = "with missing or incomplete rollback plans"
        elif "sla" in ql:
            rows = conn.execute(
                """
                SELECT DISTINCT t.ticket_id, t.ticket_type, t.short_description, t.assignment_group,
                       a.risk_score, a.risk_band, 'SLA' AS criterion_name, t.sla_status AS description
                FROM tickets t
                JOIN audits a ON a.ticket_id = t.ticket_id
                WHERE t.sla_status IN ('At Risk', 'Breached')
                ORDER BY a.risk_score DESC
                LIMIT 10
                """
            ).fetchall()
            label = "with SLA risk or SLA breaches"
        else:
            rows = conn.execute(
                """
                SELECT t.ticket_id, t.ticket_type, t.short_description, t.assignment_group,
                       a.risk_score, a.risk_band, a.decision AS criterion_name, a.ai_summary AS description
                FROM tickets t
                JOIN audits a ON a.ticket_id = t.ticket_id
                WHERE a.risk_band IN ('CRITICAL', 'HIGH')
                ORDER BY a.risk_score DESC
                LIMIT 10
                """
            ).fetchall()
            label = "in CRITICAL or HIGH risk bands"

        if not rows:
            return f"Great news — zero tickets are currently flagged as {label}.", []

        ticket_ids = [r["ticket_id"] for r in rows]
        lines = [
            f"- **{r['ticket_id']}** (`{r['ticket_type']}` · Risk **{r['risk_score']} {r['risk_band']}** · {r['assignment_group']}) — "
            f"{r['short_description']} *({r['criterion_name']})*"
            for r in rows
        ]
        return (
            f"Found **{len(rows)} ticket(s)** {label}:\n\n" + "\n".join(lines),
            ticket_ids,
        )
