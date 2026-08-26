"""Tests for StockAnalysisAgent and structured analysis output."""
import pytest
from app.agents.stock_analysis_agent import StockAnalysisAgent
from app.agents.analysis_result import (
    Recommendation,
    StockAnalysisResult,
    TechnicalScore,
    TrendDirection,
    DataQuality,
    RiskAssessment,
)
from app.market.provider_manager import ProviderManager
from app.market.mock_provider import MockMarketDataProvider
from app.market.cache import MarketDataCache


@pytest.fixture
def agent():
    cache = MarketDataCache()
    provider = ProviderManager(providers=[MockMarketDataProvider()], cache=cache)
    return StockAnalysisAgent(provider=provider)


class TestStockAnalysisAgent:
    @pytest.mark.asyncio
    async def test_analyze_returns_structured_result(self, agent):
        result = await agent.analyze("600519.SH")
        assert isinstance(result, StockAnalysisResult)
        assert result.symbol == "600519.SH"
        assert result.recommendation in Recommendation
        assert 0 <= result.overall_score <= 100
        assert 0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_analyze_has_technical_score(self, agent):
        result = await agent.analyze("600519.SH")
        assert isinstance(result.technical, TechnicalScore)
        assert result.technical.trend in TrendDirection
        assert -1.0 <= result.technical.momentum <= 1.0
        assert 0 <= result.technical.score <= 100

    @pytest.mark.asyncio
    async def test_analyze_has_risk_assessment(self, agent):
        result = await agent.analyze("600519.SH")
        assert isinstance(result.risk, RiskAssessment)
        assert result.risk.risk_level in ("LOW", "MEDIUM", "HIGH", "EXTREME")

    @pytest.mark.asyncio
    async def test_analyze_has_bull_bear(self, agent):
        result = await agent.analyze("600519.SH")
        assert result.bull_case != ""
        assert result.bear_case != ""

    @pytest.mark.asyncio
    async def test_analyze_data_quality(self, agent):
        result = await agent.analyze("600519.SH")
        assert result.data_quality in DataQuality
        assert result.data_source != ""

    @pytest.mark.asyncio
    async def test_to_dict(self, agent):
        result = await agent.analyze("600519.SH")
        d = result.to_dict()
        assert "symbol" in d
        assert "technical" in d
        assert "recommendation" in d
        assert "risk" in d
        assert "data_quality" in d
        assert isinstance(d["recommendation"], str)

    @pytest.mark.asyncio
    async def test_recommendation_is_enum_value(self, agent):
        result = await agent.analyze("600519.SH")
        assert result.recommendation.value in [
            "WATCH", "BUY_CANDIDATE", "HOLD", "REDUCE", "AVOID", "DATA_UNAVAILABLE",
        ]


class TestAnalysisResultTypes:
    def test_technical_score_to_dict(self):
        ts = TechnicalScore(trend=TrendDirection.UP, momentum=0.5, score=65.0)
        d = ts.to_dict()
        assert d["trend"] == "UP"
        assert d["momentum"] == 0.5
        assert d["score"] == 65.0

    def test_risk_assessment_to_dict(self):
        ra = RiskAssessment(volatility=0.3, risk_level="HIGH", key_risks=["test"])
        d = ra.to_dict()
        assert d["risk_level"] == "HIGH"
        assert "test" in d["key_risks"]

    def test_stock_analysis_result_to_dict(self):
        sar = StockAnalysisResult(
            symbol="TEST.SH", recommendation=Recommendation.BUY_CANDIDATE,
            overall_score=75.0, confidence=0.8,
        )
        d = sar.to_dict()
        assert d["symbol"] == "TEST.SH"
        assert d["recommendation"] == "BUY_CANDIDATE"
        assert d["overall_score"] == 75.0
