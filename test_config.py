"""
Quick configuration test script.

Run this to verify your .env configuration before starting the bot.
"""

import sys
from pathlib import Path

def test_config():
    """Test configuration and dependencies."""
    print("🔍 Testing WyEli Bot Configuration...\n")
    
    errors = []
    warnings = []
    
    # Test 1: Check Python version
    print("1️⃣ Checking Python version...")
    if sys.version_info < (3, 11):
        errors.append(f"Python 3.11+ required, but you have {sys.version}")
    else:
        print(f"   ✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    # Test 2: Check .env file exists
    print("\n2️⃣ Checking .env file...")
    env_file = Path(".env")
    if not env_file.exists():
        errors.append(".env file not found! Copy .env.example to .env and fill it in.")
    else:
        print("   ✅ .env file found")
    
    # Test 3: Try to import required modules
    print("\n3️⃣ Checking dependencies...")
    required_modules = [
        'discord',
        'supabase',
        'aiohttp',
        'websockets',
        'pandas',
        'pandas_ta',
        'numpy',
        'pydantic',
        'dotenv'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module if module != 'dotenv' else 'dotenv')
            print(f"   ✅ {module}")
        except ImportError:
            missing_modules.append(module)
            print(f"   ❌ {module}")
    
    if missing_modules:
        errors.append(f"Missing modules: {', '.join(missing_modules)}\n   Run: pip install -r requirements.txt")
    
    # Test 4: Try to load configuration
    print("\n4️⃣ Checking configuration...")
    if env_file.exists():
        try:
            from src.bot.config import Config
            config = Config.from_env()
            
            # Check required fields
            if not config.supabase.url:
                errors.append("SUPABASE_URL not set in .env")
            else:
                print(f"   ✅ Supabase URL: {config.supabase.url[:30]}...")
            
            if not config.supabase.key:
                errors.append("SUPABASE_SERVICE_KEY not set in .env")
            else:
                print(f"   ✅ Supabase Key: {config.supabase.key[:20]}...")
            
            if not config.discord.token:
                errors.append("DISCORD_TOKEN not set in .env")
            else:
                print(f"   ✅ Discord Token: {config.discord.token[:20]}...")
            
            if not config.discord.signals_channel_id:
                warnings.append("DISCORD_SIGNALS_CHANNEL_ID not set - bot won't send signal alerts")
            else:
                print(f"   ✅ Signals Channel: {config.discord.signals_channel_id}")
            
            if not config.signals.symbols:
                warnings.append("No SYMBOLS configured")
            else:
                print(f"   ✅ Symbols: {', '.join(config.signals.symbols)}")
            
            if not config.signals.timeframes:
                warnings.append("No TIMEFRAMES configured")
            else:
                print(f"   ✅ Timeframes: {', '.join(config.signals.timeframes)}")
            
            print(f"   ℹ️  Min Confidence: {config.signals.min_confidence}")
            print(f"   ℹ️  Trading Enabled: {config.trading.enabled}")
            
        except Exception as e:
            errors.append(f"Configuration error: {e}")
    
    # Test 5: Check source files exist
    print("\n5️⃣ Checking source files...")
    required_files = [
        'src/bot/main.py',
        'src/bot/config.py',
        'src/discord/commands.py',
        'src/discord/notifier.py',
        'src/signals/fuse.py',
        'src/storage/supabase_client.py',
    ]
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"   ✅ {file_path}")
        else:
            errors.append(f"Missing file: {file_path}")
    
    # Print summary
    print("\n" + "="*50)
    print("📊 SUMMARY")
    print("="*50)
    
    if errors:
        print("\n❌ ERRORS (must fix):")
        for i, error in enumerate(errors, 1):
            print(f"   {i}. {error}")
    
    if warnings:
        print("\n⚠️  WARNINGS (recommended to fix):")
        for i, warning in enumerate(warnings, 1):
            print(f"   {i}. {warning}")
    
    if not errors and not warnings:
        print("\n✅ All checks passed! You're ready to run the bot.")
        print("\nNext steps:")
        print("   1. Run: python -m src.bot.main")
        print("   2. Or press F5 in VS Code")
        print("   3. Test commands in Discord: >help")
    elif not errors:
        print("\n✅ Configuration looks good!")
        print("⚠️  Fix warnings for optimal experience.")
        print("\nTo start bot: python -m src.bot.main")
    else:
        print("\n❌ Please fix errors before running the bot.")
        return 1
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = test_config()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
