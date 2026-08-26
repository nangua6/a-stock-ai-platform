"""Shared test fixtures."""
import pytest

@pytest.fixture
def mock_stock():
    return {
        "symbol": "600519.SH",
        "name": "贵州茅台",
        "price": 1450.0,
        "pre_close": 1440.0,
    }
