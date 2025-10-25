"""
Binance REST API client for historical data.

Uses public endpoints (no API key required).
Implements rate limiting and retry logic.
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone

import aiohttp
from ..bot.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, requests_per_minute: int):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests per minute
        """
        self.requests_per_minute = requests_per_minute
        self.tokens = requests_per_minute
        self.max_tokens = requests_per_minute
        self.last_update = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """Wait until a request can be made."""
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            
            # Refill tokens based on time elapsed
            self.tokens = min(
                self.max_tokens,
                self.tokens + elapsed * (self.requests_per_minute / 60.0)
            )
            self.last_update = now
            
            # Wait if no tokens available
            if self.tokens < 1.0:
                wait_time = (1.0 - self.tokens) / (self.requests_per_minute / 60.0)
                logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                self.tokens = 1.0
                self.last_update = time.time()
            
            self.tokens -= 1.0


class BinanceRESTClient:
    """Client for Binance Futures public REST API."""
    
    def __init__(
        self,
        base_url: str = "https://fapi.binance.com",
        rate_limit: int = 1200,
        timeout: int = 30,
    ):
        """
        Initialize Binance REST client.
        
        Args:
            base_url: Binance API base URL
            rate_limit: Maximum requests per minute
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.rate_limiter = RateLimiter(rate_limit)
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure aiohttp session is created."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self.session
    
    async def close(self) -> None:
        """Close the HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        retries: int = 3,
    ) -> Any:
        """
        Make an HTTP request with rate limiting and retries.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            retries: Number of retry attempts
        
        Returns:
            Response data
        """
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(retries):
            try:
                await self.rate_limiter.acquire()
                session = await self._ensure_session()
                
                async with session.request(method, url, params=params) as response:
                    if response.status == 429:  # Rate limit exceeded
                        retry_after = int(response.headers.get("Retry-After", "60"))
                        logger.warning(f"Rate limit exceeded, waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue
                    
                    response.raise_for_status()
                    return await response.json()
            
            except aiohttp.ClientError as e:
                if attempt < retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Request failed (attempt {attempt + 1}/{retries}): {e}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Request failed after {retries} attempts: {e}")
                    raise
        
        raise RuntimeError(f"Failed to complete request after {retries} attempts")
    
    async def get_exchange_info(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Get exchange trading rules and symbol information.
        
        Args:
            symbol: Optional symbol filter
        
        Returns:
            Exchange info
        """
        params = {}
        if symbol:
            params["symbol"] = symbol
        
        return await self._request("GET", "/fapi/v1/exchangeInfo", params)
    
    async def get_klines(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 500,
    ) -> List[List[Any]]:
        """
        Get kline/candlestick data.
        
        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
            interval: Kline interval (e.g., 1m, 5m, 15m, 1h, 4h, 1d)
            start_time: Start time in milliseconds
            end_time: End time in milliseconds
            limit: Number of klines to retrieve (max 1500)
        
        Returns:
            List of klines, each as [open_time, open, high, low, close, volume, ...]
        """
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": min(limit, 1500),
        }
        
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        
        logger.debug(f"Fetching klines for {symbol} {interval} (limit={limit})")
        return await self._request("GET", "/fapi/v1/klines", params)
    
    async def get_historical_klines(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """
        Get historical kline data with parsed fields.
        Handles large requests by making multiple API calls if limit > 1500.
        
        Args:
            symbol: Trading symbol
            interval: Kline interval
            start_time: Start datetime
            end_time: End datetime
            limit: Number of candles to retrieve (can exceed 1500)
        
        Returns:
            List of parsed candle dictionaries
        """
        MAX_PER_REQUEST = 1500
        all_candles = []
        
        # If limit <= 1500, single request
        if limit <= MAX_PER_REQUEST:
            start_ms = int(start_time.timestamp() * 1000) if start_time else None
            end_ms = int(end_time.timestamp() * 1000) if end_time else None
            
            raw_klines = await self.get_klines(
                symbol=symbol,
                interval=interval,
                start_time=start_ms,
                end_time=end_ms,
                limit=limit,
            )
            all_candles = self._parse_klines(raw_klines)
        else:
            # Multiple requests needed - work backwards from end_time
            remaining = limit
            current_end_time = end_time
            
            while remaining > 0:
                batch_limit = min(remaining, MAX_PER_REQUEST)
                end_ms = int(current_end_time.timestamp() * 1000) if current_end_time else None
                
                raw_klines = await self.get_klines(
                    symbol=symbol,
                    interval=interval,
                    end_time=end_ms,
                    limit=batch_limit,
                )
                
                if not raw_klines:
                    break
                
                batch_candles = self._parse_klines(raw_klines)
                all_candles = batch_candles + all_candles  # Prepend older candles
                remaining -= len(batch_candles)
                
                # Update end_time to oldest candle in this batch minus 1ms
                if len(batch_candles) > 0:
                    oldest_time_ms = batch_candles[0]["open_time"]
                    current_end_time = datetime.fromtimestamp((oldest_time_ms - 1) / 1000, tz=timezone.utc)
                
                # If we got fewer candles than requested, we've reached the limit
                if len(batch_candles) < batch_limit:
                    break
        
        logger.info(f"Retrieved {len(all_candles)} candles for {symbol} {interval}")
        return all_candles
    
    def _parse_klines(self, raw_klines: List[List[Any]]) -> List[Dict[str, Any]]:
        """Parse raw kline data into structured format."""
        candles = []
        for kline in raw_klines:
            candles.append({
                "open_time": kline[0],
                "open": float(kline[1]),
                "high": float(kline[2]),
                "low": float(kline[3]),
                "close": float(kline[4]),
                "volume": float(kline[5]),
                "close_time": kline[6],
                "quote_volume": float(kline[7]),
                "trades": int(kline[8]),
                "taker_buy_base": float(kline[9]),
                "taker_buy_quote": float(kline[10]),
            })
        return candles
    
    async def get_ticker_price(self, symbol: Optional[str] = None) -> Any:
        """
        Get latest price for a symbol.
        
        Args:
            symbol: Trading symbol (if None, returns all symbols)
        
        Returns:
            Price data
        """
        params = {}
        if symbol:
            params["symbol"] = symbol
        
        return await self._request("GET", "/fapi/v1/ticker/price", params)
    
    async def get_24hr_ticker(self, symbol: Optional[str] = None) -> Any:
        """
        Get 24hr ticker price change statistics.
        
        Args:
            symbol: Trading symbol (if None, returns all symbols)
        
        Returns:
            Ticker data
        """
        params = {}
        if symbol:
            params["symbol"] = symbol
        
        return await self._request("GET", "/fapi/v1/ticker/24hr", params)
