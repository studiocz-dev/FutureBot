# Command Issues Diagnostic & Fix

## Issue Report

**Problem:** Bot stops responding after using commands like `>help` or `>status`.

## Root Causes Identified

### 1. Missing Error Handler ❌
The bot had **no global command error handler**, meaning any exception in a command could potentially cause issues.

### 2. No Command Logging 📝
There was no logging for command execution, making it hard to diagnose what's happening.

### 3. Potential Exception Propagation
If a command threw an exception, it wasn't being caught properly, which could affect the event loop.

---

## Fixes Implemented ✅

### Fix 1: Added Global Command Error Handler

**File:** `src/discord/commands.py`

```python
@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    """
    Global error handler for commands.
    Prevents commands from crashing the bot.
    """
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"❌ Unknown command. Use `>help` to see available commands.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: `{error.param.name}`. Use `>help` for usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument. Use `>help` for usage.")
    elif isinstance(error, commands.CommandInvokeError):
        logger.error(f"Error executing command: {error.original}", exc_info=error.original)
        await ctx.send("❌ An error occurred while executing the command. Please try again later.")
    else:
        logger.error(f"Unhandled command error: {error}", exc_info=error)
        await ctx.send("❌ An unexpected error occurred.")
```

**What it does:**
- Catches all command errors
- Logs the error details
- Sends user-friendly error messages
- **Prevents the bot from crashing**

---

### Fix 2: Added Command Logging

**File:** `src/bot/main.py`

```python
@self.discord_bot.event
async def on_command(ctx):
    """Log when a command is invoked."""
    logger.info(f"Command '{ctx.command}' invoked by {ctx.author} in {ctx.guild or 'DM'}")

@self.discord_bot.event
async def on_command_completion(ctx):
    """Log when a command completes successfully."""
    logger.info(f"Command '{ctx.command}' completed successfully for {ctx.author}")
```

**What it does:**
- Logs every command invocation
- Logs successful completion
- Helps diagnose if commands are hanging or failing

---

### Fix 3: Enhanced Status Command Logging

**File:** `src/discord/commands.py`

Added detailed logging to the `>status` command:
```python
logger.debug("Fetching fuser stats...")
fuser_stats = signal_fuser.get_stats()

logger.debug("Fetching metrics data...")
metrics_data = metrics.get_summary()

logger.debug("Creating embed...")
# ... embed creation

logger.debug("Sending status embed...")
await ctx.send(embed=embed)
```

**What it does:**
- Shows exactly where the command might be failing
- Helps identify if it's a stats issue, metrics issue, or Discord API issue

---

## Testing Your Bot

### Step 1: Update Your Server

```bash
cd /path/to/bot
git pull
```

### Step 2: Restart the Bot

```bash
python start.py
```

### Step 3: Test Commands

In your Discord server, try these commands **one at a time**:

```
>help
>status
>signal BTC
>signals 5
```

### Step 4: Check Logs

Look for these log entries:

**✅ Good (command working):**
```
INFO - Command 'help' invoked by YourUsername in YourServer
INFO - Command 'help' completed successfully for YourUsername
```

**❌ Bad (command failing):**
```
INFO - Command 'status' invoked by YourUsername in YourServer
ERROR - Error executing command: [error details]
```

---

## Common Issues & Solutions

### Issue 1: Bot Not Responding at All

**Symptoms:**
- Bot shows as online
- No response to any commands
- No log entries when commands are sent

**Solution:**
```python
# Check if bot has message content intent enabled
intents = discord.Intents.default()
intents.message_content = True  # ← Must be True
```

**Verify:**
1. Check `src/bot/main.py` has `intents.message_content = True`
2. Go to Discord Developer Portal → Your App → Bot
3. Enable "Message Content Intent"
4. Restart bot

---

### Issue 2: Status Command Fails

**Symptoms:**
- `>help` works
- `>status` doesn't respond or errors

**Check logs for:**
```
ERROR - Error in status command: 'Metrics' object has no attribute 'get_summary'
```

**Solution:**
The `get_summary()` method exists, but check if `metrics` is being passed correctly:

**File:** `src/bot/main.py` (around line 138)
```python
setup_commands(
    bot=self.discord_bot,
    supabase=self.supabase,
    signal_fuser=self.signal_fuser,
    metrics=self.metrics,  # ← Make sure this is here
)
```

---

### Issue 3: Bot Stops After Command

