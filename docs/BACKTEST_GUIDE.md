# How Backtesting Works

## 📖 Overview

The backtesting system allows you to test the Wyckoff-Elliott signal strategy on **historical data** to see how it would have performed in the past. This helps you:

- Understand signal quality and frequency
- Optimize confidence thresholds
- Estimate potential win rates and profitability
- Validate the strategy before live trading

---

## 🎯 How It Works

### Step-by-Step Process:

```
1. Load Historical Data
   ↓
2. Initialize with Starting Balance ($10,000 default)
   ↓
3. Loop Through Each Candle (from past to present)
   ├─ Analyze candles up to current point
   ├─ Run Wyckoff + Elliott Wave analysis
   ├─ Generate signal if pattern detected
   ├─ Open position if signal confidence > threshold
   ├─ Track position until TP or SL hit
   └─ Record trade results
   ↓
4. Calculate Statistics
   ├─ Win rate
   ├─ Total PnL
   ├─ Max drawdown
   └─ Trade distribution
   ↓
5. Visualize Results
```

---

## 💰 Trading Simulation

### Position Sizing
- **Default:** 2% of account balance per trade
- **Example:** With $10,000 balance, each trade uses $200

### Commission
- **Default:** 0.1% per trade (entry + exit = 0.2% total)
- **Realistic for Binance Futures taker fees**

### Exit Conditions

A position is closed when:

1. **Take Profit (TP) Hit** ✅
   - Price reaches calculated TP level
   - Marks trade as WIN

2. **Stop Loss (SL) Hit** ❌
   - Price reaches calculated SL level
   - Marks trade as LOSS

3. **End of Data** ⏹️
   - Backtest period ends with open position
   - Closes at final price

---

## 📊 Example Backtest Run

### Configuration:
```python
engine = BacktestEngine(
    initial_balance=10000.0,      # Start with $10k
    position_size_percent=0.02,   # Use 2% per trade
    commission=0.001               # 0.1% fee
)

results = await engine.run_backtest(
    candles=candles,               # 90 days of BTC 1h data
    symbol='BTCUSDT',
    timeframe='1h',
    enable_wyckoff=True,           # Use Wyckoff analysis
    enable_elliott=True,           # Use Elliott Wave analysis
    min_confidence=0.65            # Only take 65%+ confidence signals
)
```

### Sample Output:
```
==============================================================
BACKTEST RESULTS
==============================================================
Total Trades:      45
Winning Trades:    28
Losing Trades:     17
Win Rate:          62.22%
Total PnL:         $1,245.67 (12.46%)
Average Win:       $85.34
Average Loss:      -$42.18
Largest Win:       $245.89
Largest Loss:      -$98.45
Max Drawdown:      8.34%
Final Balance:     $11,245.67
==============================================================
```

---

## 📈 What Gets Analyzed

### 1. Wyckoff Method
- **Accumulation phases** → LONG signals
- **Distribution phases** → SHORT signals
- **Springs** (failed breakdowns) → Bullish
- **Upthrusts** (failed breakouts) → Bearish

### 2. Elliott Wave
- **Wave 5 completion** (impulse) → Reversal signal
- **Wave C completion** (correction) → Trend resumption
- **Fibonacci ratios** for validation

### 3. Signal Fusion
- Both methods must **agree** on direction, OR
- One method must have **>75% confidence**
- Combined confidence must meet `min_confidence` threshold

---

## 📝 How to Run a Backtest

### Option 1: Jupyter Notebook (Recommended)

1. Open `src/backtest/sample_notebook.ipynb` in VS Code
2. Run cells in order:
   - Load historical data from Binance
   - Visualize price chart
   - Run backtest
   - See equity curve and trade distribution

### Option 2: Python Script

```python
import asyncio
from src.backtest.engine import BacktestEngine, print_backtest_results
from src.ingest.binance_rest import BinanceRESTClient

async def run_backtest():
    # Load historical data
    binance = BinanceRESTClient()
    candles = await binance.get_historical_klines(
        symbol='BTCUSDT',
        interval='1h',
        limit=1500  # Last 1500 hours (~62 days)
    )
    
    # Initialize backtest engine
    engine = BacktestEngine(
        initial_balance=10000.0,
        position_size_percent=0.02,
        commission=0.001
    )
    
    # Run backtest
    results = await engine.run_backtest(
        candles=candles,
        symbol='BTCUSDT',
        timeframe='1h',
        enable_wyckoff=True,
        enable_elliott=True,
        min_confidence=0.65
    )
    
    # Print results
    print_backtest_results(results)
    
    # Access individual trades
    for trade in results['trades']:
        print(f"{trade['type']} @ {trade['entry_price']:.2f} → "
              f"{trade['exit_price']:.2f} ({trade['exit_reason']}): "
              f"${trade['pnl']:.2f}")

asyncio.run(run_backtest())
```

---

## 🔧 Parameter Optimization

