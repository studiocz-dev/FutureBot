"""
Metrics tracking module.

Tracks bot performance metrics and statistics.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import threading


class Metrics:
    """Tracks bot performance metrics."""
    
    def __init__(self):
        """Initialize metrics tracker."""
        self.lock = threading.Lock()
        
        # Signal counters: {symbol: {timeframe: {type: count}}}
        self.signal_counts: Dict[str, Dict[str, Dict[str, int]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(int))
        )
        
        # Total signals by type
        self.total_signals_by_type: Dict[str, int] = defaultdict(int)
        
        # Signal timestamps for time-based analysis
        self.signal_timestamps: List[tuple] = []  # [(timestamp, symbol, timeframe, type)]
        
        # Performance metrics (for future use)
        self.hits: int = 0
        self.stops: int = 0
        self.pending: int = 0
        
        # Start time
        self.start_time = datetime.utcnow()
    
    def increment_signal(self, symbol: str, timeframe: str, signal_type: str) -> None:
        """
        Increment signal counter.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            signal_type: Signal type (LONG/SHORT)
        """
        with self.lock:
            self.signal_counts[symbol][timeframe][signal_type] += 1
            self.total_signals_by_type[signal_type] += 1
            self.signal_timestamps.append((datetime.utcnow(), symbol, timeframe, signal_type))
    
    def increment_hit(self) -> None:
        """Increment hit counter (signal reached TP)."""
        with self.lock:
            self.hits += 1
    
    def increment_stop(self) -> None:
        """Increment stop counter (signal hit SL)."""
        with self.lock:
            self.stops += 1
    
    def get_signal_count(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        signal_type: Optional[str] = None
    ) -> int:
        """
        Get signal count with optional filters.
        
        Args:
            symbol: Optional symbol filter
            timeframe: Optional timeframe filter
            signal_type: Optional signal type filter
        
        Returns:
            Signal count
        """
        with self.lock:
            if symbol and timeframe and signal_type:
                return self.signal_counts.get(symbol, {}).get(timeframe, {}).get(signal_type, 0)
            elif symbol and timeframe:
                return sum(self.signal_counts.get(symbol, {}).get(timeframe, {}).values())
            elif symbol:
                return sum(
                    sum(tf_counts.values())
                    for tf_counts in self.signal_counts.get(symbol, {}).values()
                )
            elif signal_type:
                return self.total_signals_by_type.get(signal_type, 0)
            else:
                return sum(self.total_signals_by_type.values())
    
    def get_signals_last_hour(self) -> int:
        """Get number of signals in the last hour."""
        with self.lock:
            cutoff = datetime.utcnow() - timedelta(hours=1)
            return sum(1 for ts, _, _, _ in self.signal_timestamps if ts >= cutoff)
    
    def get_signals_today(self) -> int:
        """Get number of signals today."""
        with self.lock:
            today = datetime.utcnow().date()
            return sum(1 for ts, _, _, _ in self.signal_timestamps if ts.date() == today)
    
    def get_win_rate(self) -> float:
        """
        Calculate win rate.
        
        Returns:
            Win rate (0-1) or 0 if no closed positions
        """
        with self.lock:
            total_closed = self.hits + self.stops
            if total_closed == 0:
                return 0.0
            return self.hits / total_closed
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get metrics summary.
        
        Returns:
            Dictionary with metrics summary
        """
        with self.lock:
            uptime = datetime.utcnow() - self.start_time
            
            return {
                "uptime_seconds": int(uptime.total_seconds()),
                "uptime_formatted": self._format_uptime(uptime),
                "total_signals": self.get_signal_count(),
                "long_signals": self.get_signal_count(signal_type="LONG"),
                "short_signals": self.get_signal_count(signal_type="SHORT"),
                "signals_last_hour": self.get_signals_last_hour(),
                "signals_today": self.get_signals_today(),
                "hits": self.hits,
                "stops": self.stops,
                "pending": self.pending,
                "win_rate": self.get_win_rate(),
            }
    
    def get_detailed_stats(self) -> Dict[str, Any]:
        """
        Get detailed statistics by symbol and timeframe.
        
        Returns:
            Detailed statistics dictionary
        """
        with self.lock:
            stats = {
                "by_symbol": {},
                "by_timeframe": defaultdict(int),
                "by_type": dict(self.total_signals_by_type),
            }
            
            for symbol, timeframes in self.signal_counts.items():
                stats["by_symbol"][symbol] = {}
                for timeframe, types in timeframes.items():
                    stats["by_symbol"][symbol][timeframe] = dict(types)
                    for signal_type, count in types.items():
                        stats["by_timeframe"][timeframe] += count
            
            stats["by_timeframe"] = dict(stats["by_timeframe"])
            
            return stats
    
    def reset(self) -> None:
        """Reset all metrics."""
        with self.lock:
            self.signal_counts.clear()
            self.total_signals_by_type.clear()
            self.signal_timestamps.clear()
            self.hits = 0
            self.stops = 0
            self.pending = 0
            self.start_time = datetime.utcnow()
    
    @staticmethod
    def _format_uptime(uptime: timedelta) -> str:
        """Format uptime duration."""
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if seconds > 0 or not parts:
            parts.append(f"{seconds}s")
        
        return " ".join(parts)
