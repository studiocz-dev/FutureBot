"""
Diagnostic tool to check why symbols aren't generating signals.

This will analyze all symbols and show:
1. Which symbols have enough candles
2. Which symbols pass Wyckoff/Elliott analysis
3. Which symbols pass confidence threshold
4. Why signals are being skipped
"""

import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment
load_dotenv()

from src.bot.config import Config
from src.storage.supabase_client import SupabaseClient
from src.signals.wyckoff import WyckoffAnalyzer
from src.signals.elliott import ElliottWaveAnalyzer
from src.bot.logger import get_logger

logger = get_logger(__name__)

# Initialize analyzers
wyckoff_analyzer = WyckoffAnalyzer()
elliott_analyzer = ElliottWaveAnalyzer()


async def diagnose_symbols():
    """Diagnose why each symbol is or isn't generating signals."""
    
    config = Config()
    
    # Initialize Supabase
    supabase = SupabaseClient(
        url=config.supabase.url,
        key=config.supabase.service_key
    )
    await supabase.initialize()
    
    print("=" * 80)
    print("SYMBOL DIAGNOSTIC REPORT")
    print(f"Generated: {datetime.now()}")
    print("=" * 80)
    print()
    
    analysis_candles = config.historical.analysis_candles
    min_confidence = config.signals.min_confidence
    timeframe = config.signals.timeframes[0]  # Use first timeframe
    
    print(f"Configuration:")
    print(f"  - Timeframe: {timeframe}")
    print(f"  - Analysis Candles: {analysis_candles}")
    print(f"  - Min Confidence: {min_confidence * 100}%")
    print()
    
    results = []
    
    for symbol in config.signals.symbols:
        print(f"\nAnalyzing {symbol}...")
        print("-" * 40)
        
        try:
            # Get candles from database
            candles = await supabase.get_candles(
                symbol=symbol,
                timeframe=timeframe,
                limit=analysis_candles
            )
            
            if not candles:
                print(f"❌ No candles in database")
                results.append({
                    'symbol': symbol,
                    'status': 'NO_CANDLES',
                    'reason': 'No candles in database'
                })
                continue
            
            candle_count = len(candles)
            print(f"✅ Candles: {candle_count}/{analysis_candles}")
            
            if candle_count < config.historical.min_candles:
                print(f"❌ Not enough candles ({candle_count} < {config.historical.min_candles})")
                results.append({
                    'symbol': symbol,
                    'status': 'INSUFFICIENT_CANDLES',
                    'reason': f'Only {candle_count} candles'
                })
                continue
            
            # Get current price
            current_price = float(candles[-1]["close"])
            print(f"💰 Current Price: ${current_price}")
            
            # Analyze Wyckoff
            wyckoff_result = None
            if config.signals.enable_wyckoff:
                wyckoff_result = wyckoff_analyzer.analyze(candles)
                wyckoff_signal = wyckoff_result.get("signal")
                wyckoff_conf = wyckoff_result.get("confidence", 0.0)
                print(f"📊 Wyckoff: {wyckoff_signal or 'NONE'} ({wyckoff_conf*100:.1f}%)")
            else:
                print(f"📊 Wyckoff: DISABLED")
            
            # Analyze Elliott Wave
            elliott_result = None
            if config.signals.enable_elliott:
                elliott_result = elliott_analyzer.analyze(candles)
                elliott_signal = elliott_result.get("signal")
                elliott_conf = elliott_result.get("confidence", 0.0)
                print(f"🌊 Elliott: {elliott_signal or 'NONE'} ({elliott_conf*100:.1f}%)")
            else:
                print(f"🌊 Elliott: DISABLED")
            
            # Check if signals would be generated
            wyckoff_signal = wyckoff_result.get("signal") if wyckoff_result else None
            elliott_signal = elliott_result.get("signal") if elliott_result else None
            wyckoff_conf = wyckoff_result.get("confidence", 0.0) if wyckoff_result else 0.0
            elliott_conf = elliott_result.get("confidence", 0.0) if elliott_result else 0.0
            
            # Check signal fusion logic (from fuse.py)
            final_signal = None
            final_confidence = 0.0
            reason = ""
            
            if wyckoff_signal and elliott_signal:
                if wyckoff_signal == elliott_signal:
                    final_signal = wyckoff_signal
                    final_confidence = (wyckoff_conf + elliott_conf) / 2
                    reason = "Both agree"
                else:
                    reason = f"Disagree: Wyckoff={wyckoff_signal}, Elliott={elliott_signal}"
            elif wyckoff_signal and wyckoff_conf >= 0.75:
                final_signal = wyckoff_signal
                final_confidence = wyckoff_conf * 0.9
                reason = "Strong Wyckoff alone"
            elif elliott_signal and elliott_conf >= 0.75:
                final_signal = elliott_signal
                final_confidence = elliott_conf * 0.9
                reason = "Strong Elliott alone"
            else:
                reason = "No strong signals (need >=75% confidence)"
            
            if final_signal:
                if final_confidence >= min_confidence:
                    print(f"✅ WOULD SIGNAL: {final_signal} ({final_confidence*100:.1f}%) - {reason}")
                    results.append({
                        'symbol': symbol,
                        'status': 'SIGNAL',
                        'signal': final_signal,
                        'confidence': final_confidence,
                        'reason': reason
                    })
                else:
                    print(f"❌ Below threshold: {final_signal} ({final_confidence*100:.1f}% < {min_confidence*100}%) - {reason}")
                    results.append({
                        'symbol': symbol,
                        'status': 'LOW_CONFIDENCE',
                        'signal': final_signal,
                        'confidence': final_confidence,
                        'reason': f'Below {min_confidence*100}% threshold'
                    })
            else:
                print(f"❌ No signal: {reason}")
                results.append({
                    'symbol': symbol,
                    'status': 'NO_SIGNAL',
                    'reason': reason
                })
        
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({
                'symbol': symbol,
                'status': 'ERROR',
                'reason': str(e)
            })
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    signal_count = sum(1 for r in results if r['status'] == 'SIGNAL')
    low_conf_count = sum(1 for r in results if r['status'] == 'LOW_CONFIDENCE')
    no_signal_count = sum(1 for r in results if r['status'] == 'NO_SIGNAL')
    error_count = sum(1 for r in results if r['status'] == 'ERROR')
    
    print(f"\nTotal Symbols: {len(results)}")
    print(f"  ✅ Would Signal: {signal_count}")
    print(f"  ⚠️  Low Confidence: {low_conf_count}")
    print(f"  ❌ No Signal: {no_signal_count}")
    print(f"  ❌ Errors: {error_count}")
    
    if signal_count > 0:
        print(f"\n✅ Symbols that WOULD signal:")
        for r in results:
            if r['status'] == 'SIGNAL':
                print(f"  - {r['symbol']}: {r['signal']} ({r['confidence']*100:.1f}%) - {r['reason']}")
    
    if low_conf_count > 0:
        print(f"\n⚠️  Symbols with signals below threshold:")
        for r in results:
            if r['status'] == 'LOW_CONFIDENCE':
                print(f"  - {r['symbol']}: {r['signal']} ({r['confidence']*100:.1f}%) - {r['reason']}")
    
    print()


if __name__ == "__main__":
    asyncio.run(diagnose_symbols())