Test different settings to find optimal configuration:

```python
# Test multiple confidence levels
confidence_levels = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75]

for conf in confidence_levels:
    results = await engine.run_backtest(
        candles=candles,
        symbol='BTCUSDT',
        timeframe='1h',
        min_confidence=conf
    )
    
    print(f"Confidence {conf:.2f}: "
          f"{results['total_trades']} trades, "
          f"{results['win_rate']:.2%} win rate, "
          f"{results['total_pnl_percent']:.2f}% return")
```

**Example Output:**
```
Confidence 0.50: 78 trades, 58.97% win rate, 8.34% return
Confidence 0.55: 62 trades, 61.29% win rate, 10.12% return
Confidence 0.60: 51 trades, 62.75% win rate, 11.45% return
Confidence 0.65: 45 trades, 62.22% win rate, 12.46% return  ← Sweet spot
Confidence 0.70: 32 trades, 65.63% win rate, 9.87% return
Confidence 0.75: 18 trades, 72.22% win rate, 6.23% return
```

---

## 📊 Key Metrics Explained

### Win Rate
- **Formula:** `Winning Trades / Total Trades`
- **Good:** >55%
- **Excellent:** >60%

### Total PnL %
- **Formula:** `(Final Balance - Initial Balance) / Initial Balance × 100`
- **Target:** Positive return after commissions

### Max Drawdown
- **Definition:** Largest peak-to-trough decline in account value
- **Important:** Lower is better (means less risk)
- **Target:** <15% for conservative strategies

### Average Win vs Average Loss
- **Profit Factor:** `Avg Win / |Avg Loss|`
- **Good:** >1.5 (wins are 50% larger than losses)
- **Excellent:** >2.0

### Sharpe Ratio (coming soon)
- Measures risk-adjusted returns
- Higher is better

---

## ⚠️ Important Limitations

### 1. Perfect Execution Assumption
- Backtest assumes **instant fills** at TP/SL prices
- Real trading has **slippage** and **partial fills**

### 2. No Order Book Simulation
- Doesn't account for liquidity
- Assumes you can always enter/exit at exact prices

### 3. Survivorship Bias
- Only tests on symbols that still exist
- Doesn't account for delisted coins

### 4. Look-Ahead Bias (Avoided)
- Backtest only uses data **available at that moment**
- Doesn't "peek" into future candles

### 5. Overfitting Risk
- Optimizing too much on historical data
- May not work on future data

---

## 🎯 How to Use Results

### If Backtest Shows Good Results:
- ✅ Win rate >55%
- ✅ Consistent profits
- ✅ Drawdown <15%

**Next Steps:**
1. Test on **different time periods** (bull market, bear market, sideways)
2. Test on **different symbols** (ETH, BNB, SOL)
3. Test on **different timeframes** (15m, 1h, 4h)
4. Run **forward test** (paper trading) for 1-2 weeks
5. If still good → Consider live trading with **small position sizes**

### If Backtest Shows Poor Results:
- ❌ Win rate <50%
- ❌ Negative returns
- ❌ Large drawdowns

**Next Steps:**
1. **Lower confidence threshold** (more trades, but lower quality)
2. **Adjust stop-loss/take-profit** multipliers
3. **Try different timeframes** (maybe 4h works better than 1h)
4. **Check if market regime changed** (strategy may work only in certain conditions)

---

## 🚀 Running Your First Backtest

### Quick Start:

```powershell
# 1. Activate virtual environment
.\venv\Scripts\Activate.ps1

# 2. Start Jupyter (if using notebook)
jupyter notebook

# 3. Open sample_notebook.ipynb
# Navigate to src/backtest/sample_notebook.ipynb

# 4. Run all cells (Shift+Enter on each cell)
```

### Or use VS Code:

1. Open `src/backtest/sample_notebook.ipynb` in VS Code
2. Select Python kernel (your venv)
3. Click "Run All" at the top
4. See results and charts!

---

## 📚 Advanced Usage

### Test Multiple Symbols
```python
symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']

for symbol in symbols:
    candles = await binance.get_historical_klines(symbol, '1h', limit=1500)
    results = await engine.run_backtest(candles, symbol, '1h')
    print(f"\n{symbol}: {results['total_pnl_percent']:.2f}% return")
```

### Walk-Forward Analysis
```python
# Test on Q1, optimize on Q2, test on Q3, etc.
# Prevents overfitting by using out-of-sample data
```

### Monte Carlo Simulation
```python
# Randomize trade order to assess robustness
# Check if results hold across different sequences
```

---

## 📞 Need Help?

- **Example notebook:** `src/backtest/sample_notebook.ipynb`
- **Engine code:** `src/backtest/engine.py`
- **Documentation:** `docs/ARCHITECTURE.md`

---

**Remember:** Past performance does NOT guarantee future results. Backtest is for educational purposes and strategy validation only! 🎓
