"""Test signal fuser module."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.signals.fuse import SignalFuser


@pytest.fixture
def mock_supabase():
    """Create mock Supabase client."""
    supabase = MagicMock()
    supabase.insert_signal = AsyncMock(return_value="signal-123")
    supabase.get_candles = AsyncMock(return_value=[])
    return supabase


@pytest.fixture
def sample_candles():
    """Generate sample candles."""
    return [
        {
            "open": 50000 + i,
            "high": 50100 + i,
            "low": 49900 + i,
            "close": 50050 + i,
            "volume": 1000,
            "open_time": i * 60000,
        }
        for i in range(100)
    ]


def test_fuser_initialization(mock_supabase):
    """Test signal fuser initialization."""
    fuser = SignalFuser(
        supabase=mock_supabase,
        min_confidence=0.65,
        enable_wyckoff=True,
        enable_elliott=True,
    )
    
    assert fuser.min_confidence == 0.65
    assert fuser.enable_wyckoff is True
    assert fuser.enable_elliott is True


@pytest.mark.asyncio
async def test_generate_signal_cooldown(mock_supabase, sample_candles):
    """Test signal cooldown mechanism."""
    fuser = SignalFuser(
        supabase=mock_supabase,
        min_confidence=0.65,
        cooldown=60,  # 60 second cooldown
    )
    
    current_candle = sample_candles[-1]
    
    # First signal
    signal1 = await fuser.generate_signal(
        "BTCUSDT",
        "1h",
        current_candle,
        sample_candles[:-1]
    )
    
    # Second signal immediately (should be blocked by cooldown)
    signal2 = await fuser.generate_signal(
        "BTCUSDT",
        "1h",
        current_candle,
        sample_candles[:-1]
    )
    
    # If first signal was generated, second should be None due to cooldown
    if signal1:
        assert signal2 is None


def test_fuser_stats(mock_supabase):
    """Test fuser statistics retrieval."""
    fuser = SignalFuser(
        supabase=mock_supabase,
        min_confidence=0.7,
        enable_wyckoff=True,
        enable_elliott=False,
        cooldown=300,
    )
    
    stats = fuser.get_stats()
    
    assert stats["min_confidence"] == 0.7
    assert stats["wyckoff_enabled"] is True
    assert stats["elliott_enabled"] is False
    assert stats["cooldown_seconds"] == 300
