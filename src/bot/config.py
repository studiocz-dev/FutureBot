"""
Configuration module for the Wyckoff-Elliott Discord bot.

Loads environment variables and provides configuration objects for all modules.
"""

import os
from typing import List, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

# Load environment variables
load_dotenv()


class SupabaseConfig(BaseModel):
    """Supabase database configuration."""
    
    url: str = Field(..., description="Supabase project URL")
    service_key: Optional[str] = Field(None, description="Service role key for admin operations")
    anon_key: Optional[str] = Field(None, description="Anonymous key for client operations")
    
    @classmethod
    def from_env(cls) -> "SupabaseConfig":
        """Load Supabase config from environment variables."""
        return cls(
            url=os.getenv("SUPABASE_URL", ""),
            service_key=os.getenv("SUPABASE_SERVICE_KEY"),
            anon_key=os.getenv("SUPABASE_ANON_KEY"),
        )
    
    @property
    def key(self) -> str:
        """Return the appropriate key (service key preferred)."""
        return self.service_key or self.anon_key or ""


class DiscordConfig(BaseModel):
    """Discord bot configuration."""
    
    token: str = Field(..., description="Discord bot token")
    guild_id: Optional[int] = Field(None, description="Guild ID for slash commands")
    signals_channel_id: Optional[int] = Field(None, description="Channel ID for signal alerts")
    
    @classmethod
    def from_env(cls) -> "DiscordConfig":
        """Load Discord config from environment variables."""
        guild_id_str = os.getenv("DISCORD_GUILD_ID")
        signals_channel_id_str = os.getenv("DISCORD_SIGNALS_CHANNEL_ID")
        
        return cls(
            token=os.getenv("DISCORD_TOKEN", ""),
            guild_id=int(guild_id_str) if guild_id_str else None,
            signals_channel_id=int(signals_channel_id_str) if signals_channel_id_str else None,
        )


class BinanceConfig(BaseModel):
    """Binance API configuration."""
    
    base_url: str = Field(default="https://fapi.binance.com", description="Binance Futures base URL")
    ws_url: str = Field(default="wss://fstream.binance.com", description="Binance WebSocket URL")
    api_key: Optional[str] = Field(None, description="API key for authenticated endpoints")
    api_secret: Optional[str] = Field(None, description="API secret for authenticated endpoints")
    testnet: bool = Field(default=True, description="Use testnet for trading")
    rate_limit_per_minute: int = Field(default=1200, description="API rate limit")
    max_candles_per_request: int = Field(default=1500, description="Max candles per REST request")
    
    @classmethod
    def from_env(cls) -> "BinanceConfig":
        """Load Binance config from environment variables."""
        return cls(
            base_url=os.getenv("BINANCE_BASE_URL", "https://fapi.binance.com"),
            ws_url=os.getenv("BINANCE_WS_URL", "wss://fstream.binance.com"),
            api_key=os.getenv("BINANCE_API_KEY"),
            api_secret=os.getenv("BINANCE_API_SECRET"),
            testnet=os.getenv("BINANCE_TESTNET", "true").lower() == "true",
            rate_limit_per_minute=int(os.getenv("BINANCE_RATE_LIMIT_PER_MINUTE", "1200")),
            max_candles_per_request=int(os.getenv("MAX_CANDLES_PER_REQUEST", "1500")),
        )


class TradingConfig(BaseModel):
    """Trading module configuration."""
    
    enabled: bool = Field(default=False, description="Enable trading (DANGEROUS - default disabled)")
    
    @classmethod
    def from_env(cls) -> "TradingConfig":
        """Load trading config from environment variables."""
        return cls(
            enabled=os.getenv("ENABLE_TRADING", "false").lower() == "true",
        )
    
    def validate_enabled(self) -> None:
        """Validate that trading can be safely enabled."""
        if self.enabled:
            if not os.getenv("BINANCE_API_KEY") or not os.getenv("BINANCE_API_SECRET"):
                raise ValueError(
                    "Trading is enabled but BINANCE_API_KEY and BINANCE_API_SECRET are not set. "
                    "Disable trading or provide valid credentials."
                )


