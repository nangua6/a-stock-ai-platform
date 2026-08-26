"""
Base agent class.

All agents:
- Have a name and system prompt
- Can access tools (but only at their permission level)
- Return structured outputs (validated by Pydantic)
- Log all actions to audit trail
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.ai.client import LLMMessage, LLMProvider, get_llm_provider
from app.core.logging import get_logger


class BaseAgent(ABC):
    """Abstract base agent."""

    def __init__(self, llm: Optional[LLMProvider] = None):
        self.llm = llm or get_llm_provider()
        self.logger = get_logger(f"agent.{self.name}")

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name."""
        ...

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt defining the agent's role."""
        ...

    @property
    def tools(self) -> List[dict]:
        """Tools available to this agent. Override to restrict."""
        return []

    async def think(self, user_message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Send a message to the LLM with this agent's system prompt.
        Returns the LLM's text response.
        """
        messages = [
            LLMMessage(role="system", content=self.system_prompt),
        ]
        if context:
            ctx_str = self._format_context(context)
            messages.append(LLMMessage(role="system", content=f"Context:\n{ctx_str}"))
        messages.append(LLMMessage(role="user", content=user_message))

        self.logger.info("Agent thinking", agent=self.name, message_len=len(user_message))
        response = await self.llm.chat(messages, temperature=0.3)
        self.logger.info("Agent response", agent=self.name, response_len=len(response.content))
        return response.content

    async def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the agent's analysis. Override in subclasses."""
        return {"agent": self.name, "result": "not implemented"}

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dict as a readable string for the LLM."""
        parts = []
        for k, v in context.items():
            parts.append(f"{k}: {v}")
        return "\n".join(parts)
