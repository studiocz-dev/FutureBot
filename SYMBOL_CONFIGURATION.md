# Trading Symbols Configuration Guide

## Current Configuration

**Your symbols:** (10 coins)
```env
SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,XRPUSDT,ADAUSDT,DOGEUSDT,DOTUSDT,AVAXUSDT,LINKUSDT
```

**Your timeframes:** (3 timeframes)
```env
TIMEFRAMES=15m,1h,4h
```

---

## How Symbols Work

### Signal Generation Formula

**Total WebSocket Streams = Symbols × Timeframes**

Your current setup:
- 10 symbols × 3 timeframes = **30 WebSocket connections**
- Each connection monitors one symbol-timeframe pair
- Bot analyzes each pair when a candle closes
- Generates signals based on Wyckoff + Elliott Wave analysis

### Why BNB Has More Signals

**Reasons:**
1. **Higher volatility** - BNB moves more, creating more patterns
2. **More volume** - Higher trading activity = clearer patterns
3. **Random distribution** - Signals depend on price action, not equal distribution
4. **Confidence threshold** - BNB might hit 65%+ confidence more often

**This is normal!** Some coins are more active than others.

---

## How Many Coins Can You Add?

### Technical Limits

**Binance Limits:**
- Max WebSocket connections: **200 streams per connection**
- You're using: 30 streams (10 symbols × 3 timeframes)
- **Remaining capacity: 170 streams** ✅

**Practical Limits:**

| Symbols | Timeframes | Total Streams | Status |
|---------|------------|---------------|--------|
| 10 | 3 | 30 | ✅ Current (light) |
| 20 | 3 | 60 | ✅ Good |
| 30 | 3 | 90 | ✅ Moderate |
| 50 | 3 | 150 | ⚠️ Heavy |
| 66 | 3 | 198 | ⚠️ Max (close to limit) |

**Recommended maximum: 30-50 symbols** with 3 timeframes

### System Resource Limits

**Memory Usage:**
- Each stream: ~2-5 MB
- 30 streams: ~100-150 MB
- 100 streams: ~300-500 MB

**CPU Usage:**
- Each candle close triggers analysis
- With 3 timeframes, candles close at:
  - 15m: every 15 minutes
  - 1h: every hour
  - 4h: every 4 hours
- More symbols = more simultaneous analyses

**Database:**
- Each candle stored in Supabase
- 30 streams × 500 candles each = 15,000 candles
- 100 streams × 500 candles = 50,000 candles
- Supabase free tier: **500 MB** (plenty for candles)

---

## Popular Coins to Add

### Top Market Cap (Safe/Stable)
```env
# Add these to SYMBOLS:
BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,XRPUSDT,ADAUSDT,AVAXUSDT,DOGEUSDT,DOTUSDT,LINKUSDT,
MATICUSDT,UNIUSDT,LTCUSDT,ATOMUSDT,ETCUSDT,XLMUSDT,ALGOUSDT,VETUSDT
```

### High Volatility (More Signals, Higher Risk)
```env
# Add these for more frequent signals:
SHIBUSDT,PEPEUSDT,FLOKIUSDT,SANDUSDT,MANAUSDT,GALAUSDT,CHZUSDT
```

### DeFi Coins
```env
# DeFi protocols:
AAVEUSDT,MKRUSDT,COMPUSDT,CRVUSDT,SNXUSDT,YFIUSDT
```

### Layer 1 Blockchains
```env
# Alternative L1s:
NEARUSDT,APTUSDT,SUIUSDT,INJUSDT,SEIUSDT,TIAUSDT
```

### Meme Coins (Very Volatile)
```env
# High risk, high volatility:
SHIBUSDT,DOGEUSDT,PEPEUSDT,FLOKIUSDT,WIFUSDT,BONKUSDT
```

---

## How to Add More Symbols

### Step 1: Check Available Symbols on Binance Futures

**Valid format:** Must end with `USDT`

**Verify symbol exists:**
```python
# Test if symbol works
import requests
symbol = "ARBUSDT"
url = f"https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={symbol}"
response = requests.get(url)
if response.status_code == 200:
    print(f"✅ {symbol} is valid")
else:
    print(f"❌ {symbol} not found")
```

### Step 2: Update .env File

**Edit `SYMBOLS` line:**
```env
# Before (10 coins):
SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,XRPUSDT,ADAUSDT,DOGEUSDT,DOTUSDT,AVAXUSDT,LINKUSDT

# After (20 coins) - Example:
SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,XRPUSDT,ADAUSDT,DOGEUSDT,DOTUSDT,AVAXUSDT,LINKUSDT,MATICUSDT,UNIUSDT,LTCUSDT,ATOMUSDT,SANDUSDT,MANAUSDT,AAVEUSDT,NEARUSDT,ARBUSDT,OPUSDT
```

