"""
Quick backtest script - Run this to test the strategy on historical data.

Usage:
    python run_backtest.py
    
    Or with custom parameters:
    python run_backtest.py --symbol ETHUSDT --timeframe 4h --days 60 --confidence 0.70
"""

import asyncio
import argparse
from datetime import datetime, timedelta

from src.backtest.engine import BacktestEngine, print_backtest_results
from src.ingest.binance_rest import BinanceRESTClient


async def run_backtest(
    symbol: str = 'BTCUSDT',
    timeframe: str = '1h',
    days: int = 90,
    min_confidence: float = 0.65,
    initial_balance: float = 10000.0,
    position_size: float = 0.02,
    allow_single_method: bool = False,
    single_method_confidence: float = 0.75,
):
    """
    Run a backtest on historical data.
    
    Args:
        symbol: Trading pair (e.g., BTCUSDT)
        timeframe: Candle timeframe (15m, 1h, 4h, 1d)
        days: Number of days to backtest
        min_confidence: Minimum signal confidence (0.0-1.0)
        initial_balance: Starting account balance
        position_size: Position size as % of balance
        allow_single_method: Allow single-method signals
        single_method_confidence: Min confidence for single-method
    """
    print("\n" + "="*70)
    print("WYCKOFF-ELLIOTT BACKTEST")
    print("="*70)
    print(f"Symbol:         {symbol}")
    print(f"Timeframe:      {timeframe}")
    print(f"Period:         Last {days} days")
    print(f"Min Confidence: {min_confidence}")
    if allow_single_method:
        print(f"Single-Method:  Enabled (min {single_method_confidence})")
    print(f"Initial Balance: ${initial_balance:,.2f}")
    print(f"Position Size:  {position_size*100:.1f}% per trade")
    print("="*70 + "\n")
    
    # Initialize Binance client
    print("📡 Connecting to Binance...")
    binance = BinanceRESTClient()
    
    # Calculate limit based on timeframe and days
    intervals_per_day = {
        '15m': 96,
        '1h': 24,
        '4h': 6,
        '1d': 1,
    }
    limit = min(intervals_per_day.get(timeframe, 24) * days, 1500)
    
    # Download historical data
    print(f"📊 Downloading {limit} candles for {symbol} {timeframe}...")
    try:
        candles = await binance.get_historical_klines(
            symbol=symbol,
            interval=timeframe,
            limit=limit,
        )
        print(f"✅ Loaded {len(candles)} candles")
    except Exception as e:
        print(f"❌ Failed to load data: {e}")
        await binance.close()
        return
    finally:
        # Always close the session
        await binance.close()
    
    if len(candles) < 50:
        print("❌ Not enough data for backtest (need at least 50 candles)")
        return
    
    # Show date range
    first_candle = datetime.fromtimestamp(candles[0]['open_time'] / 1000)
    last_candle = datetime.fromtimestamp(candles[-1]['open_time'] / 1000)
    print(f"📅 Data range: {first_candle.date()} to {last_candle.date()}\n")
    
    # Initialize backtest engine
    print("🔧 Initializing backtest engine...")
    engine = BacktestEngine(
        initial_balance=initial_balance,
        position_size_percent=position_size,
        commission=0.001,  # 0.1% commission
    )
    
    # Run backtest
    print("🚀 Running backtest...\n")
    results = await engine.run_backtest(
        candles=candles,
        symbol=symbol,
        timeframe=timeframe,
        enable_wyckoff=True,
        enable_elliott=True,
        min_confidence=min_confidence,
        allow_single_method=allow_single_method,
        single_method_confidence=single_method_confidence,
    )
    
    # Print results
    print_backtest_results(results)
    
    # Show sample trades
    if results['total_trades'] > 0:
        print("\n" + "="*70)
        print("SAMPLE TRADES (First 5)")
        print("="*70)
        trades = results['trades'][:5]
        
        for i, trade in enumerate(trades, 1):
            entry_time = datetime.fromtimestamp(trade['entry_time'] / 1000)
            pnl_symbol = "✅" if trade['pnl'] > 0 else "❌"
            
            print(f"\nTrade #{i} {pnl_symbol}")
            print(f"  Type:       {trade['type']}")
            print(f"  Entry Time: {entry_time}")
            print(f"  Entry:      ${trade['entry_price']:.4f}")
            print(f"  Exit:       ${trade['exit_price']:.4f}")
            print(f"  Exit Reason: {trade['exit_reason']}")
            print(f"  Confidence: {trade['confidence']:.2%}")
            print(f"  PnL:        ${trade['pnl']:.2f}")
        
        print("\n" + "="*70)
    
    # Provide recommendations
    print("\n💡 RECOMMENDATIONS:")
    
    if results['total_trades'] == 0:
        print("  ⚠️  No trades executed. Try:")
        print("     - Lower min_confidence (try 0.55 or 0.60)")
        print("     - Longer time period (try --days 120)")
        print("     - Different timeframe (try --timeframe 4h)")
    
    elif results['win_rate'] > 0.55 and results['total_pnl'] > 0:
        print("  ✅ Strategy shows promise!")
        print("     - Win rate is above 55%")
        print("     - Total PnL is positive")
        print("     Next steps:")
        print("       1. Test on different time periods")
        print("       2. Test on different symbols")
        print("       3. Run forward test (paper trading)")
    
    elif results['win_rate'] < 0.50 or results['total_pnl'] < 0:
        print("  ⚠️  Strategy needs improvement:")
        if results['win_rate'] < 0.50:
            print("     - Win rate below 50%")
            print("     - Consider raising min_confidence")
        if results['total_pnl'] < 0:
            print("     - Negative total PnL")
            print("     - Check if market conditions favor this strategy")
        print("     - Try different timeframes or symbols")
    
    print("\n✨ Backtest complete!\n")


