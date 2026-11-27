@echo off
setlocal
cd /d %~dp0

echo === AuditIQ MVP — Starting Backend & Frontend ===

start "AuditIQ MVP Backend" cmd /k "cd backend && python -m pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000"
start "AuditIQ MVP Frontend" cmd /k "cd frontend && npm install && npm run dev"

echo.
echo AuditIQ MVP launched:
echo   Frontend UI : http://localhost:5173
echo   Backend API : http://localhost:8000/docs
echo.
pause
