"""
Main entrypoint for the Wyckoff-Elliott Discord trading signals bot.

This module orchestrates:
- Supabase connection
- Binance data ingestion (REST + WebSocket)
- Signal generation (Wyckoff + Elliott)
- Discord bot and notifications
"""

import asyncio
import signal
import sys
from typing import Optional

import discord
from discord.ext import commands

from .config import config
from .logger import get_logger
from ..storage.supabase_client import SupabaseClient
from ..ingest.binance_ws import BinanceWebSocketManager
from ..ingest.binance_rest import BinanceRESTClient
from ..ingest.candle_aggregator import CandleAggregator
from ..signals.fuse import SignalFuser
from ..discord.notifier import DiscordNotifier
from ..discord.commands import setup_commands
from ..utils.metrics import Metrics

logger = get_logger(__name__)


class TradingBot:
    """Main bot orchestrator."""
    
    def __init__(self):
        """Initialize bot components."""
        self.config = config
        self.running = False
        self.shutdown_event = asyncio.Event()
        
        # Components (initialized in setup)
        self.supabase: Optional[SupabaseClient] = None
        self.binance_rest: Optional[BinanceRESTClient] = None
        self.binance_ws: Optional[BinanceWebSocketManager] = None
        self.candle_aggregator: Optional[CandleAggregator] = None
        self.signal_fuser: Optional[SignalFuser] = None
        self.discord_bot: Optional[commands.Bot] = None
        self.discord_notifier: Optional[DiscordNotifier] = None
        self.metrics: Optional[Metrics] = None
    
    async def setup(self) -> None:
        """Initialize all components."""
        logger.info("Initializing bot components...")
        
        # Validate configuration
        try:
            self.config.validate()
        except ValueError as e:
            logger.error(f"Configuration validation failed: {e}")
            raise
        
        logger.info(f"Configuration: {self.config}")
        
        # Initialize metrics
        self.metrics = Metrics()
        
        # Initialize Supabase client
        logger.info("Connecting to Supabase...")
        self.supabase = SupabaseClient(
            url=self.config.supabase.url,
            key=self.config.supabase.key,
        )
        await self.supabase.initialize()
        logger.info("Supabase connected")
        
        # Initialize Binance REST client
        logger.info("Initializing Binance REST client...")
        self.binance_rest = BinanceRESTClient(
            base_url=self.config.binance.base_url,
            rate_limit=self.config.binance.rate_limit_per_minute,
        )
        
        # Initialize candle aggregator
        self.candle_aggregator = CandleAggregator(
            supabase=self.supabase,
            symbols=self.config.signals.symbols,
            timeframes=self.config.signals.timeframes,
        )
        
        # Initialize signal fuser
        self.signal_fuser = SignalFuser(
            supabase=self.supabase,
            min_confidence=self.config.signals.min_confidence,
            enable_wyckoff=self.config.signals.enable_wyckoff,
            enable_elliott=self.config.signals.enable_elliott,
            cooldown=self.config.signals.signal_cooldown,
            prevent_conflicts=self.config.signals.prevent_conflicts,
            analysis_candles=self.config.historical.analysis_candles,
            min_candles=self.config.historical.min_candles,
            atr_candles=self.config.historical.atr_candles,
        )
        
        # Initialize Discord bot
        logger.info("Initializing Discord bot...")
        intents = discord.Intents.default()
        intents.message_content = True  # Required for prefix commands
        
        self.discord_bot = commands.Bot(
            command_prefix=">",  # Command prefix: >signal BTC
            intents=intents,
            help_command=None,
        )
        
        # Initialize Discord notifier
        self.discord_notifier = DiscordNotifier(
            bot=self.discord_bot,
            channel_id=self.config.discord.signals_channel_id,
        )
        
        # Setup prefix commands
        setup_commands(
            bot=self.discord_bot,
            supabase=self.supabase,
            signal_fuser=self.signal_fuser,
            metrics=self.metrics,
        )
        
        # Register Discord event handlers
        @self.discord_bot.event
        async def on_ready():
            logger.info(f"Discord bot logged in as {self.discord_bot.user}")
            logger.info(f"Bot is ready! Use commands like: >signal BTC")
            logger.info(f"Registered {len(self.discord_bot.commands)} commands")
        
        @self.discord_bot.event
        async def on_command(ctx):
            """Log when a command is invoked."""
            logger.info(f"Command '{ctx.command}' invoked by {ctx.author} in {ctx.guild or 'DM'}")
        
        @self.discord_bot.event
        async def on_command_completion(ctx):
            """Log when a command completes successfully."""
            logger.info(f"Command '{ctx.command}' completed successfully for {ctx.author}")
        
        # Initialize Binance WebSocket manager
        logger.info("Initializing Binance WebSocket manager...")
        self.binance_ws = BinanceWebSocketManager(
            ws_url=self.config.binance.ws_url,
            symbols=self.config.signals.symbols,
            timeframes=self.config.signals.timeframes,
            candle_aggregator=self.candle_aggregator,
            reconnect_delay=self.config.websocket.reconnect_delay,
            max_retries=self.config.websocket.max_retries,
        )
        
        # Register signal callback
        self.candle_aggregator.on_candle_close(self._on_candle_close)
        
        logger.info("Bot components initialized successfully")
    
    async def _on_candle_close(self, symbol: str, timeframe: str, candle: dict) -> None:
        """
        Callback triggered when a candle closes.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            candle: Candle data
        """
        # Only log candle close in debug mode to reduce noise
        logger.debug(f"📊 Analyzing {symbol} {timeframe} | Close: ${candle.get('close')}")
        
        try:
            # Generate signal using fuser
            signal = await self.signal_fuser.generate_signal(symbol, timeframe, candle)
            
            if signal:
                logger.info(
                    f"🚀 SIGNAL: {signal['type']} {symbol} @ ${signal['entry_price']:.4f} | "
                    f"Confidence: {signal['confidence']*100:.1f}%",
                    extra={
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "signal_type": signal["type"],
                        "confidence": signal["confidence"],
                    }
                )
                
                # Send to Discord
                await self.discord_notifier.send_signal(signal)
                
                # Update metrics
                self.metrics.increment_signal(symbol, timeframe, signal["type"])
            
        except Exception as e:
            logger.error(f"Error processing candle close: {e}", exc_info=True)
    
    async def start(self) -> None:
        """Start the bot and all components."""
        if self.running:
            logger.warning("Bot is already running")
            return
        
        self.running = True
        logger.info("=" * 60)
        logger.info("🤖 STARTING FUTUREBOT")
        logger.info("=" * 60)
        
        try:
            # Start Discord bot in background
            logger.info("📱 Connecting to Discord...")
            discord_task = asyncio.create_task(
                self.discord_bot.start(self.config.discord.token)
            )
            
            # Give Discord time to connect, then wait for ready
            await asyncio.sleep(2)
            
            # Wait for Discord bot to be ready (with timeout)
            try:
                await asyncio.wait_for(self.discord_bot.wait_until_ready(), timeout=30.0)
                logger.info("✅ Discord bot connected")
            except asyncio.TimeoutError:
                logger.error("❌ Discord bot failed to connect within 30 seconds")
                raise
            
            # Download historical data if needed
            logger.info("📊 Loading historical candle data...")
            total_symbols = len(self.config.signals.symbols)
            for idx, symbol in enumerate(self.config.signals.symbols, 1):
                for timeframe in self.config.signals.timeframes:
                    try:
                        candles = await self.binance_rest.get_historical_klines(
                            symbol=symbol,
                            interval=timeframe,
                            limit=self.config.historical.startup_candles,
                        )
                        logger.info(f"  [{idx}/{total_symbols}] {symbol} {timeframe}: {len(candles)} candles loaded")
                        
                        # Store in database
                        await self.candle_aggregator.process_historical_candles(
                            symbol=symbol,
                            timeframe=timeframe,
                            candles=candles,
                        )
                    except Exception as e:
                        logger.error(f"  ❌ Error loading {symbol} {timeframe}: {e}")
            
            logger.info("✅ Historical data loaded successfully")
            
            # Start WebSocket connections
            stream_count = len(self.config.signals.symbols) * len(self.config.signals.timeframes)
            logger.info(f"🌐 Starting {stream_count} WebSocket streams...")
            ws_task = asyncio.create_task(self.binance_ws.start())
            
            logger.info("=" * 60)
            logger.info("🚀 BOT IS FULLY OPERATIONAL!")
            logger.info(f"📊 Monitoring: {len(self.config.signals.symbols)} symbols")
            logger.info(f"⏱️  Timeframe: {', '.join(self.config.signals.timeframes)}")
            logger.info(f"🎯 Min Confidence: {self.config.signals.min_confidence*100:.0f}%")
            logger.info("=" * 60)
            
            # Send startup notification to Discord
            await self.discord_notifier.send_startup_message(
                symbols=self.config.signals.symbols,
                timeframes=self.config.signals.timeframes,
            )
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
            # Cleanup
            logger.info("Shutting down...")
            self.binance_ws.stop()
            await ws_task
            await self.discord_bot.close()
            await discord_task
            
        except Exception as e:
            logger.error(f"Fatal error in bot: {e}", exc_info=True)
            raise
        finally:
            self.running = False
            logger.info("Bot stopped")
    
    def stop(self) -> None:
        """Signal the bot to stop."""
        logger.info("Stop signal received")
        self.shutdown_event.set()


async def main() -> None:
    """Main entry point."""
    logger.info("=" * 80)
    logger.info("Wyckoff-Elliott Discord Trading Signals Bot")
    logger.info("=" * 80)
    logger.info("⚠️  DISCLAIMER: This bot is for educational purposes only.")
    logger.info("⚠️  Not financial advice. Trade at your own risk.")
    logger.info("=" * 80)
    
    bot = TradingBot()
    
    # Setup signal handlers for graceful shutdown (Unix-like systems only)
    # Windows doesn't support loop.add_signal_handler
    if sys.platform != 'win32':
        loop = asyncio.get_running_loop()
        
        def signal_handler(sig):
            logger.info(f"Received signal {sig}, initiating shutdown...")
            bot.stop()
        
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))
    else:
        # On Windows, we rely on KeyboardInterrupt (Ctrl+C)
        logger.info("Running on Windows - use Ctrl+C to stop")
    
    try:
        await bot.setup()
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        bot.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown complete")
        sys.exit(0)
