# Timeframe Cleanup Guide

**Last Updated:** October 24, 2025  
**Bot Version:** FutureBot v1.0

---

## Why You Have Multiple Timeframes in Your Database

If you're seeing candles with timeframes like **5m, 1h, 4h, 1d** in your Supabase database, even though your `.env` is configured for `TIMEFRAMES=15m` only, here's what happened:

### The Situation

1. **Previously:** Your bot was running with multiple timeframes (e.g., `TIMEFRAMES=15m,1h,4h`)
2. **Database:** Collected candles for ALL configured timeframes
3. **Configuration Change:** You updated `.env` to only use `TIMEFRAMES=15m`
4. **Problem:** Old timeframe data (5m, 1h, 4h, 1d) is still in database from previous runs

### Why `>cleanup` Didn't Remove Them

The `>cleanup confirm` command deletes candles **older than 30 days**, NOT candles from unwanted timeframes.

- ✅ Deleted: 7,903 candles older than 30 days (any timeframe)
- ❌ Kept: Recent candles from old timeframes (5m, 1h, 4h, 1d within last 30 days)

---

## Solution: Clean Up Old Timeframes

### New Command: `>cleantf`

I've added a new command specifically for cleaning up unwanted timeframes!

#### Step 1: Preview What Will Be Deleted

```
>cleantf
```

**This will show:**
- ✅ Which timeframes are configured (from your `.env`)
- 🗑️ Which timeframes will be deleted
- 📊 How many candles will be removed

#### Step 2: Execute Cleanup

```
>cleantf confirm
```

**This will:**
- Delete ALL candles from old/unwanted timeframes
- Keep ONLY candles matching your current `TIMEFRAMES` in `.env`
- Return detailed statistics

---

## Example Workflow

### Scenario: You Changed from Multi-Timeframe to 15m Only

**Before (Old Configuration):**
```bash
# .env (old)
TIMEFRAMES=15m,1h,4h
```

**After (Current Configuration):**
```bash
# .env (current)
TIMEFRAMES=15m
```

**Result in Database:**
- Candles from **15m** (wanted) ✅
- Candles from **1h** (old, unwanted) ❌
- Candles from **4h** (old, unwanted) ❌
- Maybe some **5m**, **1d** from testing (unwanted) ❌

**Solution:**

1. **Check what you have:**
   ```
   >cleantf
   ```
   
   **Output:**
   ```
   ⚠️ Timeframe Cleanup Warning
   
   Your current configuration uses: 15m
   
   🗑️ Timeframes to Delete:
   1m, 3m, 5m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
   
   ✅ What Will Be Kept:
   • Candles for: 15m
   • All signals
   • All other database tables
   
   📝 To Proceed: Run >cleantf confirm
   ```

2. **Execute cleanup:**
   ```
   >cleantf confirm
   ```
   
   **Output:**
   ```
   ✅ Timeframe Cleanup Complete
   
   📊 Deleted: 15,234 candles from 4 timeframes
   
   🗑️ Removed Timeframes: 5m, 1h, 4h, 1d
   
   ✅ Keeping Timeframes: 15m
   ```

---

## When to Use Each Cleanup Command

### `>cleanup confirm` - Delete OLD data (by date)
**Purpose:** Remove historical data older than 30 days

**Use When:**
- Database is getting too large
- You want to keep recent data for analysis
- Regular maintenance (weekly/monthly)

**What it Deletes:**
- Candles older than 30 days (ALL timeframes)
- Signals older than 30 days

**What it Keeps:**
- Recent candles (last 30 days, ALL timeframes)
- Recent signals (last 30 days)
- Backtests, signal_performance, user_subscriptions

### `>cleantf confirm` - Delete UNWANTED timeframes
**Purpose:** Remove data from timeframes you're no longer using

**Use When:**
- You changed `TIMEFRAMES` in `.env`
- You want to clean up old multi-timeframe data
- You're switching to single-timeframe mode

**What it Deletes:**
- ALL candles from timeframes NOT in your current `.env` configuration
- Regardless of age (even recent data)

**What it Keeps:**
- Candles from configured timeframes (in `.env`)
- All signals
- Backtests, signal_performance, user_subscriptions

---

## Current Configuration Check

### What's in Your `.env`?

```bash
TIMEFRAMES=15m
```

