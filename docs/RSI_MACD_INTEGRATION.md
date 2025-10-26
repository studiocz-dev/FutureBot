# RSI + MACD Integration - Multi-Tier Signal Fusion

## Overview

The bot now uses **4 analysis methods** combined in a sophisticated fusion system:

1. **Wyckoff Method** - Accumulation/Distribution patterns, Springs/Upthrusts
2. **Elliott Wave** - 5-wave structures, Fibonacci relationships  
3. **RSI (Relative Strength Index)** - Oversold/Overbought momentum
4. **MACD (Moving Average Convergence Divergence)** - Trend changes & crossovers

## Multi-Tier Fusion Logic

### TIER 1: Highest Confidence (75-95%)
**Wyckoff + Elliott Agreement**
- Both pattern analyzers signal same direction
- Base confidence = average of both
- +5% bonus if RSI confirms
- +5% bonus if MACD confirms
- **Example:** Wyckoff LONG (70%) + Elliott LONG (75%) + RSI LONG = **82.5%** confidence

### TIER 2: Medium-High Confidence (65-80%)
**One Pattern + Both Indicators**
- Either Wyckoff OR Elliott signals
- Both RSI and MACD confirm same direction
- Base confidence = average of all three
- **Example:** Elliott SHORT (70%) + RSI SHORT (65%) + MACD SHORT (60%) = **65%** confidence

### TIER 3: Medium Confidence (55-70%)
**RSI + MACD Agreement**
- No pattern analyzers signal
- RSI and MACD both agree on direction
- Base confidence = average of both
- **Example:** RSI LONG (60%) + MACD LONG (65%) = **62.5%** confidence

### TIER 4: Lower Confidence (68-75%)
**Strong Single Pattern**
- Wyckoff alone with >75% confidence
- OR Elliott alone with >75% confidence
- 10% penalty for lack of confirmation
- **Example:** Wyckoff LONG (80%) alone = **72%** confidence

### Rejection Cases
- Pattern analyzers disagree (Wyckoff LONG vs Elliott SHORT)
- Only one indicator signals (no confirmation)
- All confidences below thresholds

## Individual Analyzer Behavior

### RSI Analyzer
**Parameters:**
- Period: 14 candles
- Oversold: <30
- Overbought: >70

**Signals:**
- RSI < 30 → **LONG** (oversold, expect bounce)
- RSI > 70 → **SHORT** (overbought, expect pullback)

**Confidence Formula:**
```python
# For oversold (RSI < 30)
confidence = (30 - current_rsi) / 30 + 0.5
# Example: RSI=20 → (30-20)/30 + 0.5 = 0.833 (83.3%)
# Example: RSI=28 → (30-28)/30 + 0.5 = 0.567 (56.7%)

# For overbought (RSI > 70)
confidence = (current_rsi - 70) / (100 - 70) + 0.5
# Example: RSI=80 → (80-70)/30 + 0.5 = 0.833 (83.3%)
# Example: RSI=72 → (72-70)/30 + 0.5 = 0.567 (56.7%)
```

### MACD Analyzer
**Parameters:**
- Fast EMA: 12 periods
- Slow EMA: 26 periods
- Signal Line: 9-period EMA of MACD

**Signals:**
- MACD crosses **above** Signal → **LONG** (bullish crossover)
- MACD crosses **below** Signal → **SHORT** (bearish crossover)

**Confidence Formula:**
```python
base = 0.5  # 50% starting point
histogram_strength = min(abs(histogram) * 100, 0.4)  # Up to 40%
zero_line_bonus = 0.2 if MACD > 0 else 0.1  # 20% if positive MACD, 10% if negative
confidence = base + histogram_strength + zero_line_bonus
# Strong bullish crossover: 0.5 + 0.4 + 0.2 = 1.1 → capped at 1.0 (100%)
# Weak bearish crossover: 0.5 + 0.1 + 0.1 = 0.7 (70%)
```

### Wyckoff Analyzer (Updated)
**Changes:**
- Minimum confidence lowered from 0.5 → **0.35**
- More springs and upthrusts will now qualify as signals

**Requirements:**
- Spring (LONG): Break below support + recover with volume + ACCUMULATION phase
- Upthrust (SHORT): Break above resistance + fail with volume + DISTRIBUTION phase
- Confidence ≥35% (was 50%)

### Elliott Wave Analyzer
**No changes** - still requires ≥5 pivot points for valid wave count

## 15m Timeframe Benefits

