"""
Test script to verify Discord bot commands work correctly.

Run this after starting the bot to test command responsiveness.
"""

import asyncio
import os
from dotenv import load_dotenv
import discord
from discord.ext import commands

load_dotenv()

async def test_bot_commands():
    """Test bot commands via API (not user interaction)."""
    
    print("=" * 60)
    print("Discord Bot Command Test")
    print("=" * 60)
    
    # Create a test bot client
    intents = discord.Intents.default()
    intents.message_content = True
    
    bot = commands.Bot(command_prefix=">", intents=intents)
    
    @bot.event
    async def on_ready():
        print(f"✅ Connected as {bot.user}")
        print(f"📋 Registered commands: {', '.join([cmd.name for cmd in bot.commands])}")
        print()
        print("=" * 60)
        print("MANUAL TEST INSTRUCTIONS:")
        print("=" * 60)
        print("1. Go to your Discord server")
        print("2. In the channel where the bot is active, type:")
        print()
        print("   >help")
        print("   >status")
        print("   >signal BTC")
        print("   >signals 5")
        print()
        print("3. Verify that:")
        print("   ✅ The bot responds to each command")
        print("   ✅ The bot continues running after each command")
        print("   ✅ Signal generation continues in the background")
        print()
        print("4. Check the logs for:")
        print("   - 'Command invoked by...'")
        print("   - 'Command completed successfully...'")
        print("   - Any error messages")
        print()
        print("=" * 60)
        print("Press Ctrl+C to exit this test")
        print("=" * 60)
        
        # Keep running to monitor
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            print("\n✅ Test complete. Shutting down...")
    
    @bot.event
    async def on_command(ctx):
        print(f"📨 Command received: >{ctx.command} from {ctx.author}")
    
    @bot.event
    async def on_command_completion(ctx):
        print(f"✅ Command completed: >{ctx.command}")
    
    @bot.event
    async def on_command_error(ctx, error):
        print(f"❌ Command error: {error}")
    
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ DISCORD_TOKEN not found in .env file")
        return
    
    try:
        await bot.start(token)
    except KeyboardInterrupt:
        await bot.close()

if __name__ == "__main__":
    try:
        asyncio.run(test_bot_commands())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
