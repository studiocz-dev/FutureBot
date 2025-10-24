"""
Candle aggregator module.

Aggregates tick data into candles, resamples timeframes, and persists to Supabase.
Triggers callbacks on candle close events.
"""

import asyncio
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from collections import defaultdict

from ..bot.logger import get_logger

logger = get_logger(__name__)


class CandleAggregator:
    """
    Aggregates and manages candlestick data.
    
    Features:
    - Receives real-time candle updates from WebSocket
    - Maintains rolling window of recent candles in memory
    - Persists candles to Supabase
    - Triggers callbacks on candle close
    """
    
    def __init__(
        self,
        supabase: Any,  # SupabaseClient
        symbols: List[str],
        timeframes: List[str],
        window_size: int = 500,
    ):
        """
        Initialize candle aggregator.
        
        Args:
            supabase: Supabase client instance
            symbols: List of trading symbols
            timeframes: List of timeframes
            window_size: Number of candles to keep in memory per symbol/timeframe
        """
        self.supabase = supabase
        self.symbols = symbols
        self.timeframes = timeframes
        self.window_size = window_size
        
        # In-memory candle storage: {(symbol, timeframe): [candles]}
        self.candles: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
        
        # Last seen candle open_time to detect closes: {(symbol, timeframe): open_time}
        self.last_open_time: Dict[tuple, int] = {}
        
        # Callbacks to trigger on candle close
        self.close_callbacks: List[Callable] = []
        
        # Lock for thread-safe operations
        self.lock = asyncio.Lock()
    
    def on_candle_close(self, callback: Callable) -> None:
        """
        Register a callback to be called when a candle closes.
        
        Args:
            callback: Async function with signature (symbol, timeframe, candle) -> None
        """
        self.close_callbacks.append(callback)
        logger.info(f"Registered candle close callback: {callback.__name__}")
    
    async def process_candle(self, candle: Dict[str, Any]) -> None:
        """
        Process an incoming candle update.
        
        Args:
            candle: Candle data from WebSocket
        """
        symbol = candle["symbol"]
        timeframe = candle["timeframe"]
        open_time = candle["open_time"]
        is_closed = candle.get("is_closed", False)
        
        key = (symbol, timeframe)
        
        async with self.lock:
            # Check if this is a new candle (different open_time)
            last_time = self.last_open_time.get(key)
            
            if last_time is not None and last_time != open_time:
                # Previous candle has closed
                # Find the closed candle
                candles = self.candles[key]
                if candles and candles[-1]["open_time"] == last_time:
                    closed_candle = candles[-1]
                    logger.debug(
                        f"Candle closed: {symbol} {timeframe} @ {last_time}",
                        extra={"symbol": symbol, "timeframe": timeframe}
                    )
                    
                    # Trigger callbacks
                    await self._trigger_close_callbacks(symbol, timeframe, closed_candle)
            
            # Update or append candle
            candles = self.candles[key]
            
            # Check if we need to update existing candle or append new one
            if candles and candles[-1]["open_time"] == open_time:
                # Update existing candle
                candles[-1] = candle
            else:
                # New candle
                candles.append(candle)
                
                # Trim to window size
                if len(candles) > self.window_size:
                    candles.pop(0)
            
            # Update last seen open time
            self.last_open_time[key] = open_time
            
            # Persist to database (async, don't wait)
            if is_closed:
                asyncio.create_task(self._persist_candle(symbol, timeframe, candle))
    
    async def _trigger_close_callbacks(
        self,
        symbol: str,
        timeframe: str,
        candle: Dict[str, Any]
    ) -> None:
        """
        Trigger all registered callbacks for candle close IN PARALLEL.
        
        This allows all symbols to be analyzed simultaneously when their
        candles close, ensuring fair signal distribution across all symbols.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            candle: Closed candle data
        """
        if not self.close_callbacks:
            return
        
        # Create tasks for all callbacks to run in parallel
        tasks = []
        for callback in self.close_callbacks:
            task = asyncio.create_task(
                self._safe_callback_wrapper(callback, symbol, timeframe, candle)
            )
            tasks.append(task)
        
        # Execute all callbacks in parallel
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _safe_callback_wrapper(
        self,
        callback: Callable,
        symbol: str,
        timeframe: str,
        candle: Dict[str, Any]
    ) -> None:
        """
        Wrapper that safely executes a callback with error handling.
        
        Args:
            callback: Callback function to execute
            symbol: Trading symbol
            timeframe: Timeframe
            candle: Closed candle data
        """
        try:
            await callback(symbol, timeframe, candle)
        except Exception as e:
            logger.error(
                f"Error in candle close callback {callback.__name__}: {e}",
                exc_info=True
            )
    
    async def _persist_candle(
        self,
        symbol: str,
        timeframe: str,
        candle: Dict[str, Any]
    ) -> None:
        """
        Persist a closed candle to Supabase.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            candle: Candle data
        """
        try:
            await self.supabase.insert_candle(
                symbol=symbol,
                timeframe=timeframe,
                candle=candle,
            )
            logger.debug(f"Persisted candle: {symbol} {timeframe} @ {candle['open_time']}")
        
        except Exception as e:
            logger.error(f"Error persisting candle: {e}", exc_info=True)
    
    async def process_historical_candles(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict[str, Any]]
    ) -> None:
        """
        Process and store historical candles.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            candles: List of historical candles
        """
        if not candles:
            return
        
        logger.info(f"Processing {len(candles)} historical candles for {symbol} {timeframe}")
        
        key = (symbol, timeframe)
        
        async with self.lock:
            # Add to in-memory storage
            self.candles[key] = candles[-self.window_size:]
            
            # Update last open time
            if candles:
                self.last_open_time[key] = candles[-1]["open_time"]
        
        # Bulk insert to database
        try:
            await self.supabase.bulk_insert_candles(
                symbol=symbol,
                timeframe=timeframe,
                candles=candles,
            )
            logger.info(f"Stored {len(candles)} historical candles for {symbol} {timeframe}")
        
        except Exception as e:
            logger.error(f"Error storing historical candles: {e}", exc_info=True)
    
    def get_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent candles from in-memory storage.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            limit: Optional limit on number of candles
        
        Returns:
            List of candles (most recent last)
        """
        key = (symbol, timeframe)
        candles = self.candles.get(key, [])
        
        if limit:
            return candles[-limit:]
        return candles.copy()
    
    def get_latest_candle(
        self,
        symbol: str,
        timeframe: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the most recent candle.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
        
        Returns:
            Latest candle or None
        """
        candles = self.get_candles(symbol, timeframe)
        return candles[-1] if candles else None
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get aggregator statistics.
        
        Returns:
            Statistics dictionary
        """
        stats = {
            "total_symbols": len(self.symbols),
            "total_timeframes": len(self.timeframes),
            "candles_in_memory": sum(len(candles) for candles in self.candles.values()),
            "streams": {},
        }
        
        for (symbol, timeframe), candles in self.candles.items():
            stats["streams"][f"{symbol}_{timeframe}"] = {
                "count": len(candles),
                "latest_time": candles[-1]["open_time"] if candles else None,
            }
        
        return stats
