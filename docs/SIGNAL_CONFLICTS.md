# Signal Conflict Prevention

## Problem

When analyzing multiple timeframes simultaneously (e.g., 5m, 15m, 1h, 4h), the bot can generate **conflicting signals** for the same symbol:

- **Lower timeframes (5m)** might detect short-term bullish momentum → **LONG signal**
- **Higher timeframes (15m)** might detect medium-term bearish momentum → **SHORT signal**

This can confuse traders and lead to poor decision-making.

## Example of Conflicting Signals

```
🔴 SHORT Signal: BNBUSDT 15m (Confidence: 81.0%)
🟢 LONG Signal:  BNBUSDT 5m  (Confidence: 78.0%)
```

Both signals were sent within seconds of each other, creating confusion about market direction.

---

## Solutions Implemented

### Solution 1: Reduce Timeframe Count (Recommended)

**Remove very short timeframes** (1m, 3m, 5m) that can conflict with longer timeframes.

**Recommended timeframes:**
```env
TIMEFRAMES=15m,1h,4h
```

This provides good coverage without too much noise:
- **15m**: Short-term trends (15-60 minutes)
- **1h**: Medium-term trends (1-4 hours)
- **4h**: Long-term trends (4-24 hours)

**Avoid:**
```env
TIMEFRAMES=5m,15m,1h,4h,1d  # Too many, causes conflicts
```

---

### Solution 2: Conflict Prevention System (NEW)

The bot now includes **automatic conflict prevention** that blocks opposite signals within 1 hour.

**How it works:**
1. When a **LONG signal** is generated for BTCUSDT, it's marked with a timestamp
2. If a **SHORT signal** is detected for BTCUSDT within the next **1 hour**, it's **blocked**
3. After 1 hour, opposite signals are allowed again (market may have changed)

**Configuration:**
```env
# Enable/disable conflict prevention
PREVENT_SIGNAL_CONFLICTS=true

# Default: blocks opposite signals within 1 hour (3600 seconds)
```

**Log output when conflict is detected:**
```
🚫 Conflicting signal blocked: SHORT BTCUSDT 5m 
   (last signal: LONG 12.3m ago). 
   Waiting 47.7m before allowing opposite signal.
```

---

## Configuration Examples

### Conservative (Fewer Signals, Higher Quality)
```env
SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT
TIMEFRAMES=1h,4h
MIN_CONFIDENCE=0.70
PREVENT_SIGNAL_CONFLICTS=true
```
- Only 2 timeframes (less noise)
- Higher confidence threshold (70%)
- Conflict prevention enabled

### Balanced (Recommended)
```env
SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,ADAUSDT
TIMEFRAMES=15m,1h,4h
MIN_CONFIDENCE=0.65
PREVENT_SIGNAL_CONFLICTS=true
```
- 3 timeframes (good coverage)
- Standard confidence (65%)
- Conflict prevention enabled

### Aggressive (More Signals, More Noise)
```env
SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,XRPUSDT,ADAUSDT,DOGEUSDT
TIMEFRAMES=5m,15m,1h,4h
MIN_CONFIDENCE=0.60
PREVENT_SIGNAL_CONFLICTS=true
```
- 4 timeframes including 5m (more signals)
- Lower confidence (60%)
- Conflict prevention **CRITICAL** here to reduce noise

---

## Technical Details

### Conflict Prevention Logic

**File:** `src/signals/fuse.py`

```python
# Track last signal type for each symbol: {symbol: (type, timestamp)}
self.last_signal_type: Dict[str, tuple] = {}

# Before generating signal, check for conflicts
if self.prevent_conflicts and symbol in self.last_signal_type:
    last_type, last_time = self.last_signal_type[symbol]
    time_since_last = now - last_time
    
    # Block if opposite signal within 1 hour (3600 seconds)
    if time_since_last < 3600 and last_type != signal["type"]:
        logger.warning(f"🚫 Conflicting signal blocked...")
        return None
```

### Cooldown vs Conflict Prevention

**Two separate systems:**

1. **Cooldown** (`SIGNAL_COOLDOWN=300`):
   - Prevents duplicate signals for **same symbol + timeframe**
   - Example: After BTCUSDT 1h LONG, no new BTCUSDT 1h signals for 5 minutes
   - Default: 300 seconds (5 minutes)

2. **Conflict Prevention** (`PREVENT_SIGNAL_CONFLICTS=true`):
   - Prevents **opposite signals** for **same symbol (any timeframe)**
   - Example: After BTCUSDT (any TF) LONG, no BTCUSDT SHORT for 1 hour
   - Default: 3600 seconds (1 hour)

---

## Recommendations

### For Live Trading
```env
TIMEFRAMES=15m,1h,4h
PREVENT_SIGNAL_CONFLICTS=true
MIN_CONFIDENCE=0.70
```
- Clear directional signals
- No conflicting messages
- Higher confidence for real money

### For Testing/Research
```env
TIMEFRAMES=5m,15m,1h,4h
PREVENT_SIGNAL_CONFLICTS=false
MIN_CONFIDENCE=0.60
```
- See all signals (including conflicts)
- Study multi-timeframe divergences
- Lower confidence to catch more patterns

### For High-Volume Servers
```env
TIMEFRAMES=1h,4h
PREVENT_SIGNAL_CONFLICTS=true
MIN_CONFIDENCE=0.75
```
- Fewer signals = less spam
- Only strong, clear signals
- Prevents Discord channel flooding

---

## Disabling Conflict Prevention

If you want to see **all signals** including conflicts (for research or testing):

```env
PREVENT_SIGNAL_CONFLICTS=false
```

**Use cases:**
- Studying multi-timeframe divergences
- Testing signal strategies
- Comparing timeframe effectiveness
- Educational purposes

**Not recommended for:**
- Live trading
- Public Discord channels (confusing for users)
- Production environments
