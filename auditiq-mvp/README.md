# AuditIQ — AI-Powered Ticket Audit Intelligence Platform (MVP v1.0)

> **From Manual Ticket Audits to Continuous Audit Intelligence**  
> **Prevent · Audit · Improve**

AuditIQ MVP transforms ITIL ticket governance across **INC (Incident)**, **SR (Service Request)**, and **CR (Change Request)** lifecycles from retrospective manual sampling into continuous, explainable, human-in-the-loop audit assurance.

Built directly from the specification in `../AI-Powered Audit Lifecycle Platform.pdf` and evolving the reference `../auditiq-prototype/` into a full-stack multi-agent MVP with relational persistence, real-time WebSocket monitoring, RAG policy retrieval, closed-loop learning, and live ticket ingestion.

---

## Core Capabilities Implemented

### 1. Multi-Agent Audit Architecture (All 9 Proposal Agents)
| # | Agent | Module | Responsibility |
|---|---|---|---|
| 1 | **Ticket Intelligence Agent** | `backend/app/agents/ticket_intelligence.py` | Extracts and normalizes all 14 ITSM attributes, lifecycle stage, and complexity |
| 2 | **Evidence Extraction Agent** | `backend/app/agents/evidence_extraction.py` | Converts unstructured descriptions, timestamped work notes, approvals & attachments into structured evidence + exact highlight spans |
| 3 | **Audit Rules Agent** | `backend/app/agents/audit_rules.py` | Applies active INC (7), SR (6), and CR (7) deterministic & AI rules grounded in RAG policies |
| 4 | **AI Audit Reasoning Agent** | `backend/app/agents/audit_reasoning.py` | Evaluates evidence via **Three-Way Decision Model (`PASS` / `FAIL` / `REVIEW`)** & **Confidence Framework** (`95–100%` Auto, `80–94%` Recommendation, `<80%` Human Review) |
| 5 | **Risk Scoring Agent** | `backend/app/agents/risk_scoring.py` | 7-factor risk score breakdown, **Predictive Audit** failure probability, and **4-tier Intelligent Sampling** |
| 6 | **Continuous Monitoring Agent** | `backend/app/agents/continuous_monitoring.py` | Detects pre-closure compliance gaps in active tickets, fires & auto-resolves live alerts over WebSocket |
| 7 | **Auditor Copilot** | `backend/app/agents/auditor_copilot.py` | Multi-turn grounded Q&A for single-ticket investigations, fleet-wide queries, similar ticket comparison, and RAG policy lookup |
| 8 | **QC Intelligence Agent** | `backend/app/agents/qc_intelligence.py` | Auditor consistency, scoring variance, outlier flagging, disputed findings, and Closed-Loop Learning feedback analytics |
| 9 | **Management Insight Agent** | `backend/app/agents/management_insight.py` | Executive narratives, compliance trends, top risk areas, recurring root causes, and Target KPIs scorecard |

### 2. All 9 Interactive MVP Screens
1. **Executive Dashboard** — Live KPIs, 6-month compliance trend chart, clickable risk distribution, Management Insight narrative, live pre-closure AI alerts, Prevent/Audit/Improve & Before vs After comparison.
2. **Live Monitoring & Predictive Audit** — WebSocket-connected live monitor, active ticket risk summary, proactive compliance alerts, Predictive Audit risk cards with explicit drivers, and one-click **Simulate Live Change Event**.
3. **Audit Queue** — All 9 governance filters (Ticket Type, Risk, Business Unit, Assignment Group, Auditor, Audit Status, Violation Type, Confidence Tier, Date Range), search, auditor workload cards, batch re-audit, and **CSV/JSON Bulk Upload + Create Ticket**.
4. **Ticket Audit Detail** — Interactive **10-Step CR001992 E2E Demo Walkthrough**, Compliance Score Ring, 7-Factor Risk Breakdown, Audit Criteria table with **Explainable AI Modal** (`Explain`), **Approve / Override / Request Evidence** actions, **Interactive AI Evidence Viewer** with inline highlights, Live Remediation panel, 6-Agent Execution Trace, and **Immutable Governance Audit Trail**.
5. **Auditor Copilot** — Multi-turn conversational assistant supporting ticket-scoped & fleet-wide questions with clickable ticket and policy citations.
6. **QC Intelligence & Closed-Loop Learning** — Auditor consistency & outlier detection, targeted QC exception queue with **Verify / Dispute** modal, and Closed-Loop Learning Feedback Store (`Captured → Queued for Tuning → Applied`).
7. **Analytics & Management Insights** — Compliance by ticket type, department, business unit, failure category breakdown, trend chart, and Target KPIs scorecard.
8. **Audit Policy Knowledge Base (RAG)** — 8 enterprise policies & SOPs (including *Change Governance Policy v3.2*), live TF-IDF cosine-similarity RAG Retrieval Tester, and Add Policy modal.
9. **Audit Configuration** — Persisted confidence & risk thresholds, dynamic sampling %, INC/SR/CR rule weights & toggles, custom rule creation, **Save & Re-Evaluate All Tickets**, and **Reset 60-Ticket Demo Dataset**.

