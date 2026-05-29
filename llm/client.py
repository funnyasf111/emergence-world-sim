"""OpenAI-compatible chat client (works with OpenAI, local proxies, many providers)."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from llm.settings import LLMSettings

log = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, settings: LLMSettings) -> None:
        self.settings = settings
        if not settings.api_key:
            raise ValueError("LLM enabled but no API key (OPENAI_API_KEY or EMERGENCE_LLM_API_KEY)")

    def chat_with_tools(
        self,
        *,
        model: str,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
    ) -> Tuple[str, Dict[str, Any]]:
        """Returns (tool_name, params dict). Raises on HTTP/parse errors."""
        base = (self.settings.base_url or "https://api.openai.com/v1").rstrip("/")
        url = f"{base}/chat/completions"
        body = {
            "model": model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "required",
            "temperature": 0.7,
        }
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.settings.timeout_s) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM HTTP {e.code}: {err_body[:500]}") from e

        choice = payload["choices"][0]["message"]
        tool_calls = choice.get("tool_calls") or []
        if not tool_calls:
            # Some models return function_call legacy field
            fc = choice.get("function_call")
            if fc:
                name = fc.get("name", "rest")
                args = json.loads(fc.get("arguments") or "{}")
                return name, args
            raise RuntimeError("LLM returned no tool call")

        tc = tool_calls[0]
        fn = tc.get("function", {})
        name = fn.get("name", "rest")
        raw_args = fn.get("arguments") or "{}"
        try:
            args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        except json.JSONDecodeError:
            args = {}
        if not isinstance(args, dict):
            args = {}
        return name, args
