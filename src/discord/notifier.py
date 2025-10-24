"""
Discord notifier module.

Sends trading signals and status updates to Discord channels.
"""

import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime

import discord
from discord.ext import commands

from ..bot.logger import get_logger

logger = get_logger(__name__)


class DiscordNotifier:
    """Sends formatted messages to Discord channels."""
    
    def __init__(
        self,
        bot: commands.Bot,
        channel_id: Optional[int] = None,
    ):
        """
        Initialize Discord notifier.
        
        Args:
            bot: Discord bot instance
            channel_id: Default channel ID for notifications
        """
        self.bot = bot
        self.default_channel_id = channel_id
        self.rate_limit_delay = 1.0  # Seconds between messages
        self.last_message_time = 0.0
    
    async def _get_channel(self, channel_id: Optional[int] = None) -> Optional[discord.TextChannel]:
        """
        Get Discord channel.
        
        Args:
            channel_id: Channel ID (uses default if None)
        
        Returns:
            Discord text channel or None
        """
        cid = channel_id or self.default_channel_id
        if not cid:
            logger.error("No channel ID provided")
            return None
        
        try:
            channel = self.bot.get_channel(cid)
            if channel is None:
                channel = await self.bot.fetch_channel(cid)
            return channel
        except Exception as e:
            logger.error(f"Error getting channel {cid}: {e}")
            return None
    
    async def _rate_limit(self) -> None:
        """Apply rate limiting between messages."""
        now = asyncio.get_event_loop().time()
        elapsed = now - self.last_message_time
        
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)
        
        self.last_message_time = asyncio.get_event_loop().time()
    
    def _create_signal_embed(self, signal: Dict[str, Any]) -> discord.Embed:
        """
        Create a rich embed for a trading signal.
        
        Args:
            signal: Signal dictionary
        
        Returns:
            Discord embed
        """
        signal_type = signal["type"]
        symbol = signal["symbol"]
        timeframe = signal["timeframe"]
        confidence = signal["confidence"]
        
        # Color based on signal type
        color = discord.Color.green() if signal_type == "LONG" else discord.Color.red()
        
        # Create embed
        embed = discord.Embed(
            title=f"🎯 {signal_type} Signal: {symbol}",
            description=f"**Timeframe:** {timeframe}\n**Confidence:** {confidence:.1%}",
            color=color,
            timestamp=datetime.utcnow(),
        )
        
        # Entry and targets
        entry = signal["entry_price"]
        stop_loss = signal.get("stop_loss")
        take_profit = signal.get("take_profit")
        take_profit_2 = signal.get("take_profit_2")
        take_profit_3 = signal.get("take_profit_3")
        
        targets_text = f"**Entry:** ${entry:.4f}\n"
        
        if stop_loss:
            targets_text += f"**Stop Loss:** ${stop_loss:.4f}\n\n"
        
        targets_text += f"**Take Profit 1:** ${take_profit:.4f}\n"
        
        if take_profit_2:
            targets_text += f"**Take Profit 2:** ${take_profit_2:.4f}\n"
        if take_profit_3:
            targets_text += f"**Take Profit 3:** ${take_profit_3:.4f}\n"
        
        embed.add_field(
            name="📊 Price Targets",
            value=targets_text,
            inline=False
        )
        
        # Risk/Reward
        if "risk_reward" in signal:
            rr = signal["risk_reward"]
            rr_text = (
                f"**R:R Ratio:** {rr['risk_reward_ratio']:.2f}:1\n"
                f"**Risk:** {rr['risk_percent']:.2f}%\n"
                f"**Reward:** {rr['reward_percent']:.2f}%"
            )
            embed.add_field(
                name="⚖️ Risk/Reward",
                value=rr_text,
                inline=True
            )
        
        # Wyckoff phase
        if signal.get("wyckoff_phase"):
            embed.add_field(
                name="📈 Wyckoff Phase",
                value=signal["wyckoff_phase"].title(),
                inline=True
            )
        
        # Elliott wave count
        if signal.get("elliott_wave_count"):
            embed.add_field(
                name="🌊 Elliott Wave",
                value=signal["elliott_wave_count"],
                inline=True
            )
        
        # Rationale
        if signal.get("rationale"):
            # Limit rationale length for Discord
            rationale = signal["rationale"]
            if len(rationale) > 1024:
                rationale = rationale[:1020] + "..."
            
            embed.add_field(
                name="💡 Analysis",
                value=rationale,
                inline=False
            )
        
        # Footer
        embed.set_footer(text="Wyckoff-Elliott Bot • Educational purposes only • Not financial advice")
        
        return embed
    
    async def send_signal(
        self,
        signal: Dict[str, Any],
        channel_id: Optional[int] = None
    ) -> Optional[discord.Message]:
        """
        Send a trading signal to Discord.
        
        Args:
            signal: Signal dictionary
            channel_id: Optional channel ID override
        
        Returns:
            Sent message or None
        """
        try:
            await self._rate_limit()
            
            channel = await self._get_channel(channel_id)
            if not channel:
                return None
            
            embed = self._create_signal_embed(signal)
            message = await channel.send(embed=embed)
            
            logger.info(f"Sent signal to Discord: {signal['type']} {signal['symbol']}")
            return message
        
        except Exception as e:
            logger.error(f"Error sending signal to Discord: {e}", exc_info=True)
            return None
    
    async def send_startup_message(
        self,
        symbols: List[str],
        timeframes: List[str],
        channel_id: Optional[int] = None
    ) -> None:
        """
        Send bot startup notification.
        
        Args:
            symbols: List of tracked symbols
            timeframes: List of tracked timeframes
            channel_id: Optional channel ID override
        """
        try:
            channel = await self._get_channel(channel_id)
            if not channel:
                return
            
            embed = discord.Embed(
                title="🚀 Wyckoff-Elliott Bot Started",
                description="Bot is now online and monitoring markets",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow(),
            )
            
            embed.add_field(
                name="📊 Tracked Symbols",
                value=", ".join(symbols),
                inline=False
            )
            
            embed.add_field(
                name="⏱️ Timeframes",
                value=", ".join(timeframes),
                inline=False
            )
            
            embed.set_footer(text="Educational purposes only • Not financial advice")
            
            await channel.send(embed=embed)
            logger.info("Sent startup message to Discord")
        
        except Exception as e:
            logger.error(f"Error sending startup message: {e}")
    
    async def send_error(
        self,
        error_message: str,
        channel_id: Optional[int] = None
    ) -> None:
        """
        Send an error notification.
        
        Args:
            error_message: Error message
            channel_id: Optional channel ID override
        """
        try:
            channel = await self._get_channel(channel_id)
            if not channel:
                return
            
            embed = discord.Embed(
                title="⚠️ Error Occurred",
                description=error_message,
                color=discord.Color.orange(),
                timestamp=datetime.utcnow(),
            )
            
            await channel.send(embed=embed)
        
        except Exception as e:
            logger.error(f"Error sending error message: {e}")
    
    async def send_status(
        self,
        status_data: Dict[str, Any],
        channel_id: Optional[int] = None
    ) -> None:
        """
        Send bot status update.
        
        Args:
            status_data: Status information
            channel_id: Optional channel ID override
        """
        try:
            channel = await self._get_channel(channel_id)
            if not channel:
                return
            
            embed = discord.Embed(
                title="📊 Bot Status",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow(),
            )
            
            for key, value in status_data.items():
                embed.add_field(
                    name=key.replace("_", " ").title(),
                    value=str(value),
                    inline=True
                )
            
            await channel.send(embed=embed)
        
        except Exception as e:
            logger.error(f"Error sending status: {e}")
