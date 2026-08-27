"""Tests for structured output parsing and validation."""
import json
import pytest

from app.agents.structured_output import (
    StockAnalysisResponse,
    Recommendation,
    DataQuality,
    parse_llm_analysis,
    _extract_json,
    _attempt_repair,
)


class TestStockAnalysisResponse:
    def test_valid_construction(self):
        resp = StockAnalysisResponse(
            symbol="600519.SH",
            name="贵州茅台",
            recommendation=Recommendation.BUY_CANDIDATE,
            overall_score=70.0,
            confidence=0.8,
        )
        assert resp.symbol == "600519.SH"
        assert resp.recommendation == Recommendation.BUY_CANDIDATE
        assert resp.schema_version == "1.0"

    def test_default_values(self):
        resp = StockAnalysisResponse(symbol="000001.SZ")
        assert resp.recommendation == Recommendation.DATA_UNAVAILABLE
        assert resp.confidence == 0.0
        assert resp.overall_score == 0.0
        assert resp.data_quality == DataQuality.UNAVAILABLE

    def test_invalid_recommendation_coerced(self):
        resp = StockAnalysisResponse(symbol="600519.SH", recommendation="STRONG_BUY")
        assert resp.recommendation == Recommendation.DATA_UNAVAILABLE

    def test_score_range_validation(self):
        with pytest.raises(Exception):
            StockAnalysisResponse(symbol="600519.SH", overall_score=150.0)

        with pytest.raises(Exception):
            StockAnalysisResponse(symbol="600519.SH", overall_score=-10.0)

    def test_confidence_range(self):
        with pytest.raises(Exception):
            StockAnalysisResponse(symbol="600519.SH", confidence=1.5)

    def test_model_dump(self):
        resp = StockAnalysisResponse(symbol="600519.SH", name="贵州茅台")
        d = resp.model_dump()
        assert d["symbol"] == "600519.SH"
        assert d["schema_version"] == "1.0"
        assert isinstance(d["bull_case"], list)


class TestExtractJson:
    def test_direct_json(self):
        result = _extract_json('{"symbol": "600519.SH"}')
        assert result["symbol"] == "600519.SH"

    def test_json_with_code_block(self):
        text = 'Here is the analysis:\n```json\n{"symbol": "600519.SH"}\n```\nDone.'
        result = _extract_json(text)
        assert result["symbol"] == "600519.SH"

    def test_json_with_extra_text(self):
        text = 'The analysis shows:\n{"symbol": "600519.SH"}\nThis is good.'
        result = _extract_json(text)
        assert result["symbol"] == "600519.SH"

    def test_invalid_json(self):
        result = _extract_json("not json at all")
        assert result is None

    def test_empty_string(self):
        result = _extract_json("")
        assert result is None


class TestParseLlmAnalysis:
    def test_valid_full_json(self):
        data = {
            "schema_version": "1.0",
            "symbol": "600519.SH",
            "name": "贵州茅台",
            "recommendation": "BUY_CANDIDATE",
            "overall_score": 70.0,
            "confidence": 0.8,
            "technical_score": 72.5,
            "fundamental_score": 68.0,
            "risk_score": 35.0,
            "data_quality": "GOOD",
        }
        resp, err = parse_llm_analysis(json.dumps(data))
        assert err is None
        assert resp.symbol == "600519.SH"
        assert resp.recommendation == Recommendation.BUY_CANDIDATE

    def test_missing_symbol_injected(self):
        data = {"recommendation": "HOLD", "overall_score": 50}
        resp, err = parse_llm_analysis(json.dumps(data), symbol="000001.SZ")
        assert err is None
        assert resp.symbol == "000001.SZ"

    def test_invalid_json_returns_error(self):
        resp, err = parse_llm_analysis("not json")
        assert resp is None
        assert "not valid JSON" in err

    def test_invalid_enum_coerced(self):
        data = {"symbol": "600519.SH", "recommendation": "SUPER_BUY"}
        resp, err = parse_llm_analysis(json.dumps(data))
        assert err is None
        assert resp.recommendation == Recommendation.DATA_UNAVAILABLE

    def test_json_in_markdown_block(self):
        text = '```json\n{"symbol": "600519.SH", "recommendation": "HOLD"}\n```'
        resp, err = parse_llm_analysis(text)
        assert err is None
        assert resp.symbol == "600519.SH"

    def test_json_with_surrounding_text(self):
        text = 'Based on my analysis:\n{"symbol": "600519.SH", "recommendation": "WATCH"}\nThis concludes.'
        resp, err = parse_llm_analysis(text)
        assert err is None
        assert resp.recommendation == Recommendation.WATCH


class TestAttemptRepair:
    def test_repair_missing_fields(self):
        data = {"symbol": "600519.SH"}
        repaired = _attempt_repair(data)
        assert repaired["symbol"] == "600519.SH"
        assert "analysis_timestamp" in repaired
        assert repaired["technical_score"] == 0.0

    def test_repair_out_of_range_scores(self):
        data = {"symbol": "600519.SH", "overall_score": 150.0}
        repaired = _attempt_repair(data)
        assert repaired["overall_score"] == 100.0

    def test_repair_negative_scores(self):
        data = {"symbol": "600519.SH", "overall_score": -10.0}
        repaired = _attempt_repair(data)
        assert repaired["overall_score"] == 0.0

    def test_repair_string_to_list(self):
        data = {"symbol": "600519.SH", "bull_case": "single string"}
        repaired = _attempt_repair(data)
        assert repaired["bull_case"] == ["single string"]

    def test_repair_invalid_data_quality(self):
        data = {"symbol": "600519.SH", "data_quality": "EXCELLENT"}
        repaired = _attempt_repair(data)
        assert repaired["data_quality"] == "UNAVAILABLE"
