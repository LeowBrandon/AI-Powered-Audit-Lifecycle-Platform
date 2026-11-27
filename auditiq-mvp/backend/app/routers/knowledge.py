"""Audit Policy Knowledge Base & RAG Retrieval API (Proposal Section 17)."""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, HTTPException, Query

from app.database import db_session, parse_json_col
from app.schemas import PolicyCreateRequest
from app.services.audit_service import refresh_rag_index, utc_now
from app.services.rag_knowledge import rag_kb

router = APIRouter(prefix="/api/knowledge", tags=["Audit Policy Knowledge Base"])


@router.get("")
def list_policies(category: str | None = Query(default=None), applies_to: str | None = Query(default=None)):
    with db_session() as conn:
        clauses = ["1 = 1"]
        params = []
        if category and category != "ALL":
            clauses.append("category = ?")
            params.append(category)
        if applies_to and applies_to != "ALL":
            clauses.append("(applies_to = ? OR applies_to = 'ALL')")
            params.append(applies_to)

        rows = conn.execute(
            f"SELECT * FROM policy_documents WHERE {' AND '.join(clauses)} ORDER BY policy_id ASC",
            params,
        ).fetchall()
        items = []
        for r in rows:
            d = dict(r)
            items.append(
                {
                    "policyId": d["policy_id"],
                    "title": d["title"],
                    "category": d["category"],
                    "version": d["version"],
                    "effectiveDate": d["effective_date"],
                    "owner": d["owner"],
                    "appliesTo": d["applies_to"],
                    "summary": d["summary"],
                    "content": d["content"],
                    "tags": parse_json_col(d["tags_json"], []),
                }
            )
        categories = [
            r["category"]
            for r in conn.execute("SELECT DISTINCT category FROM policy_documents ORDER BY category").fetchall()
        ]
        return {"items": items, "categories": categories, "total": len(items)}


@router.get("/search")
def search_knowledge_rag(
    q: str = Query(..., min_length=2),
    ticket_type: str | None = Query(default=None),
    top_k: int = Query(default=4, ge=1, le=10),
):
    hits = rag_kb.search(q, ticket_type=None if ticket_type in {None, "", "ALL"} else ticket_type, top_k=top_k)
    return {
        "query": q,
        "hits": [
            {
                "policyId": h.policy_id,
                "title": h.title,
                "category": h.category,
                "version": h.version,
                "appliesTo": h.applies_to,
                "score": h.score,
                "excerpt": h.excerpt,
                "matchedTerms": h.matched_terms,
            }
            for h in hits
        ],
    }


@router.post("", status_code=201)
def create_policy(payload: PolicyCreateRequest):
    with db_session() as conn:
        pid = payload.policy_id.strip().upper() if payload.policy_id else f"POL-{uuid.uuid4().hex[:5].upper()}"
        exists = conn.execute("SELECT 1 FROM policy_documents WHERE policy_id = ?", (pid,)).fetchone()
        if exists:
            raise HTTPException(status_code=409, detail=f"Policy {pid} already exists.")
        today = utc_now()[:10]
        conn.execute(
            """
            INSERT INTO policy_documents (
                policy_id, title, category, version, effective_date,
                owner, applies_to, summary, content, tags_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pid,
                payload.title,
                payload.category,
                payload.version,
                today,
                payload.owner,
                payload.applies_to,
                payload.summary,
                payload.content,
                json.dumps(payload.tags),
            ),
        )
        indexed = refresh_rag_index(conn)
        return {
            "message": f"Policy {pid} saved and indexed into RAG Knowledge Base ({indexed} total documents).",
            "policyId": pid,
        }
