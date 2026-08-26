"""
Specialist agents for the trading platform.
Each focuses on a specific domain of stock analysis.
"""
from __future__ import annotations

from typing import Any, Dict

from app.agents.base import BaseAgent


class TechnicalAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "TechnicalAgent"

    @property
    def system_prompt(self) -> str:
        return """你是A股技术面分析专家。
分析内容：K线形态、均线系统、MACD、RSI、KDJ、布林带、成交量、趋势线。
输出格式：技术面评分(0-100)、趋势判断、关键支撑/阻力位、技术信号。"""

    async def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        symbol = data.get("symbol", "")
        prompt = f"请对 {symbol} 进行技术面分析。数据: {data}"
        result = await self.think(prompt)
        return {"agent": self.name, "symbol": symbol, "analysis": result}


class FundamentalAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "FundamentalAgent"

    @property
    def system_prompt(self) -> str:
        return """你是A股基本面分析专家。
分析内容：营收增长、净利润、ROE、PE、PB、现金流、毛利率、行业地位。
输出格式：基本面评分(0-100)、估值判断、成长性评估。"""

    async def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        symbol = data.get("symbol", "")
        prompt = f"请对 {symbol} 进行基本面分析。数据: {data}"
        result = await self.think(prompt)
        return {"agent": self.name, "symbol": symbol, "analysis": result}


class NewsAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "NewsAgent"

    @property
    def system_prompt(self) -> str:
        return """你是A股新闻分析师。
分析内容：重大新闻、公告解读、政策影响、行业动态。
注意区分事实(FACT)和观点(OPINION)。"""

    async def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        symbol = data.get("symbol", "")
        prompt = f"请分析 {symbol} 相关新闻和公告。数据: {data}"
        result = await self.think(prompt)
        return {"agent": self.name, "symbol": symbol, "analysis": result}


class SentimentAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "SentimentAgent"

    @property
    def system_prompt(self) -> str:
        return """你是A股市场情绪分析师。
分析内容：市场情绪指标、资金流向、涨跌停数量、北向资金、融资融券。
输出：情绪评分(极度恐惧-恐惧-中性-贪婪-极度贪婪)。"""

    async def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"请分析市场情绪。数据: {data}"
        result = await self.think(prompt)
        return {"agent": self.name, "analysis": result}


class RiskAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "RiskAgent"

    @property
    def system_prompt(self) -> str:
        return """你是A股风险评估专家。
分析内容：个股风险、行业风险、市场风险、流动性风险、系统性风险。
输出：风险等级(低/中/高/极高)、主要风险因素、失效条件。"""

    async def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        symbol = data.get("symbol", "")
        prompt = f"请评估 {symbol} 的风险。数据: {data}"
        result = await self.think(prompt)
        return {"agent": self.name, "symbol": symbol, "analysis": result}
