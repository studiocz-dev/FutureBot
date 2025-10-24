# Status Command Crash - Diagnostic & Fix

## Issue

**Problem:** Bot stops/crashes when `>status` command is executed.

**Symptoms:**
- Bot responds to `>help` command
- Bot stops running after `>status` is called
- No response or error message in Discord
- Bot process terminates

---

## Root Cause Analysis

### Potential Issues:

1. **Unhandled exception in status command**
   - `metrics.get_summary()` might throw exception
   - `signal_fuser.get_stats()` might throw exception
   - Exception not caught properly → bot crashes

2. **Event loop blocking**
   - `get_summary()` might be doing synchronous operations
   - Could block the async event loop
   - Bot appears to "freeze" or stop

3. **Discord API error**
   - Embed might be too large or invalid
   - `bot.user.name` might be None at certain times
   - Network issue sending response

---

## Fixes Implemented

### Fix 1: Defensive Error Handling

**File:** `src/discord/commands.py` - `status_command()`

**Added:**
- Try-except around `signal_fuser.get_stats()`
- Try-except around `metrics.get_summary()`
- Fallback default values if either fails
- Try-except around embed creation
- Try-except around sending response

**Now:**
- If `get_stats()` fails → uses default values
- If `get_summary()` fails → uses default values (all zeros)
- If embed fails → logs error but doesn't crash
- Command always completes, never crashes bot

```python
try:
    fuser_stats = signal_fuser.get_stats()
except Exception as e:
    logger.error(f"Error fetching fuser stats: {e}")
    fuser_stats = {'min_confidence': 0.65, ...}  # defaults
```

---

### Fix 2: Better Error Handler

**File:** `src/discord/commands.py` - `on_command_error()`

**Added:**
- Try-except wrapper around entire error handler
- Prevents error handler itself from crashing

**Now:**
- Even if error handler fails, bot continues
- All exceptions are logged
- No silent failures

---

### Fix 3: Enhanced Logging

**Added detailed logging:**
- Before fetching stats
- After fetching stats (with data preview)
- Before creating embed
- Before sending response
- Success confirmation

**Now:**
- Easy to see exactly where command fails
- Can identify which part causes the crash
- Better debugging information

---

## Testing

### Quick Test (Recommended)

Run this to test if Metrics and SignalFuser work:
```bash
python test_metrics.py
```

**Expected output:**
```
✅ Metrics created successfully
✅ get_summary() returned: {...}
✅ get_signal_count() returned: 0
✅ SignalFuser created successfully
✅ get_stats() returned: {...}
```

**If any ❌ appears:**
- That component has a bug
- Check the error message and traceback
- Report the error

---

### Full Bot Test

1. **Pull latest code:**
   ```bash
   git pull
   ```

2. **Start bot:**
   ```bash
   python start.py
   ```

3. **Watch logs for:**
   ```
   INFO - Registered Discord prefix commands: signal, status, help, signals
   INFO - Total commands registered: 4
   ```

4. **In Discord, try:**
   ```
   >help    (should work)
   >status  (test if it still crashes)
   ```

5. **Check logs for:**
   ```
   INFO - Status command called by YourName
   DEBUG - Fetching fuser stats...
   DEBUG - Fuser stats: {'min_confidence': 0.65, ...}
   DEBUG - Fetching metrics data...
   DEBUG - Metrics data keys: dict_keys([...])
   DEBUG - Creating embed...
   DEBUG - Sending status embed...
   INFO - ✅ Status command executed successfully by YourName
   ```

6. **If crash occurs, check for:**
   ```
   ERROR - Error fetching fuser stats: ...
   ERROR - Error fetching metrics: ...
   ERROR - ❌ Error in status command: ...
   ```

---

## Common Issues & Solutions

### Issue 1: Bot Stops Immediately

**Symptoms:**
- Bot crashes as soon as >status is sent
- No response in Discord
- Bot process terminates

**Check logs for:**
```
ERROR - Error in status command: ...
CRITICAL - Fatal error: ...
```

**Possible causes:**
1. Exception in `get_summary()` or `get_stats()`
2. Memory issue
3. Asyncio event loop crash

**Solution:**
Run `python test_metrics.py` to isolate the issue.

---

### Issue 2: Bot Freezes (No Crash)

**Symptoms:**
- Bot doesn't respond to >status
- Bot appears online
- No error in logs
- Bot doesn't crash but seems "frozen"

**Possible causes:**
1. Blocking operation in `get_summary()`
2. Database query hanging
3. Network timeout

**Check:**
- Are there many signals? (thousands)
- Is `get_signals_today()` taking too long?
- Database connection issues?

