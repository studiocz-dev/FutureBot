"""
Supabase client wrapper.

Provides database operations and Realtime event publishing/subscription.
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime

from supabase import create_client, Client
from postgrest import APIResponse

from ..bot.logger import get_logger

logger = get_logger(__name__)


class SupabaseClient:
    """Wrapper around Supabase client for database operations."""
    
    def __init__(self, url: str, key: str):
        """
        Initialize Supabase client.
        
        Args:
            url: Supabase project URL
            key: Supabase API key (service_role or anon)
        """
        self.url = url
        self.key = key
        self.client: Optional[Client] = None
        
        # Cache symbol ID mappings
        self._symbol_cache: Dict[str, str] = {}
    
    async def initialize(self) -> None:
        """Initialize the Supabase client."""
        try:
            self.client = create_client(self.url, self.key)
            logger.info("Supabase client initialized")
            
            # Load symbol cache
            await self._load_symbol_cache()
        
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise
    
    async def _load_symbol_cache(self) -> None:
        """Load symbol IDs into cache."""
        try:
            response = self.client.table("symbols").select("id, symbol").execute()
            
            for row in response.data:
                self._symbol_cache[row["symbol"]] = row["id"]
            
            logger.info(f"Loaded {len(self._symbol_cache)} symbols into cache")
        
        except Exception as e:
            logger.error(f"Error loading symbol cache: {e}")
    
    async def get_symbol_id(self, symbol: str) -> Optional[str]:
        """
        Get symbol ID from cache or database.
        
        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
        
        Returns:
            Symbol UUID or None if not found
        """
        # Check cache first
        if symbol in self._symbol_cache:
            return self._symbol_cache[symbol]
        
        # Query database
        try:
            response = self.client.table("symbols").select("id").eq("symbol", symbol).limit(1).execute()
            
            if response.data:
                symbol_id = response.data[0]["id"]
                self._symbol_cache[symbol] = symbol_id
                return symbol_id
            
            # Symbol not found, create it
            return await self.create_symbol(symbol)
        
        except Exception as e:
            logger.error(f"Error getting symbol ID for {symbol}: {e}")
            return None
    
    async def create_symbol(
        self,
        symbol: str,
        exchange: str = "BINANCE_FUTURES",
        quote_asset: str = "USDT"
    ) -> str:
        """
        Create a new symbol record.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange name
            quote_asset: Quote asset
        
        Returns:
            Symbol UUID
        """
        try:
            response = self.client.table("symbols").insert({
                "symbol": symbol,
                "exchange": exchange,
                "quote_asset": quote_asset,
                "active": True,
            }).execute()
            
            symbol_id = response.data[0]["id"]
            self._symbol_cache[symbol] = symbol_id
            
            logger.info(f"Created symbol: {symbol} (ID: {symbol_id})")
            return symbol_id
        
        except Exception as e:
            logger.error(f"Error creating symbol {symbol}: {e}")
            raise
    
    async def insert_candle(
        self,
        symbol: str,
        timeframe: str,
        candle: Dict[str, Any]
    ) -> None:
        """
        Insert a single candle into the database.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            candle: Candle data
        """
        symbol_id = await self.get_symbol_id(symbol)
        if not symbol_id:
            logger.error(f"Cannot insert candle: symbol {symbol} not found")
            return
        
        try:
            self.client.table("candles").insert({
                "symbol_id": symbol_id,
                "timeframe": timeframe,
                "open_time": candle["open_time"],
                "close_time": candle.get("close_time", candle["open_time"] + 60000),
                "open": float(candle["open"]),
                "high": float(candle["high"]),
                "low": float(candle["low"]),
                "close": float(candle["close"]),
                "volume": float(candle["volume"]),
                "quote_volume": float(candle.get("quote_volume", 0)),
                "trades": candle.get("trades"),
                "taker_buy_base": float(candle.get("taker_buy_base", 0)),
                "taker_buy_quote": float(candle.get("taker_buy_quote", 0)),
                "json_raw": candle,
            }).execute()
        
        except Exception as e:
            # Ignore duplicate key errors (candle already exists)
            if "duplicate key" not in str(e).lower():
                logger.error(f"Error inserting candle: {e}")
    
    async def bulk_insert_candles(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict[str, Any]]
    ) -> None:
        """
        Bulk insert candles into the database.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            candles: List of candle data
        """
        symbol_id = await self.get_symbol_id(symbol)
        if not symbol_id:
            logger.error(f"Cannot insert candles: symbol {symbol} not found")
            return
        
        try:
            rows = []
            for candle in candles:
                rows.append({
                    "symbol_id": symbol_id,
                    "timeframe": timeframe,
                    "open_time": candle["open_time"],
                    "close_time": candle.get("close_time", candle["open_time"] + 60000),
                    "open": float(candle["open"]),
                    "high": float(candle["high"]),
                    "low": float(candle["low"]),
                    "close": float(candle["close"]),
                    "volume": float(candle["volume"]),
                    "quote_volume": float(candle.get("quote_volume", 0)),
                    "trades": candle.get("trades"),
                    "taker_buy_base": float(candle.get("taker_buy_base", 0)),
                    "taker_buy_quote": float(candle.get("taker_buy_quote", 0)),
                    "json_raw": candle,
                })
            
            # Supabase has a limit on bulk inserts, so chunk them
            chunk_size = 100
            for i in range(0, len(rows), chunk_size):
                chunk = rows[i:i + chunk_size]
                self.client.table("candles").insert(chunk).execute()
            
            logger.info(f"Bulk inserted {len(rows)} candles for {symbol} {timeframe}")
        
        except Exception as e:
            logger.error(f"Error bulk inserting candles: {e}")
    
    async def get_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 500,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve candles from the database.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            limit: Maximum number of candles
            start_time: Start time in milliseconds
            end_time: End time in milliseconds
        
        Returns:
            List of candles
        """
        symbol_id = await self.get_symbol_id(symbol)
        if not symbol_id:
            return []
        
        try:
            query = self.client.table("candles") \
                .select("*") \
                .eq("symbol_id", symbol_id) \
                .eq("timeframe", timeframe)
            
            if start_time:
                query = query.gte("open_time", start_time)
            if end_time:
                query = query.lte("open_time", end_time)
            
            query = query.order("open_time", desc=False).limit(limit)
            
            response = query.execute()
            return response.data
        
        except Exception as e:
            logger.error(f"Error retrieving candles: {e}")
            return []
    
    async def insert_signal(self, signal: Dict[str, Any]) -> Optional[str]:
        """
        Insert a trading signal into the database.
        
        Args:
            signal: Signal data
        
        Returns:
            Signal ID or None on error
        """
        symbol_id = await self.get_symbol_id(signal["symbol"])
        if not symbol_id:
            logger.error(f"Cannot insert signal: symbol {signal['symbol']} not found")
            return None
        
        try:
            response = self.client.table("signals").insert({
                "symbol_id": symbol_id,
                "timeframe": signal["timeframe"],
                "signal_type": signal["type"],
                "entry_price": float(signal["entry_price"]),
                "stop_loss": float(signal.get("stop_loss", 0)),
                "take_profit": float(signal.get("take_profit", 0)),
                "take_profit_2": float(signal.get("take_profit_2", 0)) if signal.get("take_profit_2") else None,
                "take_profit_3": float(signal.get("take_profit_3", 0)) if signal.get("take_profit_3") else None,
                "confidence": float(signal["confidence"]),
                "wyckoff_phase": signal.get("wyckoff_phase"),
                "elliott_wave_count": signal.get("elliott_wave_count"),
                "indicators": signal.get("indicators", {}),
                "rationale": signal.get("rationale"),
                "payload_json": signal,
            }).execute()
            
            signal_id = response.data[0]["id"]
            logger.info(f"Inserted signal: {signal_id} - {signal['type']} {signal['symbol']}")
            
            # Publish Realtime event
            await self.publish_signal_event(signal_id, signal)
            
            return signal_id
        
        except Exception as e:
            logger.error(f"Error inserting signal: {e}")
            return None
    
    async def publish_signal_event(self, signal_id: str, signal: Dict[str, Any]) -> None:
        """
        Publish a signal event via Supabase Realtime.
        
        Args:
            signal_id: Signal ID
            signal: Signal data
        """
        try:
            # Realtime events are automatically published when inserting into subscribed tables
            # This method is a placeholder for additional custom event publishing
            logger.debug(f"Signal event published: {signal_id}")
        except Exception as e:
            logger.error(f"Error publishing signal event: {e}")
    
    async def get_recent_signals(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent signals.
        
        Args:
            symbol: Optional symbol filter
            timeframe: Optional timeframe filter
            limit: Maximum number of signals
        
        Returns:
            List of signals
        """
        try:
            query = self.client.table("v_recent_signals").select("*")
            
            if symbol:
                query = query.eq("symbol", symbol)
            if timeframe:
                query = query.eq("timeframe", timeframe)
            
            query = query.order("created_at", desc=True).limit(limit)
            
            response = query.execute()
            return response.data
        
        except Exception as e:
            logger.error(f"Error retrieving recent signals: {e}")
            return []
    
    async def update_signal_status(
        self,
        signal_id: str,
        status: str,
        discord_message_id: Optional[str] = None
    ) -> None:
        """
        Update signal status.
        
        Args:
            signal_id: Signal ID
            status: New status
            discord_message_id: Optional Discord message ID
        """
        try:
            update_data = {"status": status}
            if discord_message_id:
                update_data["discord_message_id"] = discord_message_id
            
            self.client.table("signals").update(update_data).eq("id", signal_id).execute()
            logger.info(f"Updated signal {signal_id} status to {status}")
        
        except Exception as e:
            logger.error(f"Error updating signal status: {e}")
    
    async def close(self) -> None:
        """Close the Supabase client."""
        # Supabase Python client doesn't require explicit closing
        logger.info("Supabase client closed")
