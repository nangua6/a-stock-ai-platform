"""
MCP-style tool registry.

Every tool has:
- A name and description
- Input schema (JSON Schema)
- Permission level (READ_ONLY, WRITE_PAPER, WRITE_LIVE)
- An execute() function
- Full audit logging
"""
from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from app.core.logging import get_logger

logger = get_logger("tools")


class ToolPermission(str, enum.Enum):
    READ_ONLY = "READ_ONLY"       # Query market data, financials, news, account info
    WRITE_PAPER = "WRITE_PAPER"    # Paper trading operations
    WRITE_LIVE = "WRITE_LIVE"      # Live trading – DEFAULT DISABLED


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict  # JSON Schema
    permission: ToolPermission = ToolPermission.READ_ONLY
    handler: Optional[Callable] = None

    def to_openai_function(self) -> dict:
        """Convert to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Central registry for all tools."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool
        logger.info("Tool registered", name=tool.name, permission=tool.permission.value)

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self, permission: Optional[ToolPermission] = None) -> List[Tool]:
        tools = list(self._tools.values())
        if permission:
            tools = [t for t in tools if t.permission == permission]
        return tools

    def to_openai_functions(self, permission: Optional[ToolPermission] = None) -> List[dict]:
        return [t.to_openai_function() for t in self.list_tools(permission)]

    async def execute(self, name: str, arguments: dict) -> Any:
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Tool not found: {name}")
        if tool.permission == ToolPermission.WRITE_LIVE:
            raise PermissionError(f"Live tool '{name}' is disabled by default")
        if tool.handler is None:
            raise ValueError(f"Tool '{name}' has no handler")
        logger.info("Executing tool", name=name, args=arguments)
        result = await tool.handler(**arguments)
        logger.info("Tool result", name=name, success=True)
        return result


# Global tool registry singleton
_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry
