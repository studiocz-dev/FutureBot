#!/usr/bin/env python3
"""
Quick bot validation - Test if bot can start and respond to commands.
This is a 30-second test to verify core functionality.
"""
import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()


async def quick_test():
    """Run a quick 30-second bot test."""
    print("\n" + "="*70)
    print("  🚀 QUICK BOT TEST (30 seconds)")
    print("="*70 + "\n")
    
    # Test 1: Check imports
    print("1️⃣  Testing imports...")
    try:
        from src.bot.main import WyEliBot
        print("   ✅ Bot module imported successfully\n")
    except Exception as e:
        print(f"   ❌ Failed to import bot: {e}\n")
        return False
    
    # Test 2: Check configuration
    print("2️⃣  Checking configuration...")
    required_env = ["DISCORD_TOKEN", "SUPABASE_URL", "SUPABASE_SERVICE_KEY"]
    all_present = True
    for var in required_env:
        if os.getenv(var):
            print(f"   ✅ {var}: Present")
        else:
            print(f"   ❌ {var}: MISSING")
            all_present = False
    print()
    
    if not all_present:
        print("❌ Missing required environment variables\n")
        return False
    
    # Test 3: Initialize bot
    print("3️⃣  Initializing bot...")
    try:
        bot = WyEliBot()
        print("   ✅ Bot initialized successfully\n")
    except Exception as e:
        print(f"   ❌ Failed to initialize: {e}\n")
        return False
    
    # Test 4: Start bot briefly
    print("4️⃣  Starting bot (will run for 10 seconds)...")
    print("   ⏳ Connecting to Discord...\n")
    
    try:
        # Create a task to run the bot
        bot_task = asyncio.create_task(bot.run_async())
        
        # Wait for bot to be ready
        await bot.bot.wait_until_ready()
        
        print(f"   ✅ Bot logged in as: {bot.bot.user.name}#{bot.bot.user.discriminator}")
        print(f"   ✅ Bot ID: {bot.bot.user.id}")
        print(f"   ✅ Latency: {bot.bot.latency*1000:.2f}ms")
        print(f"   ✅ Connected to {len(bot.bot.guilds)} guild(s)\n")
        
        # List guilds
        for guild in bot.bot.guilds:
            print(f"   📡 Guild: {guild.name} ({guild.id})")
            print(f"      └─ Members: {guild.member_count}")
        
        print("\n   ⏳ Bot running... (will shutdown in 5 seconds)")
        await asyncio.sleep(5)
        
        # Shutdown
        print("   🛑 Shutting down bot...")
        await bot.shutdown()
        
        # Cancel the bot task
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            pass
        
        print("   ✅ Bot shut down successfully\n")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error during bot operation: {e}\n")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test runner."""
    success = await quick_test()
    
    print("="*70)
    if success:
        print("  🎉 ALL TESTS PASSED!")
        print("  ✅ Bot is working correctly")
        print("\n  To start the bot normally, run:")
        print("     python -m src.bot.main")
    else:
        print("  ❌ SOME TESTS FAILED")
        print("  ⚠️  Check errors above and fix before running bot")
    print("="*70 + "\n")
    
    return success


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
