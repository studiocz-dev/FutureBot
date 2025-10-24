"""
Quick diagnostic to test Metrics and SignalFuser classes.

Run this to see if there are issues with get_stats() or get_summary().
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.metrics import Metrics
from src.signals.fuse import SignalFuser
from src.bot.logger import get_logger

logger = get_logger(__name__)

print("=" * 80)
print("Metrics & SignalFuser Diagnostic")
print("=" * 80)
print()

# Test Metrics
print("Testing Metrics class...")
try:
    metrics = Metrics()
    print("✅ Metrics created successfully")
    
    print("   Testing get_summary()...")
    summary = metrics.get_summary()
    print(f"✅ get_summary() returned: {summary}")
    
    print("   Testing get_signal_count()...")
    count = metrics.get_signal_count()
    print(f"✅ get_signal_count() returned: {count}")
    
except Exception as e:
    print(f"❌ Metrics error: {e}")
    import traceback
    traceback.print_exc()

print()

# Test SignalFuser (without Supabase)
print("Testing SignalFuser class...")
try:
    # Create a mock supabase object
    class MockSupabase:
        async def insert_signal(self, signal):
            return "mock-id"
    
    fuser = SignalFuser(
        supabase=MockSupabase(),
        min_confidence=0.65,
        enable_wyckoff=True,
        enable_elliott=True,
        cooldown=300,
        prevent_conflicts=True,
    )
    print("✅ SignalFuser created successfully")
    
    print("   Testing get_stats()...")
    stats = fuser.get_stats()
    print(f"✅ get_stats() returned: {stats}")
    
except Exception as e:
    print(f"❌ SignalFuser error: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
print("Diagnostic complete")
print("=" * 80)
print()

if __name__ != "__main__":
    print("Note: Run this script directly, not as a module")
