"""Local TF-IDF vector retrieval engine for the Audit Policy Knowledge Base (RAG layer).

Implements zero-external-dependency cosine similarity search over enterprise
audit policies, SOPs, ITIL procedures, quality standards, and historical findings.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable

TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-_.][a-z0-9]+)*")
STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "were",
    "have", "has", "had", "not", "but", "can", "will", "should", "must", "all",
    "any", "into", "before", "after", "when", "where", "which", "who", "what",
    "why", "how", "per", "via", "its", "their", "them", "they", "been", "being",
    "also", "such", "than", "then", "only", "over", "under", "within", "each",
}


@dataclass
class IndexedPolicy:
    policy_id: str
    title: str
    category: str
    version: str
    applies_to: str
    summary: str
    content: str
    tags: list[str]
    vector: dict[str, float]


@dataclass
class RetrievalHit:
    policy_id: str
    title: str
    category: str
    version: str
    applies_to: str
    score: float
    excerpt: str
    matched_terms: list[str]


def _tokenize(text: str) -> list[str]:
    return [
        tok
        for tok in TOKEN_RE.findall(text.lower())
        if len(tok) > 1 and tok not in STOPWORDS
    ]


class RAGKnowledgeBase:
    """In-memory TF-IDF cosine-similarity index backed by the PolicyDocument table."""

    def __init__(self) -> None:
        self._docs: list[IndexedPolicy] = []
        self._idf: dict[str, float] = {}

    def rebuild(self, policy_rows: Iterable[dict]) -> None:
        raw_docs = list(policy_rows)
        if not raw_docs:
            self._docs = []
            self._idf = {}
            return

        doc_tokens: list[list[str]] = []
        df: Counter[str] = Counter()
        for doc in raw_docs:
            combined = " ".join(
                [
                    doc.get("title", ""),
                    doc.get("title", ""),  # boost title
                    doc.get("category", ""),
                    doc.get("applies_to", ""),
                    doc.get("summary", ""),
                    doc.get("content", ""),
                    " ".join(doc.get("tags", [])),
                ]
            )
            tokens = _tokenize(combined)
            doc_tokens.append(tokens)
            for unique_tok in set(tokens):
                df[unique_tok] += 1

        total_docs = len(raw_docs)
        self._idf = {
            tok: math.log((1 + total_docs) / (1 + freq)) + 1.0
            for tok, freq in df.items()
        }

        indexed: list[IndexedPolicy] = []
        for doc, tokens in zip(raw_docs, doc_tokens):
            tf = Counter(tokens)
            total_len = max(len(tokens), 1)
            vec = {
                tok: (count / total_len) * self._idf.get(tok, 1.0)
                for tok, count in tf.items()
            }
            norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
            norm_vec = {k: v / norm for k, v in vec.items()}
            indexed.append(
                IndexedPolicy(
                    policy_id=doc["policy_id"],
                    title=doc["title"],
                    category=doc["category"],
                    version=doc["version"],
                    applies_to=doc["applies_to"],
                    summary=doc["summary"],
                    content=doc["content"],
                    tags=list(doc.get("tags", [])),
                    vector=norm_vec,
                )
            )
        self._docs = indexed

    def search(
        self,
        query: str,
        ticket_type: str | None = None,
        top_k: int = 3,
    ) -> list[RetrievalHit]:
        if not self._docs or not query.strip():
            return []

        q_tokens = _tokenize(query)
        if not q_tokens:
            return []

        q_tf = Counter(q_tokens)
        q_len = len(q_tokens)
        q_vec = {
            tok: (count / q_len) * self._idf.get(tok, 1.0)
            for tok, count in q_tf.items()
        }
        q_norm = math.sqrt(sum(v * v for v in q_vec.values())) or 1.0
        q_norm_vec = {k: v / q_norm for k, v in q_vec.items()}

        scored: list[RetrievalHit] = []
        for doc in self._docs:
            dot = sum(q_norm_vec.get(tok, 0.0) * weight for tok, weight in doc.vector.items())
            if ticket_type and doc.applies_to in {ticket_type, "ALL"}:
                dot += 0.08 if dot > 0 else 0.0
            if dot <= 0:
                continue

            matched = sorted(set(q_tokens).intersection(doc.vector.keys()))
            excerpt = self._extract_best_excerpt(doc.content, matched) or doc.summary
            scored.append(
                RetrievalHit(
                    policy_id=doc.policy_id,
                    title=doc.title,
                    category=doc.category,
                    version=doc.version,
                    applies_to=doc.applies_to,
                    score=round(min(dot, 0.99), 3),
                    excerpt=excerpt,
                    matched_terms=matched[:8],
                )
            )

        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:top_k]

    @staticmethod
    def _extract_best_excerpt(content: str, matched_terms: list[str]) -> str:
        paragraphs = [p.strip() for p in content.split("\n") if p.strip()]
        if not paragraphs:
            return ""
        if not matched_terms:
            return paragraphs[0][:280]
        best_para = paragraphs[0]
        best_hits = -1
        for para in paragraphs:
            low = para.lower()
            hits = sum(1 for term in matched_terms if term in low)
            if hits > best_hits:
                best_hits = hits
                best_para = para
        return best_para[:320]


rag_kb = RAGKnowledgeBase()
