"""Data quality validation service.

Validates market data before persistence. Bad data must NOT go into
production tables – errors are recorded for observability.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger
from app.market.base import KlineData, QuoteData

logger = get_logger("data_quality")

# Symbol format: 6 digits + optional .SH/.SZ/.BJ suffix
_SYMBOL_RE = re.compile(r"^\d{6}(\.(SH|SZ|BJ))?$")


@dataclass
class DataQualityError:
    """Records a single data quality violation."""
    field: str
    value: Any
    rule: str
    message: str

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "value": str(self.value)[:100],
            "rule": self.rule,
            "message": self.message,
        }


@dataclass
class ValidationResult:
    """Result of validating a single data record."""
    is_valid: bool = True
    errors: List[DataQualityError] = field(default_factory=list)

    def add_error(self, field: str, value: Any, rule: str, message: str):
        self.errors.append(DataQualityError(field=field, value=value, rule=rule, message=message))
        self.is_valid = False

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "error_count": len(self.errors),
            "errors": [e.to_dict() for e in self.errors],
        }


class DataQualityService:
    """Validates market data records before persistence."""

    def validate_quote(self, quote: QuoteData) -> ValidationResult:
        """Validate a realtime quote record."""
        result = ValidationResult()

        if not quote.symbol:
            result.add_error("symbol", quote.symbol, "non_empty", "symbol is required")
        elif not _SYMBOL_RE.match(quote.symbol):
            result.add_error("symbol", quote.symbol, "format", f"invalid symbol format: {quote.symbol}")

        if quote.price <= 0:
            result.add_error("price", quote.price, "positive", f"price must be > 0, got {quote.price}")

        if quote.volume < 0:
            result.add_error("volume", quote.volume, "non_negative", f"volume must be >= 0, got {quote.volume}")

        if quote.amount < 0:
            result.add_error("amount", quote.amount, "non_negative", f"amount must be >= 0, got {quote.amount}")

        if not quote.timestamp:
            result.add_error("timestamp", quote.timestamp, "non_empty", "timestamp is required")

        if not quote.data_source:
            result.add_error("data_source", quote.data_source, "non_empty", "data_source is required")

        if not result.is_valid:
            logger.warning("quote_validation_failed", symbol=quote.symbol, errors=result.to_dict())

        return result

    def validate_kline(self, kline: KlineData) -> ValidationResult:
        """Validate a single kline bar."""
        result = ValidationResult()

        if not kline.symbol:
            result.add_error("symbol", kline.symbol, "non_empty", "symbol is required")
        elif not _SYMBOL_RE.match(kline.symbol):
            result.add_error("symbol", kline.symbol, "format", f"invalid symbol format: {kline.symbol}")

        if not kline.trade_date:
            result.add_error("trade_date", kline.trade_date, "non_empty", "trade_date is required")
        elif not _is_valid_date(kline.trade_date):
            result.add_error("trade_date", kline.trade_date, "format", f"invalid date: {kline.trade_date}")

        if kline.open <= 0:
            result.add_error("open", kline.open, "positive", f"open must be > 0")

        if kline.high <= 0:
            result.add_error("high", kline.high, "positive", f"high must be > 0")

        if kline.low <= 0:
            result.add_error("low", kline.low, "positive", f"low must be > 0")

        if kline.close <= 0:
            result.add_error("close", kline.close, "positive", f"close must be > 0")

        if kline.high < kline.low:
            result.add_error(
                "high_low", kline.high, "consistency",
                f"high ({kline.high}) must be >= low ({kline.low})"
            )

        if kline.volume < 0:
            result.add_error("volume", kline.volume, "non_negative", f"volume must be >= 0")

        if kline.amount < 0:
            result.add_error("amount", kline.amount, "non_negative", f"amount must be >= 0")

        if not kline.data_source:
            result.add_error("data_source", kline.data_source, "non_empty", "data_source is required")

        if not result.is_valid:
            logger.warning("kline_validation_failed", symbol=kline.symbol, trade_date=kline.trade_date, errors=result.to_dict())

        return result

    def validate_klines(self, klines: List[KlineData]) -> Dict[str, Any]:
        """Validate a batch of klines. Returns summary with valid/invalid counts."""
        valid = []
        invalid = []
        for k in klines:
            r = self.validate_kline(k)
            if r.is_valid:
                valid.append(k)
            else:
                invalid.append({"kline": k, "errors": r.errors})

        summary = {
            "total": len(klines),
            "valid": len(valid),
            "invalid": len(invalid),
            "valid_klines": valid,
            "invalid_records": invalid,
        }

        if invalid:
            logger.info(
                "kline_batch_validation",
                total=len(klines),
                valid=len(valid),
                invalid=len(invalid),
            )

        return summary

    def validate_symbol(self, symbol: str) -> bool:
        """Check if a symbol matches expected A-share format."""
        return bool(_SYMBOL_RE.match(symbol))


def _is_valid_date(date_str: str) -> bool:
    """Check if a string is a valid YYYY-MM-DD date."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False