**Solution:**
Add timeout to metrics calls (we'll implement if needed).

---

### Issue 3: Partial Response Then Crash

**Symptoms:**
- Bot starts to respond
- Then crashes mid-response
- Embed partially sent

**Possible causes:**
1. Embed too large (Discord limit: 25 fields)
2. Invalid embed data
3. Network issue

**Check logs for:**
```
DEBUG - Sending status embed...
ERROR - Error sending embed: ...
```

**Solution:**
Already handled with try-except around `ctx.send()`.

---

### Issue 4: "An error occurred" Message

**Symptoms:**
- Bot responds with "❌ An error occurred while fetching status"
- Bot continues running (good!)
- But status doesn't show

**Check logs for:**
```
ERROR - Error fetching fuser stats: ...
ERROR - Error fetching metrics: ...
```

**This is GOOD:**
- Bot didn't crash ✅
- Error was caught ✅
- Error is logged ✅

**Next step:**
- Look at the specific error in logs
- Fix the underlying issue (Metrics or SignalFuser)

---

## Diagnostic Steps

### Step 1: Check if Components Work

```bash
python test_metrics.py
```

If this fails, the issue is in Metrics or SignalFuser, not the command.

---

### Step 2: Check Bot Startup

Look for these in logs:
```
✅ INFO - Registered Discord prefix commands: signal, status, help, signals
✅ INFO - Total commands registered: 4
✅ INFO - Bot is fully operational! 🚀
```

If you don't see these, bot didn't start properly.

---

### Step 3: Test Status Command

In Discord:
```
>status
```

Watch logs in real-time. You should see:
```
INFO - Command 'status' invoked by ...
INFO - Status command called by ...
DEBUG - Fetching fuser stats...
DEBUG - Fuser stats: ...
DEBUG - Fetching metrics data...
DEBUG - Metrics data keys: ...
DEBUG - Creating embed...
DEBUG - Sending status embed...
INFO - ✅ Status command executed successfully
INFO - Command 'status' completed successfully
```

**If you see an ERROR before "✅ Status command executed":**
- That's where it's failing
- Read the error message
- Check the traceback

---

### Step 4: Check Event Loop

If bot freezes (doesn't crash, just stops responding):

**Check:**
1. Is bot still running? `ps aux | grep python` (Linux) or Task Manager (Windows)
2. Are logs still being written?
3. Can you Ctrl+C to stop it?

**If bot is frozen:**
- Likely a blocking operation
- Need to add timeouts
- Report this and we'll fix

---

## Files Modified

1. ✅ `src/discord/commands.py`
   - Enhanced status command with defensive error handling
   - Added detailed logging
   - Wrapped error handler in try-except

2. ✅ `test_metrics.py` (NEW)
   - Diagnostic script to test Metrics and SignalFuser
   - Isolates issues without running full bot

3. ✅ `STATUS_COMMAND_FIX.md` (THIS FILE)
   - Complete diagnostic guide
   - Testing procedures
   - Troubleshooting steps

---

## Next Steps

1. **Pull latest code:**
   ```bash
   git pull
   ```

2. **Test components:**
   ```bash
   python test_metrics.py
   ```

3. **Restart bot:**
   ```bash
   python start.py
   ```

4. **Test status command:**
   ```
   >status
   ```

5. **Report back with:**
   - Output of `test_metrics.py`
   - Bot logs when >status is called
   - Whether bot crashes or shows error message
   - Exact error message if any

---

## Expected Behavior

### ✅ If Fix Works:

**Scenario 1: Everything works**
```
User: >status
Bot: [Shows status embed with config, signals, cooldowns]
[Bot continues running, signals continue]
```

**Scenario 2: Metrics fails but bot continues**
```
User: >status
Bot: [Shows status embed with default/partial data]
Logs: ERROR - Error fetching metrics: ...
[Bot continues running]
```

**Scenario 3: Command fails but bot continues**
```
User: >status
Bot: "❌ An error occurred while fetching status. Check bot logs."
Logs: ERROR - ❌ Error in status command: ...
[Bot continues running]
```

### ❌ If Issue Persists:

```
User: >status
[Bot stops responding]
[Bot process terminates]
```

If this happens:
1. Run `python test_metrics.py` first
2. Capture full log output
3. Report the error with:
   - test_metrics.py output
   - Last 50 lines of bot logs
   - Python version
   - OS (Windows/Linux)

---

## Summary

✅ **Added robust error handling** to status command
✅ **Created diagnostic tool** (test_metrics.py)
✅ **Enhanced logging** for better debugging
✅ **Wrapped error handler** to prevent crashes
✅ **Documented testing procedures**

**The bot should now:**
- Not crash when >status is called
- Show error message if something fails
- Log detailed information for debugging
- Continue running even if status command has issues

**All changes pushed to GitHub!**
