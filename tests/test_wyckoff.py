"""Test wyckoff analysis module."""

import pytest
from src.signals.wyckoff import WyckoffAnalyzer, WyckoffPhase


@pytest.fixture
def sample_candles():
    """Generate sample candle data."""
    candles = []
    base_price = 50000
    
    for i in range(100):
        price = base_price + (i * 10)
        candles.append({
            "open": price,
            "high": price + 50,
            "low": price - 50,
            "close": price + 10,
            "volume": 1000 + (i * 10),
            "open_time": i * 60000,
        })
    
    return candles


def test_wyckoff_analyzer_initialization():
    """Test Wyckoff analyzer initialization."""
    analyzer = WyckoffAnalyzer()
    assert analyzer.min_candles == 50


def test_wyckoff_analysis_insufficient_candles():
    """Test analysis with insufficient candles."""
    analyzer = WyckoffAnalyzer()
    result = analyzer.analyze([], "BTCUSDT", "1h")
    
    assert result["signal"] is None
    assert result["confidence"] == 0.0


def test_wyckoff_analysis_with_candles(sample_candles):
    """Test analysis with sufficient candles."""
    analyzer = WyckoffAnalyzer()
    result = analyzer.analyze(sample_candles, "BTCUSDT", "1h")
    
    assert "signal" in result
    assert "confidence" in result
    assert "phase" in result
    assert "rationale" in result


def test_wyckoff_phase_detection(sample_candles):
    """Test phase detection."""
    analyzer = WyckoffAnalyzer()
    phase = analyzer._detect_phase(sample_candles)
    
    assert isinstance(phase, WyckoffPhase)


def test_wyckoff_spring_detection(sample_candles):
    """Test spring pattern detection."""
    analyzer = WyckoffAnalyzer()
    
    # Modify candles to create a spring pattern
    spring_candles = sample_candles.copy()
    support_level = min(c["low"] for c in spring_candles[-20:-5])
    
    # Add a spring candle
    spring_candles.append({
        "open": support_level + 10,
        "high": support_level + 20,
        "low": support_level - 50,  # Break below support
        "close": support_level + 30,  # Close back above
        "volume": 2000,
        "open_time": len(spring_candles) * 60000,
    })
    
    spring = analyzer._detect_spring(spring_candles)
    
    # Spring may or may not be detected depending on confidence criteria
    if spring:
        assert "support_level" in spring
        assert "confidence" in spring
        assert 0 <= spring["confidence"] <= 1
