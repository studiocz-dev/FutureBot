#!/usr/bin/env python3
"""
Launcher script for FutureBot.
This allows the bot to be started as a script while maintaining proper package imports.
"""
import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Now import and run the bot
from src.bot.main import main

if __name__ == "__main__":
    asyncio.run(main())
