# AuditIQ — AI-Powered Ticket Audit Intelligence Platform

A runnable prototype based on the supplied AuditIQ proposal.

## What is included
- Executive Dashboard
- Live Monitoring
- Audit Queue
- Ticket Audit Detail
- Auditor Copilot
- QC Dashboard
- Analytics
- Audit Configuration
- Mock INC / SR / CR ticket dataset
- Deterministic audit rules + simulated AI reasoning
- PASS / FAIL / REVIEW decision model
- Risk scoring
- Evidence viewer / explainability
- Human override + feedback loop
- Proactive monitoring for open/high-risk tickets

## Architecture
Frontend: React + TypeScript + Vite
Backend: Python + FastAPI
Data: in-memory mock dataset for demo
AI: deterministic simulation layer that follows the proposal's agent flow; replaceable with an enterprise LLM/RAG service.

## Run
### Backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Open the URL printed by Vite, typically http://localhost:5173.

The frontend expects the API at http://localhost:8000. You can change it with VITE_API_BASE.

## Demo flow
1. Open **Live Monitoring** to see proactive risks.
2. Open **Audit Queue** and select **CR001992**.
3. Review the missing business approval and incomplete rollback evidence.
4. Use **Explain** / the evidence panel.
5. Click **Resolve approval gap** to simulate the business approval arriving.
6. Re-run the audit and observe the risk moving from HIGH toward LOW.
7. Use **Auditor Copilot** for evidence-backed questions.
8. Review **QC Dashboard** and **Analytics** for consistency and trend views.

All figures are mock/demo data, not production metrics. The proposal explicitly says example numbers should be presented as mock data. 
