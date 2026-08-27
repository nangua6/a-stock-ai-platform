"""
Structured output schemas for AI Agent responses.

All AI-generated analysis must conform to these schemas.
schema_version enables forward-compatible evolution.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator

# ── Recommendation Enum (canonical) ──────────────────────────────────────────

class Recommendation(str, Enum):
    WATCH = "WATCH"
    BUY_CANDIDATE = "BUY_CANDIDATE"
    HOLD = "HOLD"
    REDUCE = "REDUCE"
    AVOID = "AVOID"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"


class DataQuality(str, Enum):
    GOOD = "GOOD"
    STALE = "STALE"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"


# ── Main Analysis Response ───────────────────────────────────────────────────

class EvidenceItem(BaseModel):
    """A piece of evidence supporting the analysis."""
    type: str = Field(default='UNKNOWN', description='Evidence type: MARKET/TECHNICAL/FINANCIAL/NEWS/ANNOUNCEMENT/RISK')
    source: str = Field(default='', description='Data source')
    citation_id: str = Field(default='', description='Unique citation identifier')
    timestamp: str = Field(default='', description='When the evidence was collected')
    summary: str = Field(default='', description='Brief summary of evidence')


class StockAnalysisResponse(BaseModel):
    """
    The canonical AI analysis output.

    All fields are typed and validated. Invalid LLM output cannot pass.
    """
    schema_version: str = Field(default="1.0", description="Schema version for compatibility")

    # Identity
    symbol: str = Field(..., description="Stock symbol, e.g. 600519.SH")
    name: str = Field(default="", description="Stock name")
    analysis_timestamp: str = Field(default="", description="When analysis was performed (ISO)")
    data_timestamp: str = Field(default="", description="When underlying data was last updated (ISO)")

    # Price snapshot (from real quote data)
    current_price: Optional[float] = Field(default=None, description="Latest price from quote")
    change_pct: Optional[float] = Field(default=None, description="Price change %")

    # Scores
    trend: str = Field(default="SIDEWAYS", description="Trend: STRONG_UP/UP/SIDEWAYS/DOWN/STRONG_DOWN")
    technical_score: float = Field(default=0.0, ge=0, le=100, description="Technical score 0-100")
    fundamental_score: float = Field(default=0.0, ge=0, le=100, description="Fundamental score 0-100")
    risk_score: float = Field(default=0.0, ge=0, le=100, description="Risk score 0-100")
    overall_score: float = Field(default=0.0, ge=0, le=100, description="Overall score 0-100")

    # Recommendation
    recommendation: Recommendation = Field(
        default=Recommendation.DATA_UNAVAILABLE,
        description="Investment recommendation",
    )
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence 0.0-1.0")

    # Analysis text
    bull_case: List[str] = Field(default_factory=list, description="Bull case points")
    bear_case: List[str] = Field(default_factory=list, description="Bear case points")
    key_risks: List[str] = Field(default_factory=list, description="Key risk factors")

    # Data provenance
    data_quality: DataQuality = Field(default=DataQuality.UNAVAILABLE, description="Data quality level")
    data_source: str = Field(default="", description="Data source identifier")

    # Evidence and citations
    evidence: List[EvidenceItem] = Field(default_factory=list, description="Evidence supporting the analysis")

    @field_validator("recommendation", mode="before")
    @classmethod
    def validate_recommendation(cls, v: Any) -> Recommendation:
        """Coerce invalid recommendation strings to DATA_UNAVAILABLE."""
        if isinstance(v, Recommendation):
            return v
        try:
            return Recommendation(v)
        except ValueError:
            return Recommendation.DATA_UNAVAILABLE

    @field_validator("schema_version", mode="before")
    @classmethod
    def validate_schema_version(cls, v: Any) -> str:
        return str(v) if v else "1.0"


# ── Parse / Validate / Repair Pipeline ───────────────────────────────────────

def parse_llm_analysis(raw_content: str, symbol: str = "", name: str = "") -> Tuple[Optional[StockAnalysisResponse], Optional[str]]:
    """
    Parse LLM text output into a validated StockAnalysisResponse.

    Returns (response, error_message).
    - If parsing succeeds: (response, None)
    - If parsing fails: (None, error_description)

    Handles:
    1. Valid JSON → parse → validate
    2. JSON with extra text → extract JSON → parse → validate
    3. Missing fields → fill defaults
    4. Invalid enums → coerce to DATA_UNAVAILABLE
    5. Completely invalid → return error
    """
    # Try direct parse
    parsed = _extract_json(raw_content)
    if parsed is None:
        return None, "LLM output is not valid JSON"

    # Inject identity if missing
    if "symbol" not in parsed and symbol:
        parsed["symbol"] = symbol
    if "name" not in parsed and name:
        parsed["name"] = name

    # Inject timestamp if missing
    if not parsed.get("analysis_timestamp"):
        parsed["analysis_timestamp"] = datetime.now(timezone.utc).isoformat()

    try:
        response = StockAnalysisResponse(**parsed)
        return response, None
    except Exception as e:
        # Attempt repair: try with more defaults
        repaired = _attempt_repair(parsed)
        try:
            response = StockAnalysisResponse(**repaired)
            return response, None
        except Exception as e2:
            return None, f"Validation failed after repair: {e2}"


def _extract_json(text: str) -> Optional[dict]:
    """Extract JSON from LLM output (handles markdown code blocks, extra text)."""
    text = text.strip()

    # Try direct JSON parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from ```json ... ``` blocks
    if "```" in text:
        start = text.find("```")
        if start != -1:
            # Skip ```json or ```
            after_fence = text[start + 3:]
            if after_fence.startswith("json"):
                after_fence = after_fence[4:]
            end = after_fence.find("```")
            if end != -1:
                try:
                    return json.loads(after_fence[:end].strip())
                except json.JSONDecodeError:
                    pass

    # Try finding first { to last }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(text[first_brace:last_brace + 1])
        except json.JSONDecodeError:
            pass

    return None


def _attempt_repair(parsed: dict) -> dict:
    """Attempt to repair common issues in parsed JSON."""
    repaired = dict(parsed)

    # Ensure required string fields
    repaired.setdefault("symbol", "")
    repaired.setdefault("name", "")
    repaired.setdefault("analysis_timestamp", datetime.now(timezone.utc).isoformat())
    repaired.setdefault("data_timestamp", "")
    repaired.setdefault("schema_version", "1.0")

    # Ensure numeric fields are in range
    for field_name in ("technical_score", "fundamental_score", "risk_score", "overall_score"):
        val = repaired.get(field_name, 0.0)
        if not isinstance(val, (int, float)):
            repaired[field_name] = 0.0
        else:
            repaired[field_name] = max(0.0, min(100.0, float(val)))

    val = repaired.get("confidence", 0.0)
    if not isinstance(val, (int, float)):
        repaired["confidence"] = 0.0
    else:
        repaired["confidence"] = max(0.0, min(1.0, float(val)))

    # Ensure list fields
    for field_name in ("bull_case", "bear_case", "key_risks"):
        val = repaired.get(field_name, [])
        if isinstance(val, str):
            repaired[field_name] = [val]
        elif not isinstance(val, list):
            repaired[field_name] = []

    # Fix data_quality
    dq = repaired.get("data_quality", "UNAVAILABLE")
    try:
        DataQuality(dq)
    except ValueError:
        repaired["data_quality"] = "UNAVAILABLE"

    return repaired
