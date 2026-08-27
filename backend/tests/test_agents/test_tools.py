"""Tests for built-in agent tools."""
import pytest

from app.tools.registry.base import ToolRegistry, ToolPermission, get_tool_registry
from app.tools.builtin import (
    ALL_BUILTIN_TOOLS,
    register_builtin_tools,
    MARKET_DATA_TOOL,
    TECHNICAL_ANALYSIS_TOOL,
    STOCK_SCREENING_TOOL,
    RISK_TOOL,
    PORTFOLIO_TOOL,
)


class TestToolRegistry:
    def test_register_and_get(self):
        registry = ToolRegistry()
        registry.register(MARKET_DATA_TOOL)
        assert registry.get("get_market_data") is not None
        assert registry.get("nonexistent") is None

    def test_list_tools(self):
        registry = ToolRegistry()
        for tool in ALL_BUILTIN_TOOLS:
            registry.register(tool)
        tools = registry.list_tools()
        assert len(tools) == 5

    def test_list_by_permission(self):
        registry = ToolRegistry()
        for tool in ALL_BUILTIN_TOOLS:
            registry.register(tool)
        read_tools = registry.list_tools(permission=ToolPermission.READ_ONLY)
        assert len(read_tools) == 5  # All are READ_ONLY

    def test_to_openai_functions(self):
        registry = ToolRegistry()
        registry.register(MARKET_DATA_TOOL)
        funcs = registry.to_openai_functions()
        assert len(funcs) == 1
        assert funcs[0]["type"] == "function"
        assert funcs[0]["function"]["name"] == "get_market_data"

    @pytest.mark.asyncio
    async def test_execute_not_found(self):
        registry = ToolRegistry()
        with pytest.raises(ValueError, match="Tool not found"):
            await registry.execute("nonexistent", {})

    @pytest.mark.asyncio
    async def test_execute_live_tool_blocked(self):
        from app.tools.registry.base import Tool
        live_tool = Tool(
            name="live_trade",
            description="Live trading",
            parameters={},
            permission=ToolPermission.WRITE_LIVE,
        )
        registry = ToolRegistry()
        registry.register(live_tool)
        with pytest.raises(PermissionError, match="Live tool"):
            await registry.execute("live_trade", {})


class TestToolSchemas:
    def test_market_data_tool_schema(self):
        schema = MARKET_DATA_TOOL.parameters
        assert "action" in schema["properties"]
        assert schema["required"] == ["action"]

    def test_technical_analysis_tool_schema(self):
        schema = TECHNICAL_ANALYSIS_TOOL.parameters
        assert "symbol" in schema["properties"]
        assert schema["required"] == ["symbol"]

    def test_risk_tool_schema(self):
        schema = RISK_TOOL.parameters
        assert "symbol" in schema["properties"]
        assert schema["required"] == ["symbol"]

    def test_portfolio_tool_schema(self):
        schema = PORTFOLIO_TOOL.parameters
        assert "action" in schema["properties"]

    def test_screening_tool_schema(self):
        schema = STOCK_SCREENING_TOOL.parameters
        assert "criteria" in schema["properties"]

    def test_all_tools_have_openai_format(self):
        for tool in ALL_BUILTIN_TOOLS:
            fmt = tool.to_openai_function()
            assert fmt["type"] == "function"
            assert "name" in fmt["function"]
            assert "description" in fmt["function"]
            assert "parameters" in fmt["function"]


class TestToolExecution:
    @pytest.mark.asyncio
    async def test_market_data_get_quote(self):
        result = await MARKET_DATA_TOOL.handler(action="get_quote", symbol="600519.SH")
        assert result["status"] == "OK"
        assert result["symbol"] == "600519.SH"
        assert "data" in result

    @pytest.mark.asyncio
    async def test_market_data_get_quote_no_symbol(self):
        result = await MARKET_DATA_TOOL.handler(action="get_quote")
        assert result["error"] == "INVALID_ARGUMENT"

    @pytest.mark.asyncio
    async def test_market_data_get_kline(self):
        result = await MARKET_DATA_TOOL.handler(action="get_kline", symbol="600519.SH", limit=60)
        assert result["status"] == "OK"
        assert result["count"] > 0

    @pytest.mark.asyncio
    async def test_market_data_invalid_action(self):
        result = await MARKET_DATA_TOOL.handler(action="invalid_action")
        assert "INVALID_ARGUMENT" in result.get("error", "")

    @pytest.mark.asyncio
    async def test_technical_analysis(self):
        result = await TECHNICAL_ANALYSIS_TOOL.handler(symbol="600519.SH")
        assert result["status"] == "OK"
        assert "data" in result
        assert result["kline_count"] > 0

    @pytest.mark.asyncio
    async def test_technical_analysis_no_symbol(self):
        result = await TECHNICAL_ANALYSIS_TOOL.handler(symbol="")
        assert result["error"] == "INVALID_ARGUMENT"

    @pytest.mark.asyncio
    async def test_risk_tool(self):
        result = await RISK_TOOL.handler(symbol="600519.SH")
        assert result["status"] == "OK"
        assert "risk_level" in result
        assert result["risk_level"] in ("LOW", "MEDIUM", "HIGH", "EXTREME")

    @pytest.mark.asyncio
    async def test_risk_tool_no_symbol(self):
        result = await RISK_TOOL.handler(symbol="")
        assert result["error"] == "INVALID_ARGUMENT"

    @pytest.mark.asyncio
    async def test_portfolio_tool(self):
        result = await PORTFOLIO_TOOL.handler(action="get_snapshot")
        assert result["status"] == "OK"
        assert result["mode"] == "paper_trading"
        assert "data" in result

    @pytest.mark.asyncio
    async def test_portfolio_tool_invalid_action(self):
        result = await PORTFOLIO_TOOL.handler(action="invalid")
        assert result["error"] == "INVALID_ARGUMENT"

    @pytest.mark.asyncio
    async def test_screening_tool(self):
        result = await STOCK_SCREENING_TOOL.handler(criteria="trend_strong", top_n=5)
        assert result["status"] == "OK"
        assert "candidates" in result
