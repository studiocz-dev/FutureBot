"""
Binance WebSocket client for real-time market data.

Connects to public WebSocket streams (no API key required).
Implements automatic reconnection with exponential backoff.
"""

import asyncio
import json
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime

import websockets
from websockets.client import WebSocketClientProtocol

from ..bot.logger import get_logger

logger = get_logger(__name__)


class BinanceWebSocketManager:
    """
    Manager for Binance WebSocket connections.
    
    Handles multiple symbol/timeframe streams with automatic reconnection.
    """
    
    def __init__(
        self,
        ws_url: str,
        symbols: List[str],
        timeframes: List[str],
        candle_aggregator: Any,  # CandleAggregator
        reconnect_delay: int = 5,
        max_retries: int = 10,
    ):
        """
        Initialize WebSocket manager.
        
        Args:
            ws_url: WebSocket base URL
            symbols: List of trading symbols
            timeframes: List of timeframes to subscribe
            candle_aggregator: Candle aggregator instance
            reconnect_delay: Initial reconnection delay in seconds
            max_retries: Maximum reconnection attempts (-1 for infinite)
        """
        self.ws_url = ws_url.rstrip("/")
        self.symbols = [s.lower() for s in symbols]
        self.timeframes = self._normalize_timeframes(timeframes)
        self.candle_aggregator = candle_aggregator
        self.reconnect_delay = reconnect_delay
        self.max_retries = max_retries
        
        self.connections: Dict[str, WebSocketClientProtocol] = {}
        self.running = False
        self.tasks: List[asyncio.Task] = []
    
    def _normalize_timeframes(self, timeframes: List[str]) -> List[str]:
        """
        Normalize timeframe strings to Binance WebSocket format.
        
        Args:
            timeframes: List of timeframe strings
        
        Returns:
            Normalized timeframes
        """
        return [tf.lower() for tf in timeframes]
    
    def _build_stream_name(self, symbol: str, timeframe: str) -> str:
        """
        Build WebSocket stream name.
        
        Args:
            symbol: Trading symbol (lowercase)
            timeframe: Timeframe (lowercase)
        
        Returns:
            Stream name (e.g., btcusdt@kline_1m)
        """
        return f"{symbol}@kline_{timeframe}"
    
    def _build_ws_url(self, streams: List[str]) -> str:
        """
        Build combined WebSocket URL for multiple streams.
        
        Args:
            streams: List of stream names
        
        Returns:
            WebSocket URL
        """
        stream_path = "/".join(streams)
        return f"{self.ws_url}/stream?streams={stream_path}"
    
    async def _handle_kline_message(self, data: Dict[str, Any]) -> None:
        """
        Handle incoming kline/candle message.
        
        Args:
            data: WebSocket message data
        """
        try:
            if "stream" not in data or "data" not in data:
                return
            
            stream = data["stream"]
            kline_data = data["data"]
            
            # Extract symbol and timeframe from stream name
            # Format: btcusdt@kline_1m
            parts = stream.split("@")
            if len(parts) != 2:
                return
            
            symbol = parts[0].upper()
            timeframe_part = parts[1].replace("kline_", "")
            
            # Parse kline
            k = kline_data.get("k", {})
            if not k:
                return
            
            candle = {
                "symbol": symbol,
                "timeframe": timeframe_part,
                "open_time": k["t"],
                "close_time": k["T"],
                "open": float(k["o"]),
                "high": float(k["h"]),
                "low": float(k["l"]),
                "close": float(k["c"]),
                "volume": float(k["v"]),
                "quote_volume": float(k["q"]),
                "trades": k["n"],
                "is_closed": k["x"],
            }
            
            # Pass to aggregator
            await self.candle_aggregator.process_candle(candle)
            
        except Exception as e:
            logger.error(f"Error handling kline message: {e}", exc_info=True)
    
    async def _listen(self, ws: WebSocketClientProtocol, stream_id: str) -> None:
        """
        Listen for messages on a WebSocket connection.
        
        Args:
            ws: WebSocket connection
            stream_id: Stream identifier for logging
        """
        logger.info(f"Started listening on stream: {stream_id}")
        
        try:
            async for message in ws:
                if isinstance(message, str):
                    data = json.loads(message)
                    await self._handle_kline_message(data)
                elif isinstance(message, bytes):
                    data = json.loads(message.decode("utf-8"))
                    await self._handle_kline_message(data)
        
        except websockets.ConnectionClosed as e:
            logger.warning(f"WebSocket connection closed: {stream_id} - {e}")
        except Exception as e:
            logger.error(f"Error in WebSocket listener: {stream_id} - {e}", exc_info=True)
    
    async def _connect_with_retry(self, stream_id: str, url: str) -> None:
        """
        Connect to WebSocket with automatic retry.
        
        Args:
            stream_id: Stream identifier
            url: WebSocket URL
        """
        retry_count = 0
        current_delay = self.reconnect_delay
        
        while self.running and (self.max_retries < 0 or retry_count < self.max_retries):
            try:
                logger.info(f"Connecting to WebSocket: {stream_id}")
                
                async with websockets.connect(
                    url,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=10,
                ) as ws:
                    self.connections[stream_id] = ws
                    retry_count = 0  # Reset on successful connection
                    current_delay = self.reconnect_delay
                    
                    await self._listen(ws, stream_id)
            
            except Exception as e:
                retry_count += 1
                logger.error(
                    f"WebSocket connection failed: {stream_id} (attempt {retry_count}/{self.max_retries}) - {e}"
                )
                
                if self.running and (self.max_retries < 0 or retry_count < self.max_retries):
                    logger.info(f"Reconnecting in {current_delay}s...")
                    await asyncio.sleep(current_delay)
                    current_delay = min(current_delay * 2, 60)  # Exponential backoff, max 60s
                else:
                    logger.error(f"Max retries reached for {stream_id}, giving up")
                    break
        
        # Cleanup
        if stream_id in self.connections:
            del self.connections[stream_id]
    
    async def start(self) -> None:
        """Start all WebSocket connections."""
        if self.running:
            logger.warning("WebSocket manager is already running")
            return
        
        self.running = True
        logger.info("Starting WebSocket manager...")
        
        # Create stream combinations
        streams = []
        for symbol in self.symbols:
            for timeframe in self.timeframes:
                streams.append(self._build_stream_name(symbol, timeframe))
        
        if not streams:
            logger.warning("No streams configured")
            return
        
        # Binance allows up to 200 streams per connection, but we'll group reasonably
        # For simplicity, we'll create one combined stream
        stream_id = "combined_stream"
        url = self._build_ws_url(streams)
        
        logger.info(f"Subscribing to {len(streams)} streams: {streams}")
        
        # Start connection task
        task = asyncio.create_task(self._connect_with_retry(stream_id, url))
        self.tasks.append(task)
        
        logger.info("WebSocket manager started")
    
    def stop(self) -> None:
        """Stop all WebSocket connections."""
        logger.info("Stopping WebSocket manager...")
        self.running = False
        
        # Close all connections
        for stream_id, ws in self.connections.items():
            logger.info(f"Closing WebSocket: {stream_id}")
            asyncio.create_task(ws.close())
        
        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        self.connections.clear()
        self.tasks.clear()
        logger.info("WebSocket manager stopped")
    
    def is_connected(self) -> bool:
        """Check if any WebSocket connection is active."""
        return bool(self.connections)
    
    def get_connection_status(self) -> Dict[str, bool]:
        """
        Get connection status for all streams.
        
        Returns:
            Dictionary of stream_id -> connected status
        """
        return {
            stream_id: not ws.closed
            for stream_id, ws in self.connections.items()
        }
