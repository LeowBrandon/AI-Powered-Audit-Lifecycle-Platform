"""AuditIQ MVP FastAPI entrypoint with WebSocket live monitoring & automatic startup seeding."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import analytics, config, copilot, dashboard, knowledge, monitoring, qc, tickets
from app.seed import ensure_seeded
from app.services.websocket_manager import ws_manager


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ws_manager.set_loop(asyncio.get_running_loop())
    init_db()
    ensure_seeded()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "AI-Powered Ticket Audit Intelligence Platform combining 9 specialized AI Agents, "
        "deterministic audit rules, RAG policy retrieval, real-time monitoring, explainable AI, "
        "and human-in-the-loop governance."
    ),
    lifespan=lifespan,
)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()] or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)
app.include_router(tickets.router)
app.include_router(monitoring.router)
app.include_router(copilot.router)
app.include_router(qc.router)
app.include_router(analytics.router)
app.include_router(knowledge.router)
app.include_router(config.router)


@app.get("/api/health", tags=["System"])
def health():
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "aiModel": settings.active_ai_model_label,
        "llmEnabled": settings.llm_enabled,
        "wsClients": ws_manager.active_connections,
    }


@app.websocket("/ws/monitoring")
async def monitoring_websocket(websocket: WebSocket):
    """Real-time WebSocket stream for live alerts, ticket ingestion, and audit updates."""
    await ws_manager.connect(websocket)
    try:
        while True:
            text = await websocket.receive_text()
            if text.strip().lower() == "ping":
                await websocket.send_json({"event": "pong"})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)
