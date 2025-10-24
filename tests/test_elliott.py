"""Test Elliott Wave analysis module."""

import pytest
from src.signals.elliott import ElliottWaveAnalyzer, WaveType


@pytest.fixture
def sample_candles():
    """Generate sample candle data with pivots."""
    candles = []
    
    # Create an uptrend with clear pivots
    prices = [50000, 51000, 50500, 52000, 51500, 53000, 52500, 52800, 52400, 52600]
    
    for i, price in enumerate(prices * 10):  # Repeat to get enough candles
        candles.append({
            "open": price,
            "high": price + 100,
            "low": price - 100,
            "close": price + 50,
            "volume": 1000,
            "open_time": i * 60000,
        })
    
    return candles


def test_elliott_analyzer_initialization():
    """Test Elliott analyzer initialization."""
    analyzer = ElliottWaveAnalyzer()
    assert analyzer.min_candles == 50


def test_elliott_analysis_insufficient_candles():
    """Test analysis with insufficient candles."""
    analyzer = ElliottWaveAnalyzer()
    result = analyzer.analyze([], "BTCUSDT", "1h")
    
    assert result["signal"] is None
    assert result["confidence"] == 0.0


def test_elliott_analysis_with_candles(sample_candles):
    """Test analysis with sufficient candles."""
    analyzer = ElliottWaveAnalyzer()
    result = analyzer.analyze(sample_candles, "BTCUSDT", "1h")
    
    assert "signal" in result
    assert "confidence" in result
    assert "wave_count" in result
    assert "pivots" in result


def test_elliott_pivot_detection(sample_candles):
    """Test pivot point detection."""
    analyzer = ElliottWaveAnalyzer()
    pivots = analyzer._find_pivots(sample_candles, window=5)
    
    assert isinstance(pivots, list)
    for pivot in pivots:
        assert "type" in pivot
        assert pivot["type"] in ["high", "low"]
        assert "price" in pivot