### 3. Enterprise Governance & Roles
- **4 Switchable Personas**: `Auditor`, `QC Reviewer`, `Operations Manager`, `Governance Administrator` (all decisions attributed in the immutable `audit_trail`).
- **Policy Supremacy**: Deterministic policy rules cannot be overridden by AI; overrides require explicit human justification and log to the Closed-Loop Learning `feedback` table.
- **Relational Data Model**: Implements `tickets`, `audits`, `audit_criteria`, `audit_results`, `findings`, `feedback`, `audit_trail`, `policy_documents`, `monitoring_alerts`, and `governance_config` (SQLite by default with zero setup, plus `backend/schema/postgresql.sql` for PostgreSQL).
- **Optional LLM Augmentation**: Runs 100% offline/out-of-the-box with zero API keys; configure `LLM_API_KEY` in `backend/.env` to enable live OpenAI-compatible LLM augmentation.

---

## Quick Start

### Option A — One-Command Launch
- **macOS / Linux:**
  ```bash
  cd auditiq-mvp
  chmod +x start-linux.sh
  ./start-linux.sh
  ```
- **Windows:** Double-click `auditiq-mvp/start-windows.bat`

### Option B — Manual Launch

**1. Backend (Python 3.11+ & FastAPI)**
```bash
cd auditiq-mvp/backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
API interactive docs: `http://localhost:8000/docs`

**2. Frontend (Node.js 20+ & React + TypeScript + Vite)**
```bash
cd auditiq-mvp/frontend
npm install
npm run dev
```
Open `http://localhost:5173` (override API URL with `VITE_API_BASE` if needed).

### Option C — Docker Compose
```bash
cd auditiq-mvp
docker compose up --build
```
To also launch PostgreSQL initialized with `backend/schema/postgresql.sql`:
```bash
docker compose --profile postgres up --build
```

---

## Running Backend Tests
```bash
cd auditiq-mvp/backend
python3 -m unittest discover -s tests -v
```
Tests verify the seeded 60-ticket dataset, all 9 queue filters, the complete 10-step `CR001992` remediation lifecycle (`HIGH → LOW`), human-in-the-loop overrides & Closed-Loop Learning, QC Intelligence, Auditor Copilot & RAG Policy Search, live WebSocket alert streaming, config re-evaluation, and CSV multipart bulk ingestion.

---

## Recommended 3-Minute End-to-End Demo Script (Proposal Section 29)
1. Start on **Executive Dashboard** and click **Launch CR001992 E2E Demo →**.
2. Observe **CR001992** (`Database upgrade — production PostgreSQL cluster`) flagged **HIGH risk** with missing Business Approval (`FAIL`), incomplete Rollback Plan (`REVIEW`, 71% confidence), and missing Post-Implementation Review (`FAIL`).
3. Click **Explain** on Business Approval to show Policy `Change Governance Policy v3.2 §4.2`, detected technical approval, missing business approval, and searched sources.
4. Open the **AI Evidence Viewer** tab to click extracted highlights and spotlight their exact source notes/attachments.
5. Follow the dark top walkthrough bar: **Upload Business Approval → Attach Rollback Runbook → Record PIR Validation → Close Ticket & Finalize Audit**, watching risk drop from **HIGH → LOW** and compliance rise to **100%**.
6. Click **View Updated Dashboard →** and visit **Live Monitoring** to click **Simulate Live Change Event** for real-time WebSocket detection.
7. Upload `sample-data/sample_tickets.csv` via **+ Ingest Tickets** to demonstrate bulk automated auditing.
8. Review **QC & Learning Loop**, **Policy Knowledge Base (RAG)**, and **Audit Configuration**.

*Note: All seeded ticket metrics and compliance trends represent simulated demo data as specified in Section 33 of the proposal.*
