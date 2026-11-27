"""Shared agent data structures and optional OpenAI-compatible LLM client wrapper."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from app.config import settings


@dataclass
class AgentStepTrace:
    agent_number: int
    agent_name: str
    phase: str
    status: str
    duration_ms: float
    summary: str
    model: str = "Deterministic + Local NLP"
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agentNumber": self.agent_number,
            "agentName": self.agent_name,
            "phase": self.phase,
            "status": self.status,
            "durationMs": round(self.duration_ms, 2),
            "summary": self.summary,
            "model": self.model,
            "metrics": self.metrics,
        }


class OptionalLLMClient:
    """Zero-dependency OpenAI-compatible HTTP client used ONLY when LLM_API_KEY is set.

    When unconfigured or unreachable, callers fall back cleanly to AuditIQ's
    deterministic + local NLP reasoning layer so the platform works offline.
    """

    def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 420,
    ) -> str | None:
        if not settings.llm_enabled:
            return None
        endpoint = settings.llm_base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": settings.llm_model,
            "temperature": 0.15,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.llm_api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=settings.llm_timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"].strip()
        except (urllib.error.URLError, KeyError, ValueError, TimeoutError):
            return None


llm_client = OptionalLLMClient()


def timer_start() -> float:
    return time.perf_counter()


def elapsed_ms(start: float) -> float:
    return max(0.4, (time.perf_counter() - start) * 1000.0)