class SignalConfig(BaseModel):
    """Signal generation configuration."""
    
    symbols: List[str] = Field(default_factory=lambda: ["BTCUSDT"], description="Trading symbols")
    timeframes: List[str] = Field(default_factory=lambda: ["15m", "1h", "4h"], description="Timeframes")
    min_confidence: float = Field(default=0.65, description="Minimum confidence to trigger signal")
    enable_wyckoff: bool = Field(default=True, description="Enable Wyckoff analysis")
    enable_elliott: bool = Field(default=True, description="Enable Elliott Wave analysis")
    signal_cooldown: int = Field(default=300, description="Cooldown period in seconds")
    
    @field_validator("min_confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Validate confidence is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("min_confidence must be between 0.0 and 1.0")
        return v
    
    @classmethod
    def from_env(cls) -> "SignalConfig":
        """Load signal config from environment variables."""
        symbols_str = os.getenv("SYMBOLS", "BTCUSDT,ETHUSDT,BNBUSDT")
        timeframes_str = os.getenv("TIMEFRAMES", "15m,1h,4h")
        
        return cls(
            symbols=[s.strip() for s in symbols_str.split(",") if s.strip()],
            timeframes=[t.strip() for t in timeframes_str.split(",") if t.strip()],
            min_confidence=float(os.getenv("MIN_CONFIDENCE", "0.65")),
            enable_wyckoff=os.getenv("ENABLE_WYCKOFF", "true").lower() == "true",
            enable_elliott=os.getenv("ENABLE_ELLIOTT", "true").lower() == "true",
            signal_cooldown=int(os.getenv("SIGNAL_COOLDOWN", "300")),
        )


class CacheConfig(BaseModel):
    """Cache configuration."""
    
    redis_url: Optional[str] = Field(None, description="Redis connection URL")
    
    @classmethod
    def from_env(cls) -> "CacheConfig":
        """Load cache config from environment variables."""
        return cls(
            redis_url=os.getenv("REDIS_URL"),
        )
    
    @property
    def use_redis(self) -> bool:
        """Check if Redis should be used."""
        return bool(self.redis_url)


class LogConfig(BaseModel):
    """Logging configuration."""
    
    level: str = Field(default="INFO", description="Log level")
    format: str = Field(default="json", description="Log format: json or text")
    
    @classmethod
    def from_env(cls) -> "LogConfig":
        """Load log config from environment variables."""
        return cls(
            level=os.getenv("LOG_LEVEL", "INFO").upper(),
            format=os.getenv("LOG_FORMAT", "json").lower(),
        )


class WebSocketConfig(BaseModel):
    """WebSocket configuration."""
    
    reconnect_delay: int = Field(default=5, description="Reconnection delay in seconds")
    max_retries: int = Field(default=10, description="Maximum reconnection attempts")
    
    @classmethod
    def from_env(cls) -> "WebSocketConfig":
        """Load WebSocket config from environment variables."""
        return cls(
            reconnect_delay=int(os.getenv("WS_RECONNECT_DELAY", "5")),
            max_retries=int(os.getenv("WS_MAX_RETRIES", "10")),
        )


class BacktestConfig(BaseModel):
    """Backtesting configuration."""
    
    start_date: str = Field(default="2024-01-01", description="Backtest start date")
    end_date: str = Field(default="2024-12-31", description="Backtest end date")
    initial_balance: float = Field(default=10000.0, description="Initial balance for backtesting")
    
    @classmethod
    def from_env(cls) -> "BacktestConfig":
        """Load backtest config from environment variables."""
        return cls(
            start_date=os.getenv("BACKTEST_START_DATE", "2024-01-01"),
            end_date=os.getenv("BACKTEST_END_DATE", "2024-12-31"),
            initial_balance=float(os.getenv("BACKTEST_INITIAL_BALANCE", "10000")),
        )


class Config:
    """Main configuration container."""
    
    def __init__(self):
        """Initialize all configuration sections."""
        self.supabase = SupabaseConfig.from_env()
        self.discord = DiscordConfig.from_env()
        self.binance = BinanceConfig.from_env()
        self.trading = TradingConfig.from_env()
        self.signals = SignalConfig.from_env()
        self.cache = CacheConfig.from_env()
        self.log = LogConfig.from_env()
        self.websocket = WebSocketConfig.from_env()
        self.backtest = BacktestConfig.from_env()
    
    def validate(self) -> None:
        """Validate configuration."""
        errors = []
        
        if not self.supabase.url:
            errors.append("SUPABASE_URL is required")
        
        if not self.supabase.key:
            errors.append("SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY is required")
        
        if not self.discord.token:
            errors.append("DISCORD_TOKEN is required")
        
        # Validate trading config
        try:
            self.trading.validate_enabled()
        except ValueError as e:
            errors.append(str(e))
        
        if errors:
            raise ValueError(f"Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))
    
    def __repr__(self) -> str:
        """String representation (safe for logging)."""
        return (
            f"Config(\n"
            f"  supabase_url={self.supabase.url},\n"
            f"  discord_configured={bool(self.discord.token)},\n"
            f"  symbols={self.signals.symbols},\n"
            f"  timeframes={self.signals.timeframes},\n"
            f"  trading_enabled={self.trading.enabled},\n"
            f"  redis_enabled={self.cache.use_redis}\n"
            f")"
        )


# Global config instance
config = Config()
