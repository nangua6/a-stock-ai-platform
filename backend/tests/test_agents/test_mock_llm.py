"""Tests for MockLLMProvider."""
import json
import pytest

from app.ai.mock_provider import MockLLMProvider
from app.ai.client import LLMMessage


@pytest.fixture
def mock_llm():
    return MockLLMProvider()


class TestMockLLMProvider:
    @pytest.mark.asyncio
    async def test_enqueue_valid_json_response(self, mock_llm):
        data = {"recommendation": "BUY_CANDIDATE", "overall_score": 75}
        mock_llm.enqueue_response(data)

        messages = [LLMMessage(role="user", content="test")]
        response = await mock_llm.chat(messages)

        parsed = json.loads(response.content)
        assert parsed["recommendation"] == "BUY_CANDIDATE"
        assert parsed["overall_score"] == 75

    @pytest.mark.asyncio
    async def test_enqueue_string_response(self, mock_llm):
        mock_llm.enqueue_response("plain text response")

        messages = [LLMMessage(role="user", content="test")]
        response = await mock_llm.chat(messages)

        assert response.content == "plain text response"

    @pytest.mark.asyncio
    async def test_enqueue_analysis_response(self, mock_llm):
        mock_llm.enqueue_analysis_response("600519.SH", "贵州茅台")

        messages = [LLMMessage(role="user", content="test")]
        response = await mock_llm.chat(messages)

        parsed = json.loads(response.content)
        assert parsed["symbol"] == "600519.SH"
        assert parsed["name"] == "贵州茅台"
        assert parsed["recommendation"] == "BUY_CANDIDATE"

    @pytest.mark.asyncio
    async def test_enqueue_tool_call(self, mock_llm):
        mock_llm.enqueue_tool_call("get_quote", {"symbol": "600519.SH"})

        messages = [LLMMessage(role="user", content="test")]
        response = await mock_llm.chat(messages)

        assert len(response.tool_calls) == 1
        assert response.tool_calls[0]["function"]["name"] == "get_quote"
        assert "600519.SH" in response.tool_calls[0]["function"]["arguments"]

    @pytest.mark.asyncio
    async def test_enqueue_invalid_json(self, mock_llm):
        mock_llm.enqueue_invalid_json()

        messages = [LLMMessage(role="user", content="test")]
        response = await mock_llm.chat(messages)

        with pytest.raises(json.JSONDecodeError):
            json.loads(response.content)

    @pytest.mark.asyncio
    async def test_enqueue_missing_fields(self, mock_llm):
        mock_llm.enqueue_missing_fields_response()

        messages = [LLMMessage(role="user", content="test")]
        response = await mock_llm.chat(messages)

        parsed = json.loads(response.content)
        assert "symbol" in parsed
        assert "name" not in parsed  # Missing field

    @pytest.mark.asyncio
    async def test_enqueue_wrong_enum(self, mock_llm):
        mock_llm.enqueue_wrong_enum_response()

        messages = [LLMMessage(role="user", content="test")]
        response = await mock_llm.chat(messages)

        parsed = json.loads(response.content)
        assert parsed["recommendation"] == "STRONG_BUY"  # Invalid enum

    @pytest.mark.asyncio
    async def test_default_response_when_empty(self, mock_llm):
        messages = [LLMMessage(role="user", content="test")]
        response = await mock_llm.chat(messages)

        parsed = json.loads(response.content)
        assert parsed["recommendation"] == "DATA_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_custom_default_response(self, mock_llm):
        mock_llm.set_default_response('{"status": "custom"}')

        messages = [LLMMessage(role="user", content="test")]
        response = await mock_llm.chat(messages)

        parsed = json.loads(response.content)
        assert parsed["status"] == "custom"

    @pytest.mark.asyncio
    async def test_fifo_order(self, mock_llm):
        mock_llm.enqueue_response({"first": True})
        mock_llm.enqueue_response({"second": True})

        messages = [LLMMessage(role="user", content="test")]

        r1 = await mock_llm.chat(messages)
        r2 = await mock_llm.chat(messages)

        assert json.loads(r1.content)["first"] is True
        assert json.loads(r2.content)["second"] is True

    @pytest.mark.asyncio
    async def test_call_logging(self, mock_llm):
        mock_llm.enqueue_response({"ok": True})

        messages = [LLMMessage(role="user", content="hello world")]
        await mock_llm.chat(messages, temperature=0.5)

        assert mock_llm.total_calls == 1
        assert mock_llm.call_log[0]["temperature"] == 0.5
        assert "hello world" in mock_llm.call_log[0]["messages"][0]["content"]

    @pytest.mark.asyncio
    async def test_tool_names_logged(self, mock_llm):
        from app.ai.client import LLMTool

        mock_llm.enqueue_response({"ok": True})
        messages = [LLMMessage(role="user", content="test")]
        tools = [LLMTool(function={"name": "get_quote", "parameters": {}})]

        await mock_llm.chat(messages, tools=tools)

        assert "get_quote" in mock_llm.call_log[0]["tools"]
