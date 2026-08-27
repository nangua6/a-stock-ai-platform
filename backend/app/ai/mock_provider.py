"""
Mock LLM Provider for testing.

Returns deterministic responses without calling any real LLM API.
Supports: valid structured output, invalid JSON, missing fields, tool calls.
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from app.ai.client import LLMMessage, LLMProvider, LLMResponse, LLMTool
from app.core.logging import get_logger

logger = get_logger("ai.mock")


class MockLLMProvider(LLMProvider):
    """
    Mock LLM for unit tests. Never calls real APIs.

    Usage:
        mock = MockLLMProvider()
        mock.enqueue_response(valid_analysis_json)   # queue a response
        mock.enqueue_tool_call("get_quote", {"symbol": "600519.SH"})  # queue a tool call
        response = await mock.chat(messages)
    """

    def __init__(self):
        self._responses: List[LLMResponse] = []
        self._call_log: List[Dict[str, Any]] = []
        self._default_response_content: str = ""

    def enqueue_response(self, content: str | dict):
        """Queue a text/JSON response to be returned on next chat() call."""
        if isinstance(content, dict):
            content = json.dumps(content, ensure_ascii=False)
        self._responses.append(LLMResponse(content=content, model="mock-llm"))

    def enqueue_tool_call(self, tool_name: str, arguments: dict):
        """Queue a tool call response."""
        self._responses.append(
            LLMResponse(
                content="",
                tool_calls=[
                    {
                        "id": f"call_{uuid.uuid4().hex[:8]}",
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": json.dumps(arguments, ensure_ascii=False),
                        },
                    }
                ],
                model="mock-llm",
            )
        )

    def enqueue_analysis_response(self, symbol: str = "600519.SH", name: str = "贵州茅台"):
        """Queue a valid StockAnalysisResponse JSON."""
        self.enqueue_response({
            "schema_version": "1.0",
            "symbol": symbol,
            "name": name,
            "analysis_timestamp": "2026-08-27T10:00:00Z",
            "data_timestamp": "2026-08-27T09:30:00Z",
            "current_price": 1450.0,
            "change_pct": 1.25,
            "trend": "UP",
            "technical_score": 72.5,
            "fundamental_score": 68.0,
            "risk_score": 35.0,
            "overall_score": 70.0,
            "recommendation": "BUY_CANDIDATE",
            "confidence": 0.78,
            "bull_case": [
                "技术面均线多头排列",
                "基本面ROE稳定在25%以上",
                "行业龙头地位稳固"
            ],
            "bear_case": [
                "当前估值偏高",
                "消费板块整体承压"
            ],
            "key_risks": [
                "估值风险：当前PE高于历史均值",
                "政策风险：白酒消费税调整可能",
                "流动性风险：大盘股波动率较低"
            ],
            "data_quality": "GOOD",
            "data_source": "mock",
        })

    def enqueue_invalid_json(self):
        """Queue an invalid JSON response (for testing parse failure)."""
        self._responses.append(LLMResponse(
            content="This is not valid JSON {{{",
            model="mock-llm",
        ))

    def enqueue_missing_fields_response(self):
        """Queue a JSON response with missing required fields."""
        self.enqueue_response({
            "symbol": "600519.SH",
            # Missing: name, scores, recommendation, etc.
        })

    def enqueue_wrong_enum_response(self):
        """Queue a JSON response with invalid enum values."""
        self.enqueue_response({
            "schema_version": "1.0",
            "symbol": "600519.SH",
            "name": "贵州茅台",
            "recommendation": "STRONG_BUY",  # Invalid enum
            "overall_score": 999,  # Out of range
        })

    def set_default_response(self, content: str):
        """Set a default response when queue is empty."""
        self._default_response_content = content

    @property
    def call_log(self) -> List[Dict[str, Any]]:
        """Access the log of all chat() calls for assertions."""
        return self._call_log

    @property
    def total_calls(self) -> int:
        return len(self._call_log)

    async def chat(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[LLMTool]] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        # Log the call
        self._call_log.append({
            "messages": [{"role": m.role, "content": m.content[:200]} for m in messages],
            "tools": [t.function.get("name", "") for t in (tools or [])],
            "temperature": temperature,
            "max_tokens": max_tokens,
        })

        # Return queued response or default
        if self._responses:
            response = self._responses.pop(0)
        else:
            response = LLMResponse(
                content=self._default_response_content or '{"recommendation": "DATA_UNAVAILABLE"}',
                model="mock-llm",
            )

        logger.info(
            "Mock LLM response",
            content_len=len(response.content),
            tool_calls=len(response.tool_calls),
        )
        return response
