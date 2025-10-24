"""
Discord prefix commands module.

Provides interactive text commands with > prefix for bot control.
Commands: >signal BTC, >status, >help
"""

from typing import Optional, Any
import discord
from discord.ext import commands

from ..bot.logger import get_logger

logger = get_logger(__name__)


def setup_commands(
    bot: commands.Bot,
    supabase: Any,  # SupabaseClient
    signal_fuser: Any,  # SignalFuser
    metrics: Any,  # Metrics
) -> None:
    """
    Register prefix commands with the bot.
    
    Args:
        bot: Discord bot instance
        supabase: Supabase client
        signal_fuser: Signal fuser instance
        metrics: Metrics tracker
    """
    
    @bot.event
    async def on_command_error(ctx: commands.Context, error: commands.CommandError):
        """
        Global error handler for commands.
        Prevents commands from crashing the bot.
        """
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(f"❌ Unknown command. Use `>help` to see available commands.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: `{error.param.name}`. Use `>help` for usage.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Invalid argument. Use `>help` for usage.")
        elif isinstance(error, commands.CommandInvokeError):
            logger.error(f"Error executing command: {error.original}", exc_info=error.original)
            await ctx.send("❌ An error occurred while executing the command. Please try again later.")
        else:
            logger.error(f"Unhandled command error: {error}", exc_info=error)
            await ctx.send("❌ An unexpected error occurred.")
    
    
    @bot.command(name="signal", aliases=["s"])
    async def signal_command(ctx: commands.Context, symbol: Optional[str] = None, timeframe: Optional[str] = "1h"):
        """
        Get the latest signal for a symbol.
        
        Usage: >signal BTC [timeframe]
        Example: >signal BTC 1h
        """
        try:
            # If no symbol provided, show help
            if not symbol:
                embed = discord.Embed(
                    title="📊 Signal Command",
                    description="Get the latest trading signal for a cryptocurrency",
                    color=discord.Color.blue(),
                )
                embed.add_field(
                    name="Usage",
                    value="`>signal <symbol> [timeframe]`\n"
                          "`>signal BTC`\n"
                          "`>signal ETH 4h`\n"
                          "`>signal BNB 15m`",
                    inline=False
                )
                embed.add_field(
                    name="Supported Symbols",
                    value="BTC, ETH, BNB, SOL, ADA (and more)\n"
                          "_Use ticker without USDT_",
                    inline=False
                )
                embed.add_field(
                    name="Timeframes",
                    value="15m, 1h, 4h, 1d (default: 1h)",
                    inline=False
                )
                await ctx.send(embed=embed)
                return
            
            # Normalize symbol (add USDT if not present)
            symbol = symbol.upper()
            if not symbol.endswith("USDT"):
                symbol = f"{symbol}USDT"
            
            # Normalize timeframe
            timeframe = timeframe.lower()
            
            # Fetch recent signal
            signals = await supabase.get_recent_signals(
                symbol=symbol,
                timeframe=timeframe,
                limit=1
            )
            
            if not signals:
                await ctx.send(f"❌ No signals found for **{symbol}** ({timeframe})")
                return
            
            signal = signals[0]
            
            # Create rich embed
            color = discord.Color.green() if signal['signal_type'] == 'LONG' else discord.Color.red()
            emoji = "🚀" if signal['signal_type'] == 'LONG' else "📉"
            
            embed = discord.Embed(
                title=f"{emoji} {signal['signal_type']} SIGNAL - {signal['symbol']}",
                description=f"**Timeframe:** {signal['timeframe']}\n"
                           f"**Confidence:** {float(signal['confidence']) * 100:.1f}%",
                color=color,
                timestamp=signal.get('created_at')
            )
            
            # Price levels
            entry = float(signal['entry_price'])
            sl = float(signal['stop_loss'])
            tp = float(signal['take_profit'])
            
            embed.add_field(
                name="� Entry Price",
                value=f"${entry:,.4f}",
                inline=True
            )
            
            embed.add_field(
                name="🛑 Stop Loss",
                value=f"${sl:,.4f}",
                inline=True
            )
            
            embed.add_field(
                name="🎯 Take Profit",
                value=f"${tp:,.4f}",
                inline=True
            )
            
            # Risk/Reward
            risk = abs(entry - sl)
            reward = abs(tp - entry)
            rr_ratio = reward / risk if risk > 0 else 0
            
            embed.add_field(
                name="� Risk/Reward",
                value=f"{rr_ratio:.2f}:1",
                inline=True
            )
            
            # Analysis details
            if signal.get('wyckoff_phase'):
                embed.add_field(
                    name="📈 Wyckoff Phase",
                    value=signal['wyckoff_phase'],
                    inline=True
                )
            
            if signal.get('elliott_count'):
                embed.add_field(
                    name="🌊 Elliott Count",
                    value=signal['elliott_count'],
                    inline=True
                )
            
            # Rationale
            if signal.get('rationale'):
                embed.add_field(
                    name="💡 Analysis",
                    value=signal['rationale'][:200] + "..." if len(signal['rationale']) > 200 else signal['rationale'],
                    inline=False
                )
            
            embed.set_footer(text="⚠️ Not financial advice • Educational purposes only")
            
            await ctx.send(embed=embed)
            logger.info(f"Signal command executed by {ctx.author}: {symbol} {timeframe}")
        
        except Exception as e:
            logger.error(f"Error in signal command: {e}", exc_info=True)
            await ctx.send("❌ An error occurred while fetching the signal.")
    
    @bot.command(name="status")
    async def status_command(ctx: commands.Context):
        """
        Show bot status and statistics.
        
        Usage: >status
        """
        try:
            logger.info(f"Status command called by {ctx.author}")
            
            # Gather status information
            logger.debug("Fetching fuser stats...")
            fuser_stats = signal_fuser.get_stats()
            
            logger.debug("Fetching metrics data...")
            metrics_data = metrics.get_summary()
            
            logger.debug("Creating embed...")
            embed = discord.Embed(
                title="🤖 Bot Status",
                description="Current bot statistics and configuration",
                color=discord.Color.blue(),
            )
            
            embed.add_field(
                name="⚙️ Configuration",
                value=f"Min Confidence: {fuser_stats['min_confidence']:.0%}\n"
                      f"Wyckoff: {'✅' if fuser_stats['wyckoff_enabled'] else '❌'}\n"
                      f"Elliott Wave: {'✅' if fuser_stats['elliott_enabled'] else '❌'}\n"
                      f"Cooldown: {fuser_stats['cooldown_seconds']}s",
                inline=True
            )
            
            embed.add_field(
                name="📊 Signals Today",
                value=f"Total: {metrics_data.get('total_signals', 0)}\n"
                      f"Long: {metrics_data.get('long_signals', 0)}\n"
                      f"Short: {metrics_data.get('short_signals', 0)}",
                inline=True
            )
            
            embed.add_field(
                name="🔥 Active Cooldowns",
                value=str(fuser_stats['active_cooldowns']),
                inline=True
            )
            
            embed.set_footer(text=f"Bot: {bot.user.name}")
            
            logger.debug("Sending status embed...")
            await ctx.send(embed=embed)
            logger.info(f"Status command executed successfully by {ctx.author}")
        
        except Exception as e:
            logger.error(f"Error in status command: {e}", exc_info=True)
            await ctx.send("❌ An error occurred while fetching status.")
    
    @bot.command(name="help", aliases=["h", "commands"])
    async def help_command(ctx: commands.Context):
        """
        Show bot help and available commands.
        
        Usage: >help
        """
        try:
            embed = discord.Embed(
                title="📚 Wyckoff-Elliott Bot Help",
                description="Trading signals bot using Wyckoff Method and Elliott Wave analysis",
                color=discord.Color.blue(),
            )
            
            embed.add_field(
                name=">signal <symbol> [timeframe]",
                value="Get latest signal for a crypto\n"
                      "**Examples:**\n"
                      "`>signal BTC`\n"
                      "`>signal ETH 4h`\n"
                      "`>signal BNB 15m`",
                inline=False
            )
            
            embed.add_field(
                name=">status",
                value="Show bot status and statistics",
                inline=False
            )
            
            embed.add_field(
                name=">help",
                value="Show this help message",
                inline=False
            )
            
            embed.add_field(
                name="📊 Supported Symbols",
                value="BTC, ETH, BNB, SOL, ADA\n_Use ticker only, USDT is added automatically_",
                inline=True
            )
            
            embed.add_field(
                name="⏰ Timeframes",
                value="15m, 1h (default), 4h, 1d",
                inline=True
            )
            
            embed.set_footer(text="⚠️ Educational purposes only • Not financial advice")
            
            await ctx.send(embed=embed)
            logger.info(f"Help command executed by {ctx.author}")
        
        except Exception as e:
            logger.error(f"Error in help command: {e}", exc_info=True)
            await ctx.send("❌ An error occurred.")
    
    @bot.command(name="signals", aliases=["list"])
    async def signals_list_command(ctx: commands.Context, limit: int = 5):
        """
        Show recent signals across all symbols.
        
        Usage: >signals [limit]
        """
        try:
            if limit > 20:
                limit = 20
            
            # Fetch recent signals
            signals = await supabase.get_recent_signals(
                symbol=None,
                timeframe=None,
                limit=limit
            )
            
            if not signals:
                await ctx.send("❌ No signals found")
                return
            
            embed = discord.Embed(
                title=f"📊 Recent Signals (Last {len(signals)})",
                color=discord.Color.blue(),
            )
            
            for signal in signals:
                emoji = "🚀" if signal['signal_type'] == 'LONG' else "📉"
                confidence = float(signal['confidence']) * 100
                
                value = (
                    f"**{signal['signal_type']}** @ ${float(signal['entry_price']):,.4f}\n"
                    f"Confidence: {confidence:.1f}% | TF: {signal['timeframe']}\n"
                    f"<t:{int(signal['created_at'].timestamp())}:R>"
                )
                
                embed.add_field(
                    name=f"{emoji} {signal['symbol']}",
                    value=value,
                    inline=False
                )
            
            embed.set_footer(text=f"Use >signal <symbol> for details")
            
            await ctx.send(embed=embed)
            logger.info(f"Signals list command executed by {ctx.author}")
        
        except Exception as e:
            logger.error(f"Error in signals list command: {e}", exc_info=True)
            await ctx.send("❌ An error occurred while fetching signals.")
    
    # Log all registered commands
    registered_commands = [cmd.name for cmd in bot.commands]
    logger.info(f"Registered Discord prefix commands: {', '.join(registered_commands)}")
    logger.info(f"Total commands registered: {len(registered_commands)}")