**Rules:**
- ✅ Comma-separated, no spaces
- ✅ All caps
- ✅ Must end with USDT
- ✅ No line breaks in the middle

### Step 3: Restart Bot

```bash
# Stop bot (if running)
Ctrl + C

# Or use stop script
.\stop_bot.bat

# Start bot with new symbols
python start.py
# Or
.\start_bot.bat
```

### Step 4: Verify

**Check logs for:**
```
INFO - Symbols: ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', ...]
INFO - Connecting to Binance WebSocket with 60 streams...
INFO - Downloading 500 candles for ARBUSDT 15m
```

**In Discord, test:**
```
>signal ARB
>signal OP 1h
>signals 10
```

---

## Recommended Configurations

### Conservative (Low Resource Usage)
**10-15 symbols, 3 timeframes = 30-45 streams**
```env
SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,XRPUSDT,ADAUSDT,AVAXUSDT,DOGEUSDT,DOTUSDT,LINKUSDT,MATICUSDT,UNIUSDT,LTCUSDT,ATOMUSDT,ARBUSDT
TIMEFRAMES=15m,1h,4h
```
- Good coverage of major coins
- Low system resources
- Fewer signals (higher quality)

---

### Balanced (Recommended)
**20-25 symbols, 3 timeframes = 60-75 streams**
```env
SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,XRPUSDT,ADAUSDT,AVAXUSDT,DOGEUSDT,DOTUSDT,LINKUSDT,MATICUSDT,UNIUSDT,LTCUSDT,ATOMUSDT,ARBUSDT,OPUSDT,SANDUSDT,MANAUSDT,AAVEUSDT,NEARUSDT,APTUSDT,SHIBUSDT,PEPEUSDT,INJUSDT,TIAUSDT
TIMEFRAMES=15m,1h,4h
```
- Great variety
- Moderate system resources
- Good signal frequency
- Mix of stable and volatile coins

---

### Aggressive (Maximum Coverage)
**40-50 symbols, 3 timeframes = 120-150 streams**
```env
SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,XRPUSDT,ADAUSDT,AVAXUSDT,DOGEUSDT,DOTUSDT,LINKUSDT,MATICUSDT,UNIUSDT,LTCUSDT,ATOMUSDT,ARBUSDT,OPUSDT,SANDUSDT,MANAUSDT,AAVEUSDT,NEARUSDT,APTUSDT,SHIBUSDT,PEPEUSDT,INJUSDT,TIAUSDT,SUIUSDT,SEIUSDT,COMPUSDT,MKRUSDT,CRVUSDT,SNXUSDT,YFIUSDT,ALGOUSDT,VETUSDT,FLOKIUSDT,GALAUSDT,CHZUSDT,XLMUSDT,ETCUSDT,TRXUSDT,FILUSDT,ICPUSDT,RNDRUSDT,WLDUSDT,STXUSDT,IMXUSDT,APTOSUSDT,LDOUSDT,FTMUSDT,KAVAUSDT
TIMEFRAMES=15m,1h,4h
```
- Maximum coin coverage
- High system resources (500+ MB RAM)
- Many signals per day
- Requires good server specs

---

## Why Some Coins Get More Signals

### Signal Generation Factors

**1. Volatility**
- Higher price movement = more patterns
- BNB, DOGE, SHIB = very volatile
- BTC, ETH = less volatile (but bigger moves)

**2. Volume**
- Higher volume = clearer patterns
- More trades = better price discovery
- Top 10 coins usually have highest volume

**3. Trend Strength**
- Strong trends = more Elliott Wave patterns
- Range-bound = fewer signals
- Trending coins get more signals

**4. Confidence Threshold**
- Your MIN_CONFIDENCE: 65%
- Some coins hit this threshold more often
- Lower threshold = more signals (but lower quality)

**5. Cooldown Period**
- After a signal, that symbol/timeframe has 5-minute cooldown
- Prevents duplicate signals
- Limits signals per symbol

**6. Conflict Prevention**
- After LONG signal, no SHORT for 1 hour
- Vice versa
- Reduces whipsaw signals

### Expected Signal Distribution

**With 10 symbols:**
- Active coins (BNB, DOGE): 2-5 signals/day
- Stable coins (BTC, ETH): 1-2 signals/day
- Quiet coins (DOT, LINK): 0-1 signals/day

**With 25 symbols:**
- Total: 10-30 signals/day
- Not evenly distributed
- 80% of signals from 20% of coins (Pareto principle)

