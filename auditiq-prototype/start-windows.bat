@echo off
setlocal
cd /d %~dp0
start "AuditIQ Backend" cmd /k "cd backend && python -m pip install -r requirements.txt && uvicorn app:app --reload --port 8000"
start "AuditIQ Frontend" cmd /k "cd frontend && npm install && npm run dev"
echo AuditIQ started. Open the Vite URL shown in the frontend window.
pause
