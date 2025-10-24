"""
Database models and helper functions.

Provides convenient interfaces for common database operations.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from .supabase_client import SupabaseClient


async def get_or_create_symbol(
    supabase: SupabaseClient,
    symbol: str,
    exchange: str = "BINANCE_FUTURES",
    quote_asset: str = "USDT"
) -> str:
    """
    Get or create a symbol record.
    
    Args:
        supabase: Supabase client
        symbol: Trading symbol
        exchange: Exchange name
        quote_asset: Quote asset
    
    Returns:
        Symbol UUID
    """
    symbol_id = await supabase.get_symbol_id(symbol)
    if symbol_id:
        return symbol_id
    
    return await supabase.create_symbol(symbol, exchange, quote_asset)


async def store_candles(
    supabase: SupabaseClient,
    symbol: str,
    timeframe: str,
    candles: List[Dict[str, Any]],
    bulk: bool = True
) -> None:
    """
    Store candles in the database.
    
    Args:
        supabase: Supabase client
        symbol: Trading symbol
        timeframe: Timeframe
        candles: List of candle data
        bulk: Use bulk insert (faster for many candles)
    """
    if bulk and len(candles) > 1:
        await supabase.bulk_insert_candles(symbol, timeframe, candles)
    else:
        for candle in candles:
            await supabase.insert_candle(symbol, timeframe, candle)


async def create_signal(
    supabase: SupabaseClient,
    symbol: str,
    timeframe: str,
    signal_type: str,
    entry_price: float,
    stop_loss: float,
    take_profit: float,
    confidence: float,
    **kwargs
) -> Optional[str]:
    """
    Create a trading signal.
    
    Args:
        supabase: Supabase client
        symbol: Trading symbol
        timeframe: Timeframe
        signal_type: LONG or SHORT
        entry_price: Entry price
        stop_loss: Stop loss price
        take_profit: Take profit price
        confidence: Confidence score (0-1)
        **kwargs: Additional signal fields
    
    Returns:
        Signal ID or None on error
    """
    signal = {
        "symbol": symbol,
        "timeframe": timeframe,
        "type": signal_type,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "confidence": confidence,
        **kwargs
    }
    
    return await supabase.insert_signal(signal)


async def get_signal_history(
    supabase: SupabaseClient,
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    days: int = 7
) -> List[Dict[str, Any]]:
    """
    Get signal history for the past N days.
    
    Args:
        supabase: Supabase client
        symbol: Optional symbol filter
        timeframe: Optional timeframe filter
        days: Number of days to look back
    
    Returns:
        List of signals
    """
    # For now, just get recent signals
    # In a production system, you'd add date filtering
    return await supabase.get_recent_signals(symbol, timeframe, limit=100)


async def get_candle_history(
    supabase: SupabaseClient,
    symbol: str,
    timeframe: str,
    limit: int = 500
) -> List[Dict[str, Any]]:
    """
    Get candle history from the database.
    
    Args:
        supabase: Supabase client
        symbol: Trading symbol
        timeframe: Timeframe
        limit: Maximum number of candles
    
    Returns:
        List of candles
    """
    return await supabase.get_candles(symbol, timeframe, limit=limit)


def candle_to_ohlcv(candle: Dict[str, Any]) -> tuple:
    """
    Convert candle dict to OHLCV tuple.
    
    Args:
        candle: Candle dictionary
    
    Returns:
        Tuple of (open, high, low, close, volume)
    """
    return (
        float(candle["open"]),
        float(candle["high"]),
        float(candle["low"]),
        float(candle["close"]),
        float(candle["volume"]),
    )


def candles_to_dataframe(candles: List[Dict[str, Any]]):
    """
    Convert list of candles to pandas DataFrame.
    
    Args:
        candles: List of candle dictionaries
    
    Returns:
        pandas DataFrame with OHLCV data
    """
    import pandas as pd
    from datetime import datetime
    
    if not candles:
        return pd.DataFrame()
    
    df = pd.DataFrame(candles)
    
    # Convert timestamps to datetime
    if "open_time" in df.columns:
        df["datetime"] = pd.to_datetime(df["open_time"], unit="ms")
        df.set_index("datetime", inplace=True)
    
    # Ensure numeric types
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    
    return df


def calculate_signal_risk_reward(
    entry: float,
    stop_loss: float,
    take_profit: float,
    signal_type: str
) -> Dict[str, float]:
    """
    Calculate risk/reward metrics for a signal.
    
    Args:
        entry: Entry price
        stop_loss: Stop loss price
        take_profit: Take profit price
        signal_type: LONG or SHORT
    
    Returns:
        Dictionary with risk/reward metrics
    """
    if signal_type == "LONG":
        risk = abs(entry - stop_loss)
        reward = abs(take_profit - entry)
    else:  # SHORT
        risk = abs(stop_loss - entry)
        reward = abs(entry - take_profit)
    
    risk_reward_ratio = reward / risk if risk > 0 else 0
    risk_percent = (risk / entry) * 100
    reward_percent = (reward / entry) * 100
    
    return {
        "risk": risk,
        "reward": reward,
        "risk_reward_ratio": risk_reward_ratio,
        "risk_percent": risk_percent,
        "reward_percent": reward_percent,
    }
