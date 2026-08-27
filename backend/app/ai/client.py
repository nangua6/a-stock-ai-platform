"""
Unified LLM client – OpenAI-compatible abstraction layer.

Supports MiMo, OpenAI, Claude, Qwen, DeepSeek, Gemini providers.
All LLM calls go through this single client. NEVER call provider APIs directly.
"""
from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from app.config.settings import get_settings
from app.core.logging import get_logger

logger = get_logger("ai.client")


@dataclass
class LLMMessage:
    role: str  # system | user | assistant | tool
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None


@dataclass
class LLMTool:
    type: str = "function"
    function: dict = field(default_factory=dict)


@dataclass
class LLMResponse:
    content: str = ""
    tool_calls: List[dict] = field(default_factory=list)
    model: str = ""
    usage: dict = field(default_factory=dict)
    raw: dict = field(default_factory=dict)


class LLMProvider(ABC):
    """Abstract LLM provider interface."""

    @abstractmethod
    async def chat(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[LLMTool]] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        ...


class OpenAICompatibleProvider(LLMProvider):
    """
    Base for any OpenAI-compatible API (MiMo, DeepSeek, Qwen, etc.).

    Includes retry with exponential backoff and configurable timeout.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 120.0,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay

    async def chat(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[LLMTool]] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Build messages payload (handle tool role + tool_call_id)
        msg_payload = []
        for m in messages:
            entry: dict = {"role": m.role, "content": m.content}
            if m.name:
                entry["name"] = m.name
            if m.tool_call_id:
                entry["tool_call_id"] = m.tool_call_id
            msg_payload.append(entry)

        payload: dict = {
            "model": self.model,
            "messages": msg_payload,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = [{"type": t.type, "function": t.function} for t in tools]

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(url, json=payload, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()

                choice = data.get("choices", [{}])[0]
                msg = choice.get("message", {})
                return LLMResponse(
                    content=msg.get("content", ""),
                    tool_calls=msg.get("tool_calls", []),
                    model=data.get("model", ""),
                    usage=data.get("usage", {}),
                    raw=data,
                )
            except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.ConnectError) as e:
                last_error = e
                delay = self.retry_base_delay * (2 ** attempt)
                logger.warning(
                    "LLM request failed, retrying",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    error=str(e),
                    delay=delay,
                )
                await asyncio.sleep(delay)

        logger.error("LLM request failed after all retries", error=str(last_error))
        raise last_error  # type: ignore[misc]


def get_llm_provider() -> LLMProvider:
    """Factory to get the configured LLM provider."""
    settings = get_settings()
    if not settings.mimo_api_key:
        logger.warning("MIMO_API_KEY not set – LLM calls will fail")
    return OpenAICompatibleProvider(
        base_url=settings.mimo_base_url,
        api_key=settings.mimo_api_key,
        model=settings.mimo_model,
    )