### Why 15m > 5m?
| Aspect | 5m | 15m |
|--------|-----|-----|
| **Noise** | Very high | Moderate |
| **Pattern Clarity** | Poor | Good |
| **Wyckoff Springs** | Rare (false breakouts) | Clear & reliable |
| **Elliott Waves** | 2-3 pivots (insufficient) | 5-8 pivots (valid structures) |
| **RSI Extremes** | Frequent but false | Meaningful reversals |
| **MACD Crossovers** | Many whipsaws | Strong trend changes |
| **Hold Duration** | 4-12 hours | 4-24 hours |
| **Target %** | 0.8-1.5% | 1-3% |

### Expected Signal Frequency
- **With Wyckoff + Elliott only:** 0-2 signals/week (too rare)
- **With RSI + MACD added:** 5-10 signals/day (reliable patterns)

### Signal Quality Distribution
- **TIER 1 (Wyckoff+Elliott):** ~10% of signals, 75-95% confidence
- **TIER 2 (Pattern+Indicators):** ~30% of signals, 65-80% confidence
- **TIER 3 (RSI+MACD):** ~60% of signals, 55-70% confidence

## Configuration Changes

### .env Updates
```bash
# Old 5m configuration
TIMEFRAMES=5m
STARTUP_CANDLES=6000
ANALYSIS_CANDLES=3000
MIN_CANDLES=300
ATR_STOP_LOSS_MULTIPLIER=1.5
ATR_TAKE_PROFIT_MULTIPLIER=2.0

# New 15m configuration
TIMEFRAMES=15m
STARTUP_CANDLES=2000    # 21 days
ANALYSIS_CANDLES=1000   # 10 days
MIN_CANDLES=100         # 1 day
ENABLE_RSI=true         # NEW
ENABLE_MACD=true        # NEW
ATR_STOP_LOSS_MULTIPLIER=2.0    # Standard swing
ATR_TAKE_PROFIT_MULTIPLIER=3.0   # Standard swing
```

## Migration Steps

### For Local Development:
1. Update `.env` with new 15m configuration
2. Clean database: `python clean_database.py --all --days=0`
3. Restart bot - it will load 2000 candles (15m) per symbol

### For Server Deployment:
1. **Commit and push** changes to GitHub
2. **SSH to server** and update `.env` manually:
   ```bash
   nano .env
   # Change TIMEFRAMES=5m → TIMEFRAMES=15m
   # Change STARTUP_CANDLES=6000 → STARTUP_CANDLES=2000
   # Change ANALYSIS_CANDLES=3000 → ANALYSIS_CANDLES=1000
   # Change MIN_CANDLES=300 → MIN_CANDLES=100
   # Add ENABLE_RSI=true
   # Add ENABLE_MACD=true
   # Change ATR multipliers to 2.0 and 3.0
   ```
3. **Clean database:**
   ```bash
   python clean_database.py --all --days=0
   ```
4. **Restart bot:**
   ```bash
   pm2 restart futurebot
   pm2 logs futurebot
   ```

## Monitoring

### What to Watch:
- **Signal frequency:** Should see 5-10 signals/day
- **Tier distribution:** Mix of TIER 1/2/3 signals
- **Confidence range:** Mostly 60-85%
- **Win rate target:** ≥55% (TIER 1/2 should be higher)

### Log Examples:
```bash
🔍 Analyzing BTCUSDT 15m @ $67500.0000
  📊 Wyckoff: LONG (45.2%)
  🌊 Elliott: NONE (0.0%)
  📈 RSI: LONG (68.5%) [RSI=28.3]
  📉 MACD: LONG (72.1%) [Hist=12.5670]
  ✓ TIER 3 Fusion: RSI+MACD agree on LONG (conf: 70.3%)
  🚀 SIGNAL SENT TO DISCORD
```

## Rollback Plan

If 15m doesn't perform well, revert to 5m:
```bash
git checkout swing-trading-backup
# Or manually change .env back to 5m settings
python clean_database.py --all --days=0
# Restart bot
```

## Performance Expectations

### Realistic Goals (15m + RSI/MACD):
- **Signals per day:** 5-10 quality signals
- **Symbols covered:** 10-15 different symbols/day
- **Average confidence:** 65-75%
- **Win rate target:** 55-65%
- **Average gain:** 1.5-2.5% per winner
- **Average loss:** -1.0% per loser
- **Risk/Reward:** 1:2 to 1:3

### Why This Works:
1. **Pattern analyzers** catch major turning points (high quality, rare)
2. **Technical indicators** catch momentum shifts (good quality, frequent)
3. **Fusion system** ensures confirmation before signaling
4. **15m timeframe** filters out noise while keeping responsiveness

