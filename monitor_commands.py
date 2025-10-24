"""
Real-time log monitor for bot commands.

Run this while the bot is running to see command activity.
"""

import time
import os
from pathlib import Path

def tail_logs():
    """Monitor the most recent log file for command activity."""
    
    print("=" * 80)
    print("Bot Command Activity Monitor")
    print("=" * 80)
    print()
    print("Watching for command activity...")
    print("Press Ctrl+C to stop")
    print()
    print("=" * 80)
    print()
    
    # Look for log files
    log_files = list(Path(".").glob("*.log"))
    
    if not log_files:
        print("❌ No log files found in current directory")
        print()
        print("Make sure:")
        print("1. Bot is running")
        print("2. Bot is configured to log to files")
        print("3. You're in the bot directory")
        return
    
    # Get most recent log file
    latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
    print(f"📁 Monitoring: {latest_log}")
    print()
    
    try:
        with open(latest_log, 'r', encoding='utf-8', errors='ignore') as f:
            # Go to end of file
            f.seek(0, 2)
            
            while True:
                line = f.readline()
                if line:
                    # Filter for command-related lines
                    if any(keyword in line for keyword in [
                        'Command', 'command', '>help', '>status', '>signal', '>signals',
                        'invoked', 'completed', 'error'
                    ]):
                        # Color code output
                        if 'completed successfully' in line.lower():
                            print(f"✅ {line.strip()}")
                        elif 'error' in line.lower():
                            print(f"❌ {line.strip()}")
                        elif 'invoked' in line.lower():
                            print(f"📨 {line.strip()}")
                        else:
                            print(f"   {line.strip()}")
                else:
                    time.sleep(0.1)
    
    except KeyboardInterrupt:
        print()
        print("=" * 80)
        print("✅ Monitoring stopped")
        print("=" * 80)
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    tail_logs()
