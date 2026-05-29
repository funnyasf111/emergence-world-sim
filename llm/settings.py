"""LLM configuration from environment and CLI."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMSettings:
    enabled: bool = False
    model: str = "gpt-4o-mini"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout_s: float = 60.0
    max_tools_in_prompt: int = 28
    request_delay_s: float = 0.0

    @classmethod
    def from_env(
        cls,
        *,
        enabled: bool = False,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> "LLMSettings":
        key = os.environ.get("OPENAI_API_KEY") or os.environ.get("EMERGENCE_LLM_API_KEY")
        return cls(
            enabled=enabled and bool(key),
            model=model or os.environ.get("EMERGENCE_LLM_MODEL", "gpt-4o-mini"),
            api_key=key,
            base_url=base_url or os.environ.get("EMERGENCE_LLM_BASE_URL") or os.environ.get("OPENAI_BASE_URL"),
            timeout_s=float(os.environ.get("EMERGENCE_LLM_TIMEOUT", "60")),
            max_tools_in_prompt=int(os.environ.get("EMERGENCE_LLM_MAX_TOOLS", "28")),
            request_delay_s=float(os.environ.get("EMERGENCE_LLM_DELAY", "0")),
        )

    def model_for_agent(self, agent_id: str) -> str:
        """Per-agent override: EMERGENCE_MODEL_anchor=gpt-4o etc."""
        key = f"EMERGENCE_MODEL_{agent_id.upper()}"
        return os.environ.get(key, self.model)
