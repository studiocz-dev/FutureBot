# Server Deployment Guide

## Issues Found in Logs

### ❌ Issue 1: Disk Space
```
ERROR: Could not install packages due to an OSError: [Errno 28] No space left on device
```
**Solution:** Contact Wispbyte support to increase disk space or clean up old files.

### ❌ Issue 2: Import Error
```
ImportError: attempted relative import with no known parent package
```
**Problem:** Server is running `python /home/container/src/bot/main.py` directly, but the code uses relative imports.

### ❌ Issue 3: Async Function Not Awaited
```
RuntimeWarning: coroutine 'main' was never awaited
```
**Problem:** The `main()` function is async but was being called as a regular function.
**Solution:** Use `asyncio.run(main())` - this is now fixed in `start.py`.

---

## Deployment Solutions

### Option 1: Use start.py (Recommended)
Update your server's startup command to:
```bash
python start.py
```

The `start.py` launcher handles the import path correctly.

### Option 2: Run as Module
Update your server's startup command to:
```bash
python -m src.bot.main
```

### Option 3: Update Server Configuration
In your Wispbyte panel, update these settings:

**PY_FILE variable:**
- Current: `src/bot/main.py` ❌
- Change to: `start.py` ✅

**Or set custom startup command:**
```bash
cd /home/container && python -m src.bot.main
```

---

## Recommended Server Settings

### 1. Requirements File
Use the minimal requirements for faster installation and less disk space:

```bash
REQUIREMENTS_FILE=requirements-minimal.txt
```

This installs only 13 essential packages instead of 40+ packages.

### 2. Disk Space
Ensure at least **500 MB** free space for:
- Python packages (~200 MB)
- Logs and cache (~100 MB)
- Application data (~50 MB)

### 3. Environment Variables
Make sure your `.env` file is uploaded to the server with:
```env
DISCORD_BOT_TOKEN=your_token_here
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_service_role_key
MIN_CONFIDENCE=0.65
```

---

## Testing Deployment

After fixing the issues, the bot should start with logs like:
```
[2025-10-24 01:36:00] INFO - FutureBot starting...
[2025-10-24 01:36:01] INFO - Database initialized
[2025-10-24 01:36:02] INFO - Connected 9 WebSocket streams
[2025-10-24 01:36:03] INFO - Bot connected as FutureBot#6502
[2025-10-24 01:36:03] INFO - Ready to receive commands
```

---

## Quick Commands for Server

### Check disk space:
```bash
df -h /home/container
```

### Check installed packages:
```bash
pip list
```

### Manual install (if needed):
```bash
pip install -r requirements-minimal.txt
```

### Test bot locally first:
```bash
python start.py
```

---

## Support

If issues persist:
1. Contact Wispbyte support for disk space
2. Verify `.env` file exists on server
3. Check server logs for other errors
4. Test the bot locally before deploying
