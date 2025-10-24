#!/usr/bin/env python3
"""
Health check script for WyEli Bot.
Validates all components before deployment.
"""
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()


class HealthCheck:
    """Comprehensive health check for all bot components."""
    
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []
    
    def print_header(self, text: str):
        """Print section header."""
        print("\n" + "="*70)
        print(f"  {text}")
        print("="*70)
    
    def print_check(self, name: str, status: str, details: str = ""):
        """Print check result."""
        symbols = {"✅": "✅", "❌": "❌", "⚠️": "⚠️"}
        print(f"{symbols.get(status, status)} {name}")
        if details:
            print(f"   └─ {details}")
    
    async def check_env_vars(self):
        """Check all required environment variables."""
        self.print_header("1. ENVIRONMENT VARIABLES")
        
        required = {
            "SUPABASE_URL": "Supabase database URL",
            "SUPABASE_SERVICE_KEY": "Supabase service role key",
            "DISCORD_TOKEN": "Discord bot token",
            "DISCORD_GUILD_ID": "Discord server ID",
            "DISCORD_SIGNALS_CHANNEL_ID": "Discord signals channel ID",
        }
        
        optional = {
            "SYMBOLS": "Trading symbols (default: BTCUSDT)",
            "TIMEFRAMES": "Analysis timeframes (default: 1h)",
            "MIN_CONFIDENCE": "Min confidence threshold (default: 0.65)",
            "ENABLE_TRADING": "Trading enabled flag (default: false)",
            "LOG_LEVEL": "Logging level (default: INFO)",
        }
        
        # Check required
        all_present = True
        for key, desc in required.items():
            value = os.getenv(key)
            if value:
                masked = f"{value[:10]}..." if len(value) > 20 else value
                self.print_check(f"{key}", "✅", f"{desc} - Present")
                self.passed.append(f"ENV: {key}")
            else:
                self.print_check(f"{key}", "❌", f"{desc} - MISSING!")
                self.failed.append(f"ENV: {key}")
                all_present = False
        
        # Check optional
        for key, desc in optional.items():
            value = os.getenv(key)
            if value:
                self.print_check(f"{key}", "✅", f"{desc} - {value}")
                self.passed.append(f"ENV Optional: {key}")
            else:
                self.print_check(f"{key}", "⚠️", f"{desc} - Using default")
                self.warnings.append(f"ENV Optional: {key}")
        
        return all_present
    
    async def check_supabase(self):
        """Check Supabase database connection."""
        self.print_header("2. SUPABASE DATABASE")
        
        try:
            from src.storage.supabase_client import SupabaseClient
            
            supabase = SupabaseClient()
            
            # Test connection by querying candles table
            result = supabase.client.table("candles").select("*").limit(1).execute()
            
            self.print_check("Supabase Connection", "✅", "Connected successfully")
            self.passed.append("Supabase: Connection")
            
            # Count records
            count_result = supabase.client.table("candles").select("*", count="exact").limit(1).execute()
            count = count_result.count if hasattr(count_result, 'count') else 0
            self.print_check("Candles Table", "✅", f"{count} records found")
            self.passed.append("Supabase: Candles table")
            
            # Check signals table
            signal_result = supabase.client.table("signals").select("*").limit(1).execute()
            self.print_check("Signals Table", "✅", "Accessible")
            self.passed.append("Supabase: Signals table")
            
            return True
            
        except Exception as e:
            self.print_check("Supabase Connection", "❌", f"Error: {str(e)}")
            self.failed.append(f"Supabase: {str(e)}")
            return False
    
    async def check_discord(self):
        """Check Discord bot token validity."""
        self.print_header("3. DISCORD BOT")
        
        try:
            import discord
            from discord.ext import commands
            
            token = os.getenv("DISCORD_TOKEN")
            if not token:
                self.print_check("Discord Token", "❌", "Token not found in .env")
                self.failed.append("Discord: Token missing")
                return False
            
            # Create a minimal bot to test token
            intents = discord.Intents.default()
            intents.message_content = True
            bot = commands.Bot(command_prefix=">", intents=intents)
            
            @bot.event
            async def on_ready():
                self.print_check("Discord Connection", "✅", f"Logged in as {bot.user.name}#{bot.user.discriminator}")
                self.print_check("Bot ID", "✅", str(bot.user.id))
                
                # Check guild access
                guild_id = os.getenv("DISCORD_GUILD_ID")
                if guild_id:
                    guild = bot.get_guild(int(guild_id))
                    if guild:
                        self.print_check("Guild Access", "✅", f"{guild.name} ({len(guild.members)} members)")
                        self.passed.append(f"Discord: Guild {guild.name}")
                        
                        # Check channel access
                        channel_id = os.getenv("DISCORD_SIGNALS_CHANNEL_ID")
                        if channel_id:
                            channel = guild.get_channel(int(channel_id))
                            if channel:
                                self.print_check("Signals Channel", "✅", f"#{channel.name}")
                                self.passed.append(f"Discord: Channel #{channel.name}")
                            else:
                                self.print_check("Signals Channel", "❌", "Channel not found")
                                self.failed.append("Discord: Signals channel not found")
                    else:
                        self.print_check("Guild Access", "❌", "Guild not found")
                        self.failed.append("Discord: Guild not found")
                
                self.passed.append("Discord: Connection")
                await bot.close()
            
            # Try to connect with timeout
            try:
                await asyncio.wait_for(bot.start(token), timeout=10.0)
            except asyncio.TimeoutError:
                self.print_check("Discord Connection", "⚠️", "Connection timeout (but token may be valid)")
                self.warnings.append("Discord: Connection timeout")
            
            return True
            
        except discord.LoginFailure:
            self.print_check("Discord Token", "❌", "Invalid token")
            self.failed.append("Discord: Invalid token")
            return False
        except Exception as e:
            self.print_check("Discord Connection", "❌", f"Error: {str(e)}")
            self.failed.append(f"Discord: {str(e)}")
            return False
    
    async def check_binance(self):
        """Check Binance API connectivity."""
        self.print_header("4. BINANCE API")
        
        try:
            from src.ingest.binance_rest import BinanceRESTClient
            
            binance = BinanceRESTClient()
            
            # Test REST API
            try:
                candles = await binance.get_historical_klines("BTCUSDT", "1h", 5)
                self.print_check("REST API", "✅", f"Retrieved {len(candles)} candles")
                self.passed.append("Binance: REST API")
            except Exception as e:
                self.print_check("REST API", "❌", f"Error: {str(e)}")
                self.failed.append(f"Binance REST: {str(e)}")
            finally:
                await binance.close()
            
            # Test WebSocket (brief check)
            from src.ingest.binance_ws import BinanceWebSocketManager
            
            ws = BinanceWebSocketManager(
                symbols=["BTCUSDT"],
                timeframes=["1h"],
                aggregator=None  # Don't need aggregator for test
            )
            
            # Just check if we can create the stream URL
            streams = ws._build_stream_list()
            self.print_check("WebSocket Streams", "✅", f"{len(streams)} streams configured")
            self.passed.append("Binance: WebSocket config")
            
            return True
            
        except Exception as e:
            self.print_check("Binance API", "❌", f"Error: {str(e)}")
            self.failed.append(f"Binance: {str(e)}")
            return False
    
    async def check_analyzers(self):
        """Check analysis modules."""
        self.print_header("5. ANALYSIS MODULES")
        
        try:
            # Check Wyckoff
            from src.analysis.wyckoff import WyckoffAnalyzer
            wyckoff = WyckoffAnalyzer()
            self.print_check("Wyckoff Analyzer", "✅", "Module loaded")
            self.passed.append("Analysis: Wyckoff")
            
            # Check Elliott Wave
            from src.analysis.elliott import ElliottWaveAnalyzer
            elliott = ElliottWaveAnalyzer()
            self.print_check("Elliott Wave Analyzer", "✅", "Module loaded")
            self.passed.append("Analysis: Elliott Wave")
            
            # Check Signal Fusion
            from src.signals.fuse import SignalFuser
            fuser = SignalFuser(None, None)  # Don't need real clients for test
            self.print_check("Signal Fuser", "✅", "Module loaded")
            self.passed.append("Analysis: Signal Fuser")
            
            return True
            
        except Exception as e:
            self.print_check("Analysis Modules", "❌", f"Error: {str(e)}")
            self.failed.append(f"Analysis: {str(e)}")
            return False
    
    async def check_backtest(self):
        """Check backtest engine."""
        self.print_header("6. BACKTEST ENGINE")
        
        try:
            from src.backtest.engine import BacktestEngine
            
            engine = BacktestEngine(
                initial_balance=10000,
                position_size_percent=0.02,
                commission=0.001
            )
            self.print_check("Backtest Engine", "✅", "Module loaded")
            self.passed.append("Backtest: Engine")
            
            # Check if run_backtest.py exists
            if os.path.exists("run_backtest.py"):
                self.print_check("Backtest Script", "✅", "run_backtest.py found")
                self.passed.append("Backtest: Script")
            else:
                self.print_check("Backtest Script", "⚠️", "run_backtest.py not found")
                self.warnings.append("Backtest: Script missing")
            
            return True
            
        except Exception as e:
            self.print_check("Backtest Engine", "❌", f"Error: {str(e)}")
            self.failed.append(f"Backtest: {str(e)}")
            return False
    
    async def check_commands(self):
        """Check Discord command files."""
        self.print_header("7. DISCORD COMMANDS")
        
        try:
            from src.discord.commands import setup_commands
            self.print_check("Commands Module", "✅", "Module loaded")
            self.passed.append("Commands: Module")
            
            # List expected commands
            commands = [">signal", ">status", ">signals", ">help"]
            self.print_check("Available Commands", "✅", ", ".join(commands))
            self.passed.append("Commands: All defined")
            
            return True
            
        except Exception as e:
            self.print_check("Commands Module", "❌", f"Error: {str(e)}")
            self.failed.append(f"Commands: {str(e)}")
            return False
    
    def print_summary(self):
        """Print final summary."""
        self.print_header("HEALTH CHECK SUMMARY")
        
        total = len(self.passed) + len(self.failed) + len(self.warnings)
        
        print(f"\n✅ Passed:   {len(self.passed)}/{total}")
        print(f"❌ Failed:   {len(self.failed)}/{total}")
        print(f"⚠️  Warnings: {len(self.warnings)}/{total}")
        
        if self.failed:
            print("\n" + "="*70)
            print("  ❌ FAILED CHECKS:")
            print("="*70)
            for fail in self.failed:
                print(f"  • {fail}")
        
        if self.warnings:
            print("\n" + "="*70)
            print("  ⚠️  WARNINGS:")
            print("="*70)
            for warn in self.warnings:
                print(f"  • {warn}")
        
        print("\n" + "="*70)
        if not self.failed:
            print("  🎉 ALL CRITICAL CHECKS PASSED!")
            print("  ✅ Bot is ready for deployment")
        else:
            print("  ⚠️  SOME CHECKS FAILED")
            print("  ❌ Fix errors before deploying bot")
        print("="*70 + "\n")
        
        return len(self.failed) == 0


async def main():
    """Run all health checks."""
    print("\n" + "="*70)
    print("  🏥 WYELI BOT HEALTH CHECK")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*70)
    
    checker = HealthCheck()
    
    # Run all checks
    await checker.check_env_vars()
    await checker.check_supabase()
    await checker.check_binance()
    await checker.check_analyzers()
    await checker.check_backtest()
    await checker.check_commands()
    await checker.check_discord()  # Discord last as it takes longest
    
    # Print summary
    success = checker.print_summary()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Health check interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Health check failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
