#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
python3 -m pip install -r backend/requirements.txt
(cd backend && uvicorn app:app --reload --port 8000) &
(cd frontend && npm install && npm run dev)
