"""Application configuration loaded from environment variables with safe defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "auditiq.db"


@dataclass(frozen=True)
class Settings:
    app_name: str = "AuditIQ — AI-Powered Ticket Audit Intelligence Platform"
    app_version: str = "1.0.0-mvp"
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")
    cors_origins: str = os.getenv("CORS_ORIGINS", "*")
    llm_api_key: str = os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    llm_timeout_seconds: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "15"))

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_key.strip())

    @property
    def active_ai_model_label(self) -> str:
        if self.llm_enabled:
            return f"AuditIQ-Hybrid ({self.llm_model} + Deterministic Rules)"
        return "AuditIQ-Hybrid-v1 (Deterministic Rules + Local NLP Reasoning)"


settings = Settings()
