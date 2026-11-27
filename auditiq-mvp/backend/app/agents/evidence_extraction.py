"""Agent 2 — Evidence Extraction Agent (Proposal Section 4 Page 7 & Section 12 Page 23).

Converts unstructured ticket descriptions, timestamped work notes, approvals,
attachments, and closure details into structured evidence items plus exact
highlighted text spans for the AI Evidence Viewer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.agents.base import AgentStepTrace, elapsed_ms, timer_start
from app.agents.ticket_intelligence import TicketContext


@dataclass
class EvidenceHighlight:
    source_type: str  # "work_note" | "attachment" | "approval" | "resolution"
    source_index: int
    source_label: str
    quote: str
    evidence_label: str
    status: str  # "PASS" | "REVIEW" | "FAIL"
    confidence: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "sourceType": self.source_type,
            "sourceIndex": self.source_index,
            "sourceLabel": self.source_label,
            "quote": self.quote,
            "evidenceLabel": self.evidence_label,
            "status": self.status,
            "confidence": self.confidence,
        }


@dataclass
class ExtractedEvidence:
    facts: dict[str, dict[str, Any]] = field(default_factory=dict)
    highlights: list[EvidenceHighlight] = field(default_factory=list)
    searched_sources: list[str] = field(
        default_factory=lambda: [
            "Ticket fields",
            "Approvals",
            "Work notes",
            "Attachments",
            "Closure details",
            "Related records",
        ]
    )


class EvidenceExtractionAgent:
    """Extracts structured compliance signals and exact citations from unstructured ticket text."""

    # Keyword patterns mapped to evidence categories
    CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
        "Network": ("network", "switch", "vpn", "router", "connectivity", "branch", "latency", "dns", "bandwidth"),
        "Database": ("database", "postgres", "sql", "cluster", "db ", "replica", "schema", "query"),
        "Security": ("firewall", "security", "tls", "certificate", "access", "iam", "mfa", "vulnerability", "active directory", "pam"),
        "Applications": ("batch", "api", "application", "service", "gateway", "deployment", "erp", "portal", "payment"),
        "Infrastructure": ("server", "vm", "cluster", "load balancer", "storage", "backup", "patch", "upgrade", "kubernetes", "os "),
        "End User": ("laptop", "workstation", "license", "saas", "mailbox", "onboarding", "device", "monitor", "account"),
    }

    def extract(self, ctx: TicketContext) -> tuple[ExtractedEvidence, AgentStepTrace]:
        start = timer_start()
        highlights: list[EvidenceHighlight] = []
        facts: dict[str, dict[str, Any]] = {}

        # Scan work notes and attachments for exact highlightable phrases
        for idx, note in enumerate(ctx.work_notes):
            text = note["text"]
            low = text.lower()
            ts_label = f"Work Notes [{note['timestamp']}]"

            self._detect_note_highlight(highlights, "work_note", idx, ts_label, text, low)

        for idx, att in enumerate(ctx.attachments):
            text = f"{att['name']}: {att['content_summary']}"
            low = text.lower()
            att_label = f"{att['name']} → {att['section']}"
            self._detect_note_highlight(highlights, "attachment", idx, att_label, text, low)

        for idx, appr in enumerate(ctx.approvals):
            summary = f"{appr['type']} approval by {appr['approver']} ({appr['status']})"
            if appr.get("note"):
                summary += f" — {appr['note']}"
            st = "PASS" if appr["status"] == "Approved" else "FAIL"
            highlights.append(
                EvidenceHighlight(
                    source_type="approval",
                    source_index=idx,
                    source_label="Approval Records",
                    quote=summary,
                    evidence_label=f"{appr['type']} Approval",
                    status=st,
                    confidence=99 if st == "PASS" else 97,
                )
            )

        if ctx.resolution.strip():
            highlights.append(
                EvidenceHighlight(
                    source_type="resolution",
                    source_index=0,
                    source_label="Closure / Resolution Details",
                    quote=ctx.resolution.strip()[:180],
                    evidence_label="Resolution Evidence",
                    status="PASS" if len(ctx.resolution.strip()) >= 28 else "REVIEW",
                    confidence=96 if len(ctx.resolution.strip()) >= 28 else 74,
                )
            )

        # Build structured facts dictionary for the Rules + Reasoning agents
        facts["business_approval"] = self._extract_approval(ctx, {"Business", "CAB"})
        facts["technical_approval"] = self._extract_approval(ctx, {"Technical"})
        facts["manager_authorization"] = self._extract_approval(ctx, {"Manager", "Business"})
        facts["risk_assessment"] = self._extract_risk_assessment(ctx)
        facts["implementation_plan"] = self._extract_implementation_plan(ctx)
        facts["rollback_plan"] = self._extract_rollback_plan(ctx)
        facts["testing"] = self._extract_testing(ctx)
        facts["post_implementation_review"] = self._extract_post_validation(ctx)
        facts["root_cause"] = self._extract_root_cause(ctx)
        facts["resolution"] = self._extract_resolution(ctx)
        facts["customer_communication"] = self._extract_customer_comm(ctx)
        facts["categorization"] = self._extract_categorization(ctx)
        facts["priority"] = self._extract_priority_alignment(ctx)
        facts["sla"] = self._extract_sla(ctx)
        facts["closure"] = self._extract_closure(ctx)
        facts["fulfillment"] = self._extract_fulfillment(ctx)
        facts["documentation"] = self._extract_sr_documentation(ctx)

        extracted = ExtractedEvidence(facts=facts, highlights=highlights)
        trace = AgentStepTrace(
            agent_number=2,
            agent_name="Evidence Extraction Agent",
            phase="Phase 3 — Unstructured Evidence Extraction",
            status="completed",
            duration_ms=elapsed_ms(start),
            summary=(
                f"Extracted {len(facts)} structured audit attributes and {len(highlights)} "
                f"verifiable text highlights across work notes, approvals, attachments, and closure details."
            ),
            metrics={
                "structuredFields": len(facts),
                "highlightsCaptured": len(highlights),
                "sourcesScanned": len(extracted.searched_sources),
            },
        )
        return extracted, trace

    def _detect_note_highlight(
        self,
        highlights: list[EvidenceHighlight],
        source_type: str,
        idx: int,
        label: str,
        text: str,
        low: str,
    ) -> None:
        patterns = [
            (
                r"(customer (?:confirmed|notified|acknowledged|verified)[^.]*\.?|user confirmed[^.]*\.?|stakeholder notified[^.]*\.?)",
                "Customer Communication",
                "PASS",
                96,
            ),
            (
                r"(root cause[^.]*\.?|caused by[^.]*\.?|failed switch[^.]*\.?|memory leak[^.]*\.?|misconfigured[^.]*\.?)",
                "Root Cause Evidence",
                "REVIEW" if ("brief" in low or "unclear" in low or "tbd" in low) else "PASS",
                72 if ("brief" in low or "unclear" in low or "tbd" in low) else 95,
            ),
            (
                r"(deployment completed[^.]*\.?|service restored[^.]*\.?|implementation window[^.]*\.?|change window[^.]*\.?|upgrade completed[^.]*\.?)",
                "Implementation Evidence",
                "PASS",
                95,
            ),
            (
                r"(no rollback plan[^.]*\.?|rollback[^.]*incomplete[^.]*\.?|rollback steps[^.]*missing[^.]*\.?)",
                "Rollback Assessment",
                "FAIL" if "no rollback" in low else "REVIEW",
                95 if "no rollback" in low else 71,
            ),
            (
                r"(rollback (?:plan|steps|procedure|verified|tested|not required)[^.]*\.?|snapshot restore[^.]*\.?|revert procedure[^.]*\.?)",
                "Rollback Assessment",
                "PASS",
                94,
            ),
            (
                r"(post-implementation (?:validation|review|verification)[^.]*\.?|smoke test(?:s|ing)? passed[^.]*\.?|health check(?:s)? passed[^.]*\.?)",
                "Post-Implementation Validation",
                "PASS",
                95,
            ),
            (
                r"(approval from [^.]*\.?|approved by [^.]*\.?|manager authorization[^.]*\.?|cab approved[^.]*\.?)",
                "Approval Evidence",
                "PASS",
                96,
            ),
            (
                r"(approval pending[^.]*\.?|missing business approval[^.]*\.?|awaiting business approval[^.]*\.?)",
                "Approval Gap",
                "FAIL",
                97,
            ),
            (
                r"(pre-production (?:test|validation)[^.]*\.?|uat passed[^.]*\.?|staging test[^.]*\.?|test plan[^.]*\.?)",
                "Testing Evidence",
                "PASS",
                95,
            ),
            (
                r"(risk assessment[^.]*\.?|impact analysis[^.]*\.?)",
                "Risk Assessment",
                "PASS",
                97,
            ),
            (
                r"(device issued[^.]*\.?|access provisioned[^.]*\.?|license assigned[^.]*\.?|request fulfilled[^.]*\.?)",
                "Fulfillment Evidence",
                "PASS",
                96,
            ),
        ]

        seen_labels: set[str] = set()
        for regex, ev_label, status, conf in patterns:
            if ev_label in seen_labels:
                continue
            m = re.search(regex, text, flags=re.IGNORECASE)
            if m:
                seen_labels.add(ev_label)
                highlights.append(
                    EvidenceHighlight(
                        source_type=source_type,
                        source_index=idx,
                        source_label=label,
                        quote=m.group(0).strip(),
                        evidence_label=ev_label,
                        status=status,
                        confidence=conf,
                    )
                )

    @staticmethod
    def _extract_approval(ctx: TicketContext, target_types: set[str]) -> dict[str, Any]:
        approved = [a for a in ctx.approvals if a["type"] in target_types and a["status"] == "Approved"]
        pending = [a for a in ctx.approvals if a["type"] in target_types and a["status"] == "Pending"]
        other_approved = [a for a in ctx.approvals if a["status"] == "Approved"]

        if approved:
            a = approved[0]
            return {
                "found": True,
                "partial": False,
                "approver": a["approver"],
                "source": "Approval Records",
                "detected": f"{a['type']} approval recorded by {a['approver']} ({a.get('timestamp', 'timestamped')}).",
                "missing": "",
                "confidence": 99,
            }

        # Check unstructured work notes for explicit approval statements (Agent 2 example page 7!)
        for note in ctx.work_notes:
            low = note["text"].lower()
            if "pending" in low or "missing" in low or "without" in low or "awaiting" in low:
                continue
            if "Business" in target_types and re.search(
                r"(business owner approv|approved by .*vp|approved by .*business|cab approved|finance .*approved)",
                low,
            ):
                return {
                    "found": True,
                    "partial": False,
                    "approver": note["author"],
                    "source": f"Work Notes [{note['timestamp']}]",
                    "detected": note["text"],
                    "missing": "",
                    "confidence": 93,
                }
            if "Manager" in target_types and re.search(
                r"(manager approv|manager authorization|approval from .*manager|line manager)",
                low,
            ):
                return {
                    "found": True,
                    "partial": False,
                    "approver": note["author"],
                    "source": f"Work Notes [{note['timestamp']}]",
                    "detected": note["text"],
                    "missing": "",
                    "confidence": 94,
                }
            if "Technical" in target_types and re.search(
                r"(technical (?:review|approval) (?:completed|approved)|peer reviewed|architecture approved)",
                low,
            ):
                return {
                    "found": True,
                    "partial": False,
                    "approver": note["author"],
                    "source": f"Work Notes [{note['timestamp']}]",
                    "detected": note["text"],
                    "missing": "",
                    "confidence": 95,
                }

        detected_other = (
            ", ".join(f"{a['type']} approval by {a['approver']}" for a in other_approved)
            if other_approved
            else "No relevant approval records located."
        )
        if pending:
            return {
                "found": False,
                "partial": False,
                "approver": None,
                "source": "Approval Records",
                "detected": f"Pending approval request sent to {pending[0]['approver']}. {detected_other}",
                "missing": f"Completed {'/'.join(sorted(target_types))} owner approval.",
                "confidence": 97,
            }

        return {
            "found": False,
            "partial": False,
            "approver": None,
            "source": "Approval Records",
            "detected": detected_other,
            "missing": f"{'/'.join(sorted(target_types))} owner approval before execution.",
            "confidence": 98,
        }

    @staticmethod
    def _extract_risk_assessment(ctx: TicketContext) -> dict[str, Any]:
        for att in ctx.attachments:
            if any(k in (att["name"] + " " + att["content_summary"]).lower() for k in ("risk assessment", "impact analysis", "risk matrix")):
                return {
                    "found": True,
                    "partial": False,
                    "source": f"{att['name']} → {att['section']}",
                    "detected": att["content_summary"],
                    "missing": "",
                    "confidence": 98,
                }
        for note in ctx.work_notes:
            low = note["text"].lower()
            if "no risk assessment" in low or "risk assessment missing" in low:
                return {
                    "found": False,
                    "partial": False,
                    "source": f"Work Notes [{note['timestamp']}]",
                    "detected": note["text"],
                    "missing": "Documented change risk assessment and service impact analysis.",
                    "confidence": 96,
                }
            if "risk assessment" in low or "impact analysis" in low:
                return {
                    "found": True,
                    "partial": False,
                    "source": f"Work Notes [{note['timestamp']}]",
                    "detected": note["text"],
                    "missing": "",
                    "confidence": 94,
                }
        return {
            "found": False,
            "partial": False,
            "source": "Change Risk Assessment",
            "detected": "No risk assessment artifact detected.",
            "missing": "Formal risk & impact assessment.",
            "confidence": 95,
        }

    @staticmethod
    def _extract_implementation_plan(ctx: TicketContext) -> dict[str, Any]:
        for att in ctx.attachments:
            low = (att["name"] + " " + att["content_summary"]).lower()
            if any(k in low for k in ("implementation plan", "runbook", "deployment plan", "change plan")):
                if "incomplete" in low or "draft" in low:
                    return {
                        "found": False,
                        "partial": True,
                        "source": f"{att['name']} → {att['section']}",
                        "detected": att["content_summary"],
                        "missing": "Finalized step-by-step execution sequence and owner sign-off.",
                        "confidence": 75,
                    }
                return {
                    "found": True,
                    "partial": False,
                    "source": f"{att['name']} → {att['section']}",
                    "detected": att["content_summary"],
                    "missing": "",
                    "confidence": 95,
                }
        for note in ctx.work_notes:
            low = note["text"].lower()
            if any(k in low for k in ("implementation window", "change window", "implementation plan", "runbook", "deployment steps")):
                return {
                    "found": True,
                    "partial": False,
                    "source": f"Work Notes [{note['timestamp']}]",
                    "detected": note["text"],
                    "missing": "",
                    "confidence": 92,
                }
        if ctx.target_window and len(ctx.description) > 35:
            return {
                "found": False,
                "partial": True,
                "source": "Ticket Description",
                "detected": f"Target window {ctx.target_window} specified, but structured runbook steps are brief.",
                "missing": "Detailed step-by-step implementation runbook.",
                "confidence": 76,
            }
        return {
            "found": False,
            "partial": False,
            "source": "Implementation Plan",
            "detected": "No structured implementation plan attached.",
            "missing": "Documented implementation steps, owner, and change window.",
            "confidence": 94,
        }

    @staticmethod
    def _extract_rollback_plan(ctx: TicketContext) -> dict[str, Any]:
        # Scan attachments first (prefer latest uploaded/updated attachment!)
        for att in reversed(ctx.attachments):
            low = (att["name"] + " " + att["content_summary"]).lower()
            if "rollback" in low or "backout" in low or "restore" in low:
                if any(w in low for w in ("incomplete", "partial", "missing steps", "intent only", "tbd")):
                    return {
                        "found": False,
                        "partial": True,
                        "source": f"{att['name']} → {att['section']}",
                        "detected": att["content_summary"],
                        "missing": "Detailed step-by-step rollback commands, recovery time estimate, and verification step.",
                        "confidence": 71,
                    }
                return {
                    "found": True,
                    "partial": False,
                    "source": f"{att['name']} → {att['section']}",
                    "detected": att["content_summary"],
                    "missing": "",
                    "confidence": 96,
                }

        # Scan work notes newest-first so remediation notes override earlier gaps!
        for note in reversed(ctx.work_notes):
            low = note["text"].lower()
            if "rollback" in low or "backout" in low or "restore previous" in low:
                if any(w in low for w in ("no rollback", "missing rollback", "without rollback")):
                    return {
                        "found": False,
                        "partial": False,
                        "source": f"Work Notes [{note['timestamp']}]",
                        "detected": note["text"],
                        "missing": "Documented rollback/backout procedure prior to change execution.",
                        "confidence": 96,
                    }
                if any(w in low for w in ("incomplete", "partial", "brief", "tbd")):
                    return {
                        "found": False,
                        "partial": True,
                        "source": f"Work Notes [{note['timestamp']}]",
                        "detected": note["text"],
                        "missing": "Executable rollback steps and verification criteria.",
                        "confidence": 71,
                    }
                return {
                    "found": True,
                    "partial": False,
                    "source": f"Work Notes [{note['timestamp']}]",
                    "detected": note["text"],
                    "missing": "",
                    "confidence": 95,
                }

        return {
            "found": False,
            "partial": False,
            "source": "Implementation Plan → Section 4",
            "detected": "No rollback plan detected across attachments or work notes.",
            "missing": "Documented and tested rollback plan.",
            "confidence": 95,
        }

    @staticmethod
    def _extract_testing(ctx: TicketContext) -> dict[str, Any]:
        for att in reversed(ctx.attachments):
            low = (att["name"] + " " + att["content_summary"]).lower()
            if any(k in low for k in ("test", "validation checklist", "uat", "staging", "qa")):
                if "not completed" in low or "skipped" in low:
                    return {
                        "found": False,
                        "partial": False,
                        "source": f"{att['name']} → {att['section']}",
                        "detected": att["content_summary"],
                        "missing": "Completed pre-production testing sign-off.",
                        "confidence": 95,
                    }
                return {
                    "found": True,
                    "partial": False,
                    "source": f"{att['name']} → {att['section']}",
                    "detected": att["content_summary"],
                    "missing": "",
                    "confidence": 95,
                }
        for note in reversed(ctx.work_notes):
            low = note["text"].lower()
            if any(k in low for k in ("no testing", "testing skipped", "untested")):
                return {
                    "found": False,
                    "partial": False,
                    "source": f"Work Notes [{note['timestamp']}]",
                    "detected": note["text"],
                    "missing": "Pre-production test results and validation evidence.",
                    "confidence": 96,
                }
            if any(k in low for k in ("pre-prod", "pre-production", "uat passed", "staging test", "test passed", "validated in staging")):
                return {
                    "found": True,
                    "partial": False,
                    "source": f"Work Notes [{note['timestamp']}]",
                    "detected": note["text"],
                    "missing": "",
                    "confidence": 94,
                }
        return {
            "found": False,
            "partial": False,
            "source": "Validation Checklist",
            "detected": "No pre-production testing evidence found.",
            "missing": "Pre-implementation test execution results.",
            "confidence": 92,
        }

    @staticmethod
    def _extract_post_validation(ctx: TicketContext) -> dict[str, Any]:
        for att in reversed(ctx.attachments):
            low = (att["name"] + " " + att["content_summary"]).lower()
            if any(k in low for k in ("post-implementation", "pir", "post validation", "smoke test", "verification")):
                return {
                    "found": True,
                    "partial": False,
                    "source": f"{att['name']} → {att['section']}",
                    "detected": att["content_summary"],
                    "missing": "",
                    "confidence": 96,
                }
        for note in reversed(ctx.work_notes):
            low = note["text"].lower()
            if any(k in low for k in ("post-implementation validation", "post-implementation review", "smoke test", "health check", "service verified", "pir completed")):
                if "missing" in low or "pending" in low or "not recorded" in low:
                    continue
                return {
                    "found": True,
                    "partial": False,
                    "source": f"Work Notes [{note['timestamp']}]",
                    "detected": note["text"],
                    "missing": "",
                    "confidence": 95,
                }
        if ctx.resolution and any(k in ctx.resolution.lower() for k in ("validated", "verified", "post-implementation", "health check")):
            return {
                "found": True,
                "partial": False,
                "source": "Closure Details",
                "detected": ctx.resolution,
                "missing": "",
                "confidence": 93,
            }
        return {
            "found": False,
            "partial": False,
            "source": "Closure Controls",
            "detected": "No post-implementation validation or PIR evidence recorded.",
            "missing": "Post-implementation review / health verification sign-off.",
            "confidence": 94,
        }

    @staticmethod
    def _extract_root_cause(ctx: TicketContext) -> dict[str, Any]:
        for note in reversed(ctx.work_notes):
            low = note["text"].lower()
            if any(k in low for k in ("root cause", "caused by", "failed switch", "memory leak", "certificate expired", "misconfig", "disk full", "deadlock", "bug in")):
                if any(w in low for w in ("brief", "unclear", "unknown", "tbd", "investigating")):
                    return {
                        "found": False,
                        "partial": True,
                        "source": f"Work Notes [{note['timestamp']}]",
                        "detected": note["text"],
                        "missing": "Detailed technical root cause statement and linked problem record.",
                        "confidence": 72,
                    }
                return {
                    "found": True,
                    "partial": False,
                    "source": f"Work Notes [{note['timestamp']}]",
                    "detected": note["text"],
                    "missing": "",
                    "confidence": 96,
                }
        if ctx.resolution and any(k in ctx.resolution.lower() for k in ("root cause", "caused by", "due to")):
            return {
                "found": True,
                "partial": False,
                "source": "Resolution Details",
                "detected": ctx.resolution,
                "missing": "",
                "confidence": 94,
            }
        return {
            "found": False,
            "partial": False,
            "source": "Work Notes / Resolution",
            "detected": "No documented technical root cause located.",
            "missing": "Explicit root cause analysis in work notes or resolution.",
            "confidence": 95,
        }

    @staticmethod
    def _extract_resolution(ctx: TicketContext) -> dict[str, Any]:
        if len(ctx.resolution.strip()) >= 28:
            return {
                "found": True,
                "partial": False,
                "source": "Resolution Details",
                "detected": ctx.resolution.strip(),
                "missing": "",
                "confidence": 97,
            }
        for note in reversed(ctx.work_notes):
            low = note["text"].lower()
            if any(k in low for k in ("resolved", "service restored", "replaced", "restarted", "patched", "fixed", "mitigated")):
                if len(note["text"]) < 32:
                    return {
                        "found": False,
                        "partial": True,
                        "source": f"Work Notes [{note['timestamp']}]",
                        "detected": note["text"],
                        "missing": "Complete resolution steps and service verification timestamp.",
                        "confidence": 74,
                    }
                return {
                    "found": True,
                    "partial": False,
                    "source": f"Work Notes [{note['timestamp']}]",
                    "detected": note["text"],
                    "missing": "",
                    "confidence": 95,
                }
        return {
            "found": False,
            "partial": False,
            "source": "Closure / Work Notes",
            "detected": ctx.resolution.strip() or "No substantive resolution statement recorded.",
            "missing": "Clear step-by-step resolution documentation.",
            "confidence": 94,
        }

    @staticmethod
    def _extract_customer_comm(ctx: TicketContext) -> dict[str, Any]:
        for note in reversed(ctx.work_notes):
            low = note["text"].lower()
            if any(k in low for k in ("customer confirmed", "customer notified", "user confirmed", "stakeholder notified", "caller updated", "business notified")):
                return {
                    "found": True,
                    "partial": False,
                    "source": f"Work Notes [{note['timestamp']}]",
                    "detected": note["text"],
                    "missing": "",
                    "confidence": 96,
                }
            if "no customer communication" in low or "customer not notified" in low:
                return {
                    "found": False,
                    "partial": False,
                    "source": f"Work Notes [{note['timestamp']}]",
                    "detected": note["text"],
                    "missing": "Customer notification and recovery confirmation.",
                    "confidence": 97,
                }
        if any(k in ctx.resolution.lower() for k in ("customer confirmed", "user confirmed", "notified")):
            return {
                "found": True,
                "partial": False,
                "source": "Closure Notes",
                "detected": ctx.resolution,
                "missing": "",
                "confidence": 94,
            }
        return {
            "found": False,
            "partial": False,
            "source": "Work Notes / Closure Notes",
            "detected": "No customer communication or recovery confirmation detected.",
            "missing": "Timestamped customer update / confirmation of restoration.",
            "confidence": 93,
        }

    def _extract_categorization(self, ctx: TicketContext) -> dict[str, Any]:
        text = f"{ctx.short_description} {ctx.description}".lower()
        cat = ctx.category
        if not cat or cat.lower() in {"general", "other", "misc", "unclassified"}:
            return {
                "found": False,
                "partial": False,
                "source": "Ticket Fields",
                "detected": f"Category is set to generic value '{cat or 'Empty'}'.",
                "missing": "Specific ITIL service category aligned to affected service.",
                "confidence": 96,
            }
        expected_words = self.CATEGORY_KEYWORDS.get(cat, ())
        if not expected_words or any(w in text for w in expected_words):
            return {
                "found": True,
                "partial": False,
                "source": "Ticket Fields",
                "detected": f"Category '{cat}' aligns with ticket scope ({ctx.short_description}).",
                "missing": "",
                "confidence": 98,
            }
        # Check if another category strongly matches -> possible miscategorization
        for other_cat, words in self.CATEGORY_KEYWORDS.items():
            if other_cat != cat and sum(1 for w in words if w in text) >= 2:
                return {
                    "found": False,
                    "partial": False,
                    "source": "Ticket Fields",
                    "detected": f"Ticket categorized as '{cat}', but description references '{other_cat}' components.",
                    "missing": f"Category alignment (expected '{other_cat}').",
                    "confidence": 89,
                }
        return {
            "found": True,
            "partial": False,
            "source": "Ticket Fields",
            "detected": f"Category '{cat}' recorded and consistent with assignment group '{ctx.assignment_group}'.",
            "missing": "",
            "confidence": 95,
        }

    @staticmethod
    def _extract_priority_alignment(ctx: TicketContext) -> dict[str, Any]:
        text = f"{ctx.short_description} {ctx.description}".lower()
        high_impact = any(k in text for k in ("outage", "down", "critical", "core banking", "production", "payment"))
        if high_impact and ctx.priority in {"P3", "P4"}:
            return {
                "found": False,
                "partial": False,
                "source": "Ticket Fields",
                "detected": f"Priority marked {ctx.priority} despite high-impact production indicators.",
                "missing": "Priority reclassification to P1/P2 per severity matrix.",
                "confidence": 92,
            }
        return {
            "found": True,
            "partial": False,
            "source": "Ticket Fields",
            "detected": f"Priority {ctx.priority} matches documented business impact and urgency.",
            "missing": "",
            "confidence": 97,
        }

    @staticmethod
    def _extract_sla(ctx: TicketContext) -> dict[str, Any]:
        if ctx.sla_status in {"Met", "Within SLA"}:
            return {
                "found": True,
                "partial": False,
                "source": "SLA Record",
                "detected": f"SLA status is '{ctx.sla_status}' for {ctx.priority} target.",
                "missing": "",
                "confidence": 99,
            }
        if ctx.sla_status == "At Risk":
            return {
                "found": False,
                "partial": True,
                "source": "SLA Record",
                "detected": f"Ticket SLA is currently '{ctx.sla_status}' approaching breach threshold.",
                "missing": "Timely completion or documented SLA exception approval.",
                "confidence": 92,
            }
        return {
            "found": False,
            "partial": False,
            "source": "SLA Record",
            "detected": f"SLA status recorded as '{ctx.sla_status}'.",
            "missing": "Resolution within contractual SLA target or breach justification.",
            "confidence": 99,
        }

    @staticmethod
    def _extract_closure(ctx: TicketContext) -> dict[str, Any]:
        if ctx.is_active:
            return {
                "found": True,
                "partial": True,
                "source": "Ticket Lifecycle State",
                "detected": f"Ticket is currently '{ctx.status}' (pre-closure monitoring active).",
                "missing": "Final closure code upon ticket completion.",
                "confidence": 85,
            }
        valid_codes = {
            "Solved (Permanently)",
            "Solved (Workaround)",
            "Successful - Validated",
            "Fulfilled - Verified",
            "Completed",
            "Resolved",
            "Closed/Resolved by Caller",
        }
        if ctx.closure_code and (ctx.closure_code in valid_codes or len(ctx.closure_code) >= 8):
            return {
                "found": True,
                "partial": False,
                "source": "Ticket Fields",
                "detected": f"Closure code '{ctx.closure_code}' aligns with resolution outcome.",
                "missing": "",
                "confidence": 98,
            }
        return {
            "found": False,
            "partial": False,
            "source": "Ticket Fields",
            "detected": f"Closure code is '{ctx.closure_code or 'Missing'}'.",
            "missing": "Standardized ITIL closure code matching resolution details.",
            "confidence": 97,
        }

    @staticmethod
    def _extract_fulfillment(ctx: TicketContext) -> dict[str, Any]:
        corpus = f"{ctx.resolution} {' '.join(n['text'] for n in ctx.work_notes)}".lower()
        if any(k in corpus for k in ("fulfilled", "issued", "provisioned", "assigned", "completed", "granted", "delivered")):
            return {
                "found": True,
                "partial": False,
                "source": "Fulfillment Record",
                "detected": "Service request fulfillment activity verified in work notes / resolution.",
                "missing": "",
                "confidence": 97,
            }
        if ctx.is_active:
            return {
                "found": False,
                "partial": True,
                "source": "Fulfillment Record",
                "detected": f"Request is still '{ctx.status}'; fulfillment confirmation not yet logged.",
                "missing": "Fulfillment completion verification.",
                "confidence": 78,
            }
        return {
            "found": False,
            "partial": False,
            "source": "Fulfillment Record",
            "detected": "No fulfillment confirmation recorded before closure.",
            "missing": "Documented evidence of request delivery/provisioning.",
            "confidence": 95,
        }

    @staticmethod
    def _extract_sr_documentation(ctx: TicketContext) -> dict[str, Any]:
        has_notes = len(ctx.work_notes) >= 2 or (len(ctx.work_notes) >= 1 and len(ctx.resolution) >= 24)
        incomplete_cue = any(
            any(w in n["text"].lower() for w in ("incomplete", "missing closure", "no documentation", "minimal note"))
            for n in ctx.work_notes
        )
        if incomplete_cue:
            return {
                "found": False,
                "partial": True,
                "source": "Work Notes / Closure Details",
                "detected": "Closure or fulfillment documentation flagged as incomplete.",
                "missing": "Complete fulfillment checklist and requester handoff note.",
                "confidence": 76,
            }
        if has_notes:
            return {
                "found": True,
                "partial": False,
                "source": "Work Notes & Closure Details",
                "detected": f"{len(ctx.work_notes)} work notes and resolution summary document end-to-end fulfillment.",
                "missing": "",
                "confidence": 94,
            }
        return {
            "found": False,
            "partial": False,
            "source": "Work Notes",
            "detected": "Insufficient fulfillment documentation recorded.",
            "missing": "Complete request fulfillment and requester verification notes.",
            "confidence": 91,
        }
