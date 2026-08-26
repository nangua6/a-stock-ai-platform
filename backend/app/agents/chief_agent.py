"""
ChiefAgent – the orchestrator that coordinates all other agents.

Responsibilities:
1. Understand user intent
2. Dispatch to appropriate specialist agents
3. Aggregate results
4. Generate final structured output
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent


class ChiefAgent(BaseAgent):
    """Orchestrator agent that coordinates all specialist agents."""

    def __init__(self, agents: Optional[Dict[str, BaseAgent]] = None, **kwargs):
        super().__init__(**kwargs)
        self._agents = agents or {}

    @property
    def name(self) -> str:
        return "ChiefAgent"

    @property
    def system_prompt(self) -> str:
        return """你是A股智能投研平台的首席分析师 (ChiefAgent)。

你的职责：
1. 理解用户的自然语言请求
2. 决定需要调用哪些专业Agent
3. 协调各Agent的工作
4. 汇总分析结果
5. 生成结构化的投资建议

你能调度的专业Agent包括：
- TechnicalAgent: 技术面分析
- FundamentalAgent: 基本面分析
- NewsAgent: 新闻分析
- SentimentAgent: 情绪分析
- RiskAgent: 风险评估
- PortfolioAgent: 组合管理
- StrategyAgent: 策略分析

重要规则：
1. 所有投资建议必须包含风险提示
2. 不能使用"保证赚钱""必涨"等确定性措辞
3. 必须区分事实(FACT)和观点(OPINION)
4. 所有数据必须注明来源和时间
5. 建议必须包含止损、止盈和失效条件
6. 任何交易操作必须经过RiskEngine检查"""

    def register_agent(self, agent: BaseAgent):
        """Register a specialist agent."""
        self._agents[agent.name] = agent

    async def analyze_stock(self, symbol: str, market_data: dict) -> Dict[str, Any]:
        """Full multi-dimensional stock analysis."""
        results = {
            "symbol": symbol,
            "agent": self.name,
            "sub_analyses": {},
        }
        # Dispatch to specialists
        for agent_name, agent in self._agents.items():
            try:
                analysis = await agent.analyze({"symbol": symbol, **market_data})
                results["sub_analyses"][agent_name] = analysis
            except Exception as e:
                self.logger.warning(f"Agent {agent_name} failed", error=str(e))
                results["sub_analyses"][agent_name] = {"error": str(e)}

        return results

    async def analyze_market(self, market_data: dict) -> Dict[str, Any]:
        """Market-level analysis."""
        prompt = f"""请分析今日A股市场状况：

市场数据：
{market_data}

请给出：
1. 市场整体趋势判断
2. 主要指数分析
3. 行业轮动情况
4. 市场情绪评估
5. 今日关注方向
6. 风险事件提醒"""

        analysis = await self.think(prompt)
        return {"agent": self.name, "market_analysis": analysis}

    async def find_candidates(self, criteria: str, stock_list: list) -> List[Dict[str, Any]]:
        """Find candidate stocks based on natural language criteria."""
        prompt = f"""从以下股票中找出符合"{criteria}"的候选股票：

可用股票：
{stock_list}

请输出：
1. 候选股票列表（最多10只）
2. 每只股票的选择理由
3. 风险提示
4. 建议关注级别（高/中/低）"""

        analysis = await self.think(prompt)
        return [{"agent": self.name, "candidates": analysis}]
