"""
Time utilities module.

Provides time conversion and formatting functions.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional


def timestamp_to_datetime(timestamp_ms: int) -> datetime:
    """
    Convert millisecond timestamp to datetime.
    
    Args:
        timestamp_ms: Timestamp in milliseconds
    
    Returns:
        Datetime object (UTC)
    """
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)


def datetime_to_timestamp(dt: datetime) -> int:
    """
    Convert datetime to millisecond timestamp.
    
    Args:
        dt: Datetime object
    
    Returns:
        Timestamp in milliseconds
    """
    return int(dt.timestamp() * 1000)


def parse_timeframe(timeframe: str) -> int:
    """
    Parse timeframe string to minutes.
    
    Args:
        timeframe: Timeframe string (e.g., '1m', '5m', '1h', '4h', '1d')
    
    Returns:
        Number of minutes
    """
    timeframe = timeframe.lower()
    
    if timeframe.endswith('m'):
        return int(timeframe[:-1])
    elif timeframe.endswith('h'):
        return int(timeframe[:-1]) * 60
    elif timeframe.endswith('d'):
        return int(timeframe[:-1]) * 60 * 24
    elif timeframe.endswith('w'):
        return int(timeframe[:-1]) * 60 * 24 * 7
    else:
        raise ValueError(f"Invalid timeframe: {timeframe}")


def get_candle_open_time(timestamp_ms: int, timeframe: str) -> int:
    """
    Get the candle open time for a given timestamp and timeframe.
    
    Args:
        timestamp_ms: Timestamp in milliseconds
        timeframe: Timeframe string
    
    Returns:
        Candle open time in milliseconds
    """
    minutes = parse_timeframe(timeframe)
    milliseconds = minutes * 60 * 1000
    
    return (timestamp_ms // milliseconds) * milliseconds


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
    
    Returns:
        Formatted string (e.g., "2h 30m", "45s")
    """
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes}m"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m"
    else:
        days = int(seconds / 86400)
        hours = int((seconds % 86400) / 3600)
        return f"{days}d {hours}h"


def get_date_range(days: int = 30, end_date: Optional[datetime] = None) -> tuple[datetime, datetime]:
    """
    Get date range for backtesting or historical data.
    
    Args:
        days: Number of days
        end_date: End date (defaults to now)
    
    Returns:
        Tuple of (start_date, end_date)
    """
    if end_date is None:
        end_date = datetime.now(timezone.utc)
    
    start_date = end_date - timedelta(days=days)
    
    return start_date, end_date


def is_market_hours(dt: Optional[datetime] = None) -> bool:
    """
    Check if current time is within crypto market hours (always True for crypto).
    
    Args:
        dt: Datetime to check (defaults to now)
    
    Returns:
        True (crypto markets are 24/7)
    """
    # Crypto markets are always open
    return True


def next_candle_close_time(current_time_ms: int, timeframe: str) -> int:
    """
    Calculate the next candle close time.
    
    Args:
        current_time_ms: Current timestamp in milliseconds
        timeframe: Timeframe string
    
    Returns:
        Next candle close time in milliseconds
    """
    candle_open = get_candle_open_time(current_time_ms, timeframe)
    minutes = parse_timeframe(timeframe)
    milliseconds = minutes * 60 * 1000
    
    return candle_open + milliseconds


def time_until_candle_close(current_time_ms: int, timeframe: str) -> int:
    """
    Calculate time until next candle close.
    
    Args:
        current_time_ms: Current timestamp in milliseconds
        timeframe: Timeframe string
    
    Returns:
        Milliseconds until candle close
    """
    next_close = next_candle_close_time(current_time_ms, timeframe)
    return next_close - current_time_ms
