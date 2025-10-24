# Stop Bot - Quick Reference

## Windows PowerShell Commands

### Check for Running Python Processes
```powershell
# Method 1: Using Get-Process
Get-Process python -ErrorAction SilentlyContinue

# Method 2: Using tasklist
tasklist /FI "IMAGENAME eq python.exe"

# Method 3: Find bot specifically (if running from this directory)
Get-Process | Where-Object {$_.Path -like "*Discord_Bot*"}
```

### Stop All Python Processes
```powershell
# Stop all Python processes (CAUTION: Kills ALL Python)
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force

# OR using taskkill
taskkill /F /IM python.exe
```

### Stop Specific Python Process by ID
```powershell
# First, get the process ID
Get-Process python

# Then kill by ID (replace 12345 with actual ID)
Stop-Process -Id 12345 -Force
```

### Graceful Stop (Recommended)
```powershell
# If bot is running in a terminal, just press:
Ctrl + C

# This triggers graceful shutdown:
# - Closes WebSocket connections
# - Closes Discord connection  
# - Saves state
# - Exits cleanly
```

---

## Linux/Mac Commands

### Check for Running Processes
```bash
# Find Python processes
ps aux | grep python

# Find bot specifically
ps aux | grep "start.py\|main.py"
```

### Stop Processes
```bash
# Graceful stop (if running in terminal)
Ctrl + C

# Kill all Python processes (CAUTION)
pkill python

# Kill specific process by ID
kill <PID>

# Force kill if not responding
kill -9 <PID>
```

---

## Current Status

✅ **No Python processes running**
```
INFO: No tasks are running which match the specified criteria.
```

The bot is currently **stopped**.

---

## How to Start Bot

```powershell
# Navigate to bot directory
cd I:\Discord_Bot\WyEli_Bot

# Start the bot
python start.py
```

---

## Safety Tips

### ⚠️ Before Stopping

1. **Check if signals are being generated**
   - Wait for current signal to complete
   - Don't stop mid-analysis

2. **Note the uptime**
   - Check `>status` in Discord
   - Record any important metrics

3. **Save logs**
   - Bot logs are saved automatically
   - But check if you need any specific data

### ✅ Graceful Stop (Best Practice)

**Always use Ctrl+C** when possible:
- Closes WebSocket connections cleanly
- Closes Discord connection properly
- Saves state
- Logs shutdown message

### ❌ Force Kill (Last Resort)

Only use `Stop-Process -Force` or `taskkill /F` if:
- Bot is frozen/not responding
- Ctrl+C doesn't work
- Bot is stuck in infinite loop

**Side effects of force kill:**
- WebSocket connections may stay open (timeout eventually)
- Discord bot may show as "online" briefly
- In-progress signals might be lost
- No graceful shutdown logs

---

## Troubleshooting

### Bot Won't Stop with Ctrl+C

**Try:**
1. Wait 10 seconds (bot is shutting down)
2. Press Ctrl+C again (second signal)
3. Close terminal window
4. Use force kill as last resort

**Check logs for:**
```
INFO - Stop signal received
INFO - Shutting down...
INFO - Bot stopped
```

### Multiple Python Processes

**To identify bot process:**
```powershell
Get-Process python | Select-Object Id, StartTime, @{
    Name="WorkingSet(MB)";
    Expression={[Math]::Round($_.WorkingSet/1MB, 2)}
}
```

The bot process usually:
- Started from `I:\Discord_Bot\WyEli_Bot`
- Uses 50-200 MB of RAM
- Started recently (if you just launched it)

---

## Quick Commands Reference

| Action | Windows | Linux/Mac |
|--------|---------|-----------|
| **Check processes** | `tasklist /FI "IMAGENAME eq python.exe"` | `ps aux \| grep python` |
| **Graceful stop** | `Ctrl + C` | `Ctrl + C` |
| **Force stop all** | `taskkill /F /IM python.exe` | `pkill python` |
| **Force stop by ID** | `Stop-Process -Id <ID> -Force` | `kill -9 <PID>` |
| **Start bot** | `python start.py` | `python start.py` |

---

## Status: ✅ No Bot Running

Current status: **No Python processes found**

To start the bot:
```powershell
python start.py
```

To monitor while running:
```powershell
# In another terminal
python monitor_commands.py
```
