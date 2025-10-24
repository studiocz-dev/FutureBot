"""Test candle aggregator module."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.ingest.candle_aggregator import CandleAggregator


@pytest.fixture
def mock_supabase():
    """Create mock Supabase client."""
    supabase = MagicMock()
    supabase.insert_candle = AsyncMock()
    supabase.bulk_insert_candles = AsyncMock()
    return supabase


@pytest.fixture
def aggregator(mock_supabase):
    """Create candle aggregator instance."""
    return CandleAggregator(
        supabase=mock_supabase,
        symbols=["BTCUSDT", "ETHUSDT"],
        timeframes=["1h", "4h"],
        window_size=100,
    )


@pytest.mark.asyncio
async def test_aggregator_initialization(aggregator):
    """Test aggregator initialization."""
    assert aggregator.window_size == 100
    assert len(aggregator.symbols) == 2
    assert len(aggregator.timeframes) == 2


@pytest.mark.asyncio
async def test_process_candle(aggregator):
    """Test processing a single candle."""
    candle = {
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "open_time": 1000000,
        "close_time": 1060000,
        "open": 50000,
        "high": 50100,
        "low": 49900,
        "close": 50050,
        "volume": 1000,
        "is_closed": False,
    }
    
    await aggregator.process_candle(candle)
    
    # Check candle was stored
    candles = aggregator.get_candles("BTCUSDT", "1h")
    assert len(candles) == 1
    assert candles[0]["open"] == 50000


@pytest.mark.asyncio
async def test_candle_close_callback(aggregator):
    """Test candle close callback execution."""
    callback_called = False
    callback_data = {}
    
    async def test_callback(symbol, timeframe, candle):
        nonlocal callback_called, callback_data
        callback_called = True
        callback_data = {"symbol": symbol, "timeframe": timeframe}
    
    aggregator.on_candle_close(test_callback)
    
    # Process two candles with different open times
    candle1 = {
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "open_time": 1000000,
        "close_time": 1060000,
        "open": 50000,
        "high": 50100,
        "low": 49900,
        "close": 50050,
        "volume": 1000,
        "is_closed": True,
    }
    
    candle2 = {
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "open_time": 1060000,  # Different open time
        "close_time": 1120000,
        "open": 50050,
        "high": 50150,
        "low": 49950,
        "close": 50100,
        "volume": 1100,
        "is_closed": False,
    }
    
    await aggregator.process_candle(candle1)
    await aggregator.process_candle(candle2)
    
    # Callback should have been triggered when candle2 arrived (candle1 closed)
    assert callback_called
    assert callback_data["symbol"] == "BTCUSDT"


def test_get_latest_candle(aggregator):
    """Test getting latest candle."""
    # Initially should be None
    latest = aggregator.get_latest_candle("BTCUSDT", "1h")
    assert latest is None


def test_get_stats(aggregator):
    """Test getting aggregator statistics."""
    stats = aggregator.get_stats()
    
    assert "total_symbols" in stats
    assert "total_timeframes" in stats
    assert stats["total_symbols"] == 2
    assert stats["total_timeframes"] == 2
