# AuditIQ — AI-Powered Audit Lifecycle Platform

> **From Manual Ticket Audits to Continuous Audit Intelligence**

This repository contains the proposal specification, initial prototype, and full-stack **AuditIQ MVP** for an AI-powered ITSM ticket governance platform covering **Incident (INC)**, **Service Request (SR)**, and **Change Request (CR)** auditing.

## Repository Structure

| Path | Description |
|---|---|
| [`AI-Powered Audit Lifecycle Platform.pdf`](./AI-Powered%20Audit%20Lifecycle%20Platform.pdf) | Full 50-page architectural proposal and product specification by Leow Jin Tao |
| [`auditiq-mvp/`](./auditiq-mvp/) | **Full-Stack MVP (v1.0)** — 9-agent FastAPI orchestrator, SQLite/PostgreSQL relational schema, TF-IDF RAG Policy Knowledge Base, real-time WebSocket monitoring, 60-ticket simulated dataset, CSV/JSON ingestion, and modular React + TypeScript application |
| [`auditiq-prototype/`](./auditiq-prototype/) | Initial v0.1 reference prototype (preserved for comparison) |

## Quick Start (MVP)

See [`auditiq-mvp/README.md`](./auditiq-mvp/README.md) for complete documentation, API details, Docker instructions, and the 10-step `CR001992` End-to-End Demo guide.

```bash
# Backend (FastAPI + SQLite + WebSockets + 9 AI Agents)
cd auditiq-mvp/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (React + TypeScript + Vite)
cd auditiq-mvp/frontend
npm install
npm run dev
```
