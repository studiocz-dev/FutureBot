"""
Analyze bot log files for signal performance and issues.

Usage:
    python analyze_logs.py logs/bot_20251024.log
"""

import json
import sys
from datetime import datetime
from collections import defaultdict
from pathlib import Path


def analyze_log_file(log_file_path):
    """Analyze a bot log file."""
    
    signals = []
    errors = []
    warnings = []
    candle_closes = []
    
    symbol_counts = defaultdict(int)
    signal_types = defaultdict(int)
    confidence_levels = []
    
    print(f"\n📊 Analyzing log file: {log_file_path}\n")
    print("=" * 80)
    
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    entry = json.loads(line.strip())
                    
                    level = entry.get('level', '')
                    message = entry.get('message', '')
                    
                    # Track errors and warnings
                    if level == 'ERROR':
                        errors.append(entry)
                    elif level == 'WARNING':
                        warnings.append(entry)
                    
                    # Track signals
                    if entry.get('signal_type'):
                        signals.append(entry)
                        symbol = entry.get('symbol', 'UNKNOWN')
                        signal_type = entry.get('signal_type', 'UNKNOWN')
                        confidence = entry.get('confidence', 0)
                        
                        symbol_counts[symbol] += 1
                        signal_types[signal_type] += 1
                        confidence_levels.append(confidence)
                    
                    # Track candle closes
                    if 'Candle closed' in message:
                        candle_closes.append(entry)
                
                except json.JSONDecodeError as e:
                    print(f"⚠️  Line {line_num}: Invalid JSON - {e}")
                    continue
        
        # Print statistics
        print(f"\n📈 SIGNAL STATISTICS")
        print("-" * 80)
        print(f"Total Signals Generated: {len(signals)}")
        
        if signals:
            print(f"\n📍 Signals by Type:")
            for sig_type, count in sorted(signal_types.items()):
                print(f"  • {sig_type}: {count}")
            
            print(f"\n🎯 Signals by Symbol:")
            for symbol, count in sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  • {symbol}: {count}")
            
            if confidence_levels:
                avg_conf = sum(confidence_levels) / len(confidence_levels)
                min_conf = min(confidence_levels)
                max_conf = max(confidence_levels)
                print(f"\n📊 Confidence Levels:")
                print(f"  • Average: {avg_conf:.1%}")
                print(f"  • Min: {min_conf:.1%}")
                print(f"  • Max: {max_conf:.1%}")
        
        # Print detailed signal list
        if signals:
            print(f"\n📝 DETAILED SIGNALS")
            print("-" * 80)
            for idx, sig in enumerate(signals, 1):
                timestamp = sig.get('timestamp', 'N/A')
                symbol = sig.get('symbol', 'N/A')
                sig_type = sig.get('signal_type', 'N/A')
                conf = sig.get('confidence', 0)
                
                print(f"{idx}. [{timestamp}] {sig_type} {symbol} - Confidence: {conf:.1%}")
                print(f"   Message: {sig.get('message', 'N/A')}")
        
        # Print errors and warnings
        print(f"\n⚠️  ERRORS AND WARNINGS")
        print("-" * 80)
        print(f"Total Errors: {len(errors)}")
        print(f"Total Warnings: {len(warnings)}")
        
        if errors:
            print(f"\n🔴 Recent Errors (last 10):")
            for err in errors[-10:]:
                print(f"  • [{err.get('timestamp')}] {err.get('message')}")
                if err.get('exception'):
                    print(f"    Exception: {err['exception'][:200]}...")
        
        if warnings:
            print(f"\n🟡 Recent Warnings (last 10):")
            for warn in warnings[-10:]:
                print(f"  • [{warn.get('timestamp')}] {warn.get('message')}")
        
        # Candle processing stats
        print(f"\n🕒 CANDLE PROCESSING")
        print("-" * 80)
        print(f"Total Candle Closes: {len(candle_closes)}")
        
        # Check for issues
        print(f"\n🔍 POTENTIAL ISSUES")
        print("-" * 80)
        
        issues_found = False
        
        if len(signals) == 0:
            print("  ❌ NO SIGNALS GENERATED - Check confidence threshold and analysis logic")
            issues_found = True
        
        if len(errors) > 10:
            print(f"  ⚠️  HIGH ERROR COUNT ({len(errors)}) - Check error messages above")
            issues_found = True
        
        if len(candle_closes) < 10:
            print(f"  ⚠️  FEW CANDLE CLOSES ({len(candle_closes)}) - Bot may not be receiving data")
            issues_found = True
        
        if signals and len(set(symbol_counts.keys())) < 5:
            print(f"  ⚠️  LIMITED SYMBOL COVERAGE ({len(set(symbol_counts.keys()))} symbols) - Expected ~20 symbols")
            issues_found = True
        
        if not issues_found:
            print("  ✅ No obvious issues detected")
        
        print("\n" + "=" * 80)
        print("Analysis complete!\n")
    
    except FileNotFoundError:
        print(f"❌ Error: File not found: {log_file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error analyzing log file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_logs.py <log_file_path>")
        print("Example: python analyze_logs.py logs/bot_20251024.log")
        sys.exit(1)
    
    log_file = sys.argv[1]
    analyze_log_file(log_file)
