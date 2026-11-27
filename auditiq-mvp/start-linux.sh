#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo "=== AuditIQ MVP — Starting Backend & Frontend ==="

if [ ! -d "backend/.venv" ]; then
  python3 -m venv backend/.venv
fi
source backend/.venv/bin/activate
python -m pip install --quiet -r backend/requirements.txt

(
  cd backend
  uvicorn app.main:app --reload --port 8000
) &
BACKEND_PID=$!

trap 'kill "$BACKEND_PID" 2>/dev/null || true' EXIT

cd frontend
if [ ! -d "node_modules" ]; then
  npm install
fi

echo "Backend API:  http://localhost:8000/docs"
echo "Frontend App: http://localhost:5173"
npm run dev