**Symptoms:**
- Command executes successfully
- Bot stops generating signals after
- No more candle close events

**This should NOT happen anymore** with the error handler in place. But if it does:

**Check:**
1. Look for exceptions in logs
2. Check if WebSocket connections are still active
3. Verify background tasks are still running

**Debug command:**
```python
# In Discord, send:
>status

# Check "Active Cooldowns" field
# If it's frozen at a number, something might be wrong
```

---

### Issue 4: Commands Work But Signals Stop

**Symptoms:**
- Commands respond correctly
- But no new signals are generated

**Check:**
1. **Cooldown**: Signals have a 5-minute cooldown per symbol/timeframe
2. **Conflict Prevention**: Opposite signals blocked for 1 hour
3. **Confidence**: Check if signals are below MIN_CONFIDENCE threshold

**Verify with:**
```
>status
# Check "Signals Today" count - should increase over time
```

---

## Testing Script

A test script has been created: `test_commands.py`

**Run it (in a separate terminal while bot is running):**
```bash
python test_commands.py
```

This will:
- Connect to Discord
- Monitor command activity
- Show you what to test
- Display command logs in real-time

---

## Expected Bot Behavior

### ✅ Correct Behavior

1. **Command Execution:**
   ```
   User: >help
   Bot: [Shows help embed]
   [Bot continues running, signals still work]
   ```

2. **Background Tasks:**
   ```
   [Candle closes for BTCUSDT 1h]
   [Signal analyzed]
   [Signal sent to Discord]
   [Bot still responsive to commands]
   ```

3. **Multiple Commands:**
   ```
   User: >help
   Bot: [Response]
   User: >status
   Bot: [Response]
   User: >signal BTC
   Bot: [Response]
   [All work without issues]
   ```

---

## Monitoring

### Check Bot Health

```
>status
```

**Should show:**
- ⚙️ Configuration (confidence, analyzers, cooldown)
- 📊 Signals Today (total, long, short)
- 🔥 Active Cooldowns (number of symbols on cooldown)

### Check Recent Signals

```
>signals 10
```

**Should show:**
- Last 10 signals across all symbols
- Each with timestamp, symbol, type, confidence

### Test Signal Lookup

```
>signal BTC
>signal ETH 4h
>signal BNB 15m
```

**Should show:**
- Latest signal for that symbol/timeframe
- Entry price, SL, TPs
- Wyckoff phase, Elliott count
- Analysis rationale

---

## Files Modified

1. ✅ `src/discord/commands.py`
   - Added `on_command_error` handler
   - Enhanced `>status` command logging

2. ✅ `src/bot/main.py`
   - Added `on_command` event logger
   - Added `on_command_completion` event logger

3. ✅ `test_commands.py` (NEW)
   - Testing utility for command debugging

4. ✅ `COMMAND_ISSUES_FIX.md` (THIS FILE)
   - Complete diagnostic guide

---

## Next Steps

1. **Pull the latest code:**
   ```bash
   git pull
   ```

2. **Restart your bot:**
   ```bash
   python start.py
   ```

3. **Test all commands:**
   - >help
   - >status
   - >signal BTC
   - >signals

4. **Monitor logs** for any errors

5. **Report back** if issues persist with:
   - Exact command that fails
   - Error message from logs
   - Bot behavior (stops, crashes, no response)

---

## If Issues Persist

### Collect Diagnostic Info

1. **Run the bot with verbose logging:**
   ```bash
   # In .env, change:
   LOG_LEVEL=DEBUG
   ```

2. **Try each command and note:**
   - Which commands work
   - Which commands fail
   - Exact error messages
   - Whether bot continues after or stops

3. **Check these log entries:**
   ```
   Command 'X' invoked by...
   Command 'X' completed successfully...
   ERROR - Error in X command: ...
   ```

4. **Test signal generation:**
   - Wait for a candle to close (check logs)
   - See if signal is generated
   - Verify Discord notification is sent

---

## Summary

✅ **Added global error handler** - prevents commands from crashing bot
✅ **Added command logging** - helps diagnose issues
✅ **Enhanced status command** - more detailed error tracking
✅ **Created test script** - easier debugging
✅ **Documented troubleshooting** - comprehensive guide

**Your bot should now:**
- ✅ Handle command errors gracefully
- ✅ Continue running after commands
- ✅ Log all command activity
- ✅ Provide better error messages

**All changes pushed to GitHub!** Pull and restart your bot.