def main():
    """Parse arguments and run backtest."""
    parser = argparse.ArgumentParser(
        description='Run Wyckoff-Elliott strategy backtest'
    )
    parser.add_argument(
        '--symbol',
        type=str,
        default='BTCUSDT',
        help='Trading symbol (default: BTCUSDT)'
    )
    parser.add_argument(
        '--timeframe',
        type=str,
        default='1h',
        choices=['15m', '1h', '4h', '1d'],
        help='Timeframe (default: 1h)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=90,
        help='Number of days to backtest (default: 90)'
    )
    parser.add_argument(
        '--confidence',
        type=float,
        default=0.65,
        help='Minimum signal confidence 0.0-1.0 (default: 0.65)'
    )
    parser.add_argument(
        '--balance',
        type=float,
        default=10000.0,
        help='Initial balance in USDT (default: 10000)'
    )
    parser.add_argument(
        '--position-size',
        type=float,
        default=0.02,
        help='Position size as decimal 0.0-1.0 (default: 0.02 = 2%%)'
    )
    parser.add_argument(
        '--allow-single',
        action='store_true',
        help='Allow single-method signals with high confidence (default: False)'
    )
    parser.add_argument(
        '--single-confidence',
        type=float,
        default=0.75,
        help='Min confidence for single-method signals (default: 0.75)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not 0 <= args.confidence <= 1:
        print("❌ Error: Confidence must be between 0.0 and 1.0")
        return
    
    if not 0 < args.position_size <= 1:
        print("❌ Error: Position size must be between 0.0 and 1.0")
        return
    
    # Run backtest
    try:
        asyncio.run(run_backtest(
            symbol=args.symbol,
            timeframe=args.timeframe,
            days=args.days,
            min_confidence=args.confidence,
            initial_balance=args.balance,
            position_size=args.position_size,
            allow_single_method=args.allow_single,
            single_method_confidence=args.single_confidence,
        ))
    except KeyboardInterrupt:
        print("\n\n⚠️  Backtest interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