**This means:**
- ✅ Bot will monitor: **15m timeframe only**
- ✅ Bot will create: **15m candles**
- ❌ Bot will NOT create: 5m, 1h, 4h, 1d, etc.

### What `>cleantf confirm` Will Do

**Delete candles from these timeframes:**
- 1m, 3m, 5m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M

**Keep candles from:**
- **15m** (your configured timeframe)

---

## Safety Features

### ⚠️ Confirmation Required

Both cleanup commands require explicit confirmation:

```
>cleanup           # Shows warning, doesn't delete
>cleanup confirm   # Actually deletes

>cleantf          # Shows warning, doesn't delete
>cleantf confirm  # Actually deletes
```

### 📊 Detailed Reporting

Every cleanup returns:
- Number of records deleted
- What was deleted
- What was kept
- Who executed the command

### 🔒 Irreversible

**WARNING:** These operations **CANNOT BE UNDONE**

Once data is deleted from Supabase, it's gone permanently. Always:
1. Review the preview first (`>cleanup` or `>cleantf`)
2. Confirm your `.env` configuration is correct
3. Only run `confirm` when you're sure

---

## Recommended Cleanup Strategy

### Initial Setup (After Configuration Change)

1. **Clean unwanted timeframes:**
   ```
   >cleantf confirm
   ```
   
2. **Clean old data:**
   ```
   >cleanup confirm
   ```

### Ongoing Maintenance

**Weekly:**
```
>cleanup confirm
```
(Removes data older than 30 days)

**After .env Changes:**
```
>cleantf confirm
```
(Removes candles from old timeframes)

---

## Technical Details

### Database Impact

**Before Cleanup:**
```
Timeframes in DB: 5m, 15m, 1h, 4h, 1d
Total candles: ~50,000
Database size: ~150 MB
```

**After `>cleantf confirm` (keeping only 15m):**
```
Timeframes in DB: 15m
Total candles: ~10,000 (80% reduction)
Database size: ~30 MB (80% reduction)
```

### Performance Benefits

**Smaller Database:**
- ✅ Faster queries
- ✅ Lower storage costs
- ✅ Better Supabase performance

**Single Timeframe:**
- ✅ Fewer WebSocket streams (20 vs 60)
- ✅ Faster signal generation
- ✅ No timeframe conflicts
- ✅ Lower CPU/memory usage

---

## FAQ

### Q: Will this delete my signals?
**A:** No. Both cleanup commands preserve ALL signals. Only candle data is deleted.

### Q: Will this affect backtests?
**A:** No. Backtest results are stored in the `backtests` table and are never deleted by cleanup commands.

### Q: Can I restore deleted data?
**A:** No. Cleanup is permanent. However, the bot will automatically re-fetch the last 500 candles for each symbol when it starts, so you'll have recent data again.

### Q: What if I want to add timeframes back later?
**A:** Just update your `.env` with the new timeframes and restart the bot. It will automatically fetch historical data for the new timeframes.

### Q: How often should I run cleanup?
**A:** 
- **`>cleanup confirm`:** Weekly or monthly (for old data)
- **`>cleantf confirm`:** Only after changing `TIMEFRAMES` in `.env`

### Q: Will cleanup improve bot performance?
**A:** Yes! A smaller database means faster queries and less storage usage. Especially noticeable if you're on Supabase free tier.

---

## Commands Summary

| Command | Purpose | Safety | Frequency |
|---------|---------|--------|-----------|
| `>cleanup` | Preview old data cleanup | Safe (read-only) | As needed |
| `>cleanup confirm` | Delete data >30 days old | ⚠️ Permanent | Weekly/Monthly |
| `>cleantf` | Preview timeframe cleanup | Safe (read-only) | After config changes |
| `>cleantf confirm` | Delete unwanted timeframes | ⚠️ Permanent | After config changes |

---

## Your Next Steps

1. **Restart your bot** to load the new commands:
   ```powershell
   python start.py
   ```

2. **Preview the cleanup** (see what will be deleted):
   ```
   >cleantf
   ```

3. **Execute cleanup** when ready:
   ```
   >cleantf confirm
   ```

4. **Verify results** in your Supabase dashboard:
   - Should only see candles with `timeframe = '15m'`
   - No more 5m, 1h, 4h, 1d candles

---

**Your database will be clean and optimized for your 15m-only configuration!** 🎉
