"""
AI Agent API endpoints.

POST /api/v1/agent/analyze – full investment research analysis via InvestmentResearchAgent.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.investment_research_agent import InvestmentResearchAgent
from app.agents.structured_output import StockAnalysisResponse
from app.tools.builtin import register_builtin_tools
from app.core.logging import get_logger

logger = get_logger("api.agent")

router = APIRouter()

# Ensure tools are registered on module load
register_builtin_tools()

# Lazy singleton — created once, reused
_agent: Optional[InvestmentResearchAgent] = None


def _get_agent() -> InvestmentResearchAgent:
    global _agent
    if _agent is None:
        _agent = InvestmentResearchAgent()
    return _agent


class AgentAnalyzeRequest(BaseModel):
    symbol: str
    question: Optional[str] = None
    context: Optional[str] = None


@router.post("/analyze")
async def analyze_stock(request: AgentAnalyzeRequest):
    """
    Run full AI investment research analysis on a stock.

    Pipeline: Tools → LLM → Structured Output → Validation → Risk Check
    """
    agent = _get_agent()

    response, trace = await agent.analyze_stock(
        symbol=request.symbol,
        question=request.question,
        context={"extra": request.context} if request.context else None,
    )

    if response is None:
        return {
            "success": False,
            "error": "Analysis failed completely",
            "trace": trace.to_dict(),
        }

    return {
        "success": True,
        "data": response.model_dump(),
        "trace": trace.to_dict(),
    }