---

## Performance Considerations

### System Requirements by Symbol Count

| Symbols | Streams | RAM Usage | CPU | Signal Frequency |
|---------|---------|-----------|-----|------------------|
| 10 | 30 | 100 MB | Low | 5-15 signals/day |
| 20 | 60 | 200 MB | Low-Med | 10-30 signals/day |
| 30 | 90 | 300 MB | Medium | 15-45 signals/day |
| 50 | 150 | 500 MB | Med-High | 25-75 signals/day |

### Discord Rate Limits

**Important:** Discord has rate limits for messages

- Max 5 messages per 5 seconds per channel
- Max 50 messages per minute per channel

**If you have too many symbols:**
- Bot might hit rate limits
- Messages get delayed
- Some signals might not show

**Solution:** Use multiple channels or reduce symbols

---

## Testing New Symbols

### Quick Test Script

Create `test_symbol.py`:
```python
import requests

def test_binance_symbol(symbol):
    """Test if symbol exists on Binance Futures."""
    if not symbol.endswith("USDT"):
        symbol = f"{symbol}USDT"
    
    url = f"https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={symbol}"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {symbol}")
            print(f"   Price: ${float(data['lastPrice']):,.4f}")
            print(f"   24h Change: {float(data['priceChangePercent']):.2f}%")
            print(f"   24h Volume: ${float(data['quoteVolume']):,.0f}")
            return True
        else:
            print(f"❌ {symbol} - Not found")
            return False
    except Exception as e:
        print(f"❌ {symbol} - Error: {e}")
        return False

# Test symbols
symbols = ["BTC", "ETH", "ARB", "OP", "MATIC", "PEPE"]
for sym in symbols:
    test_binance_symbol(sym)
    print()
```

**Run:**
```bash
python test_symbol.py
```

---

## Best Practices

### ✅ Do:
1. **Start small** - Add 5-10 coins at a time
2. **Test first** - Verify symbols exist on Binance
3. **Monitor resources** - Check RAM/CPU usage
4. **Watch signal quality** - Too many symbols = noise
5. **Use top coins** - Higher volume = better signals

### ❌ Don't:
1. **Add 100 coins at once** - System overload
2. **Add low-volume coins** - Poor signal quality
3. **Forget to restart bot** - Changes need restart
4. **Use spot symbols** - Must be Futures (USDT perpetuals)
5. **Add symbols without testing** - Might not exist

---

## Troubleshooting

### Symbol Not Working

**Error:** `KeyError: 'XXXUSDT'`

**Solutions:**
1. Check if symbol exists: `https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=XXXUSDT`
2. Use correct format: `XXXUSDT` not `XXX-USDT` or `XXX/USDT`
3. Must be Futures symbol, not Spot

### Too Many Signals

**Problem:** Getting 100+ signals per day

**Solutions:**
1. Increase `MIN_CONFIDENCE` from 0.65 to 0.70 or 0.75
2. Reduce number of symbols
3. Reduce timeframes (remove 15m)
4. Enable `PREVENT_SIGNAL_CONFLICTS=true`

### Not Enough Signals

**Problem:** Getting 0-2 signals per day

**Solutions:**
1. Lower `MIN_CONFIDENCE` from 0.65 to 0.60
2. Add more symbols (especially volatile ones)
3. Add more timeframes (add 15m or 1d)
4. Check if bot is actually running

### High Memory Usage

**Problem:** Bot using >1 GB RAM

**Solutions:**
1. Reduce symbols (aim for <50)
2. Reduce `window_size` in CandleAggregator (default: 500)
3. Reduce historical data fetch (default: 500 candles)

---

## Quick Reference

### Current Setup
```
Symbols: 10
Timeframes: 3
Total Streams: 30
Expected Signals: 5-15 per day
RAM Usage: ~100-150 MB
```

### To Add More Coins

**Edit `.env`:**
```env
SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT,NEWCOINUSDT,ANOTHERCOINUSDT
```

**Restart bot:**
```bash
.\stop_bot.bat
.\start_bot.bat
```

**Verify in logs:**
```
INFO - Symbols: ['BTCUSDT', 'ETHUSDT', ...]
INFO - Connecting to Binance WebSocket with XX streams...
```

---

## Summary

✅ **Current:** 10 symbols × 3 timeframes = 30 streams
✅ **Binance Limit:** 200 streams max
✅ **Recommended:** 20-30 symbols for balanced performance
✅ **Maximum practical:** 50-60 symbols
✅ **Signal distribution:** Normal for some coins to get more signals
✅ **BNB active:** Expected - high volatility coin

**You can safely add 10-20 more coins!**
