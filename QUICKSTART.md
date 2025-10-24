# Quick Start Guide

## 🚀 Get Your Bot Running in 5 Minutes

### Prerequisites Checklist
- ✅ Python 3.11+ installed
- ✅ Supabase project created
- ✅ SQL migration executed
- ✅ Discord bot created and added to server
- ✅ `.env` file configured

---

## Step 1: Install Dependencies

```powershell
# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1

# Install packages
pip install -r requirements.txt
```

---

## Step 2: Configure Environment

Make sure your `.env` file has these values:

```env
# From Supabase Dashboard → Settings → API
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# From Discord Developer Portal
DISCORD_TOKEN=MTIzNDU2Nzg5MDEyMzQ1Njc4.GhJ4Kl...
DISCORD_GUILD_ID=123456789012345678
DISCORD_SIGNALS_CHANNEL_ID=987654321098765432

# Trading pairs (no spaces!)
SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT
TIMEFRAMES=15m,1h,4h

# Signal settings
MIN_CONFIDENCE=0.65
ENABLE_WYCKOFF=true
ENABLE_ELLIOTT=true

# Trading (keep disabled for testing)
ENABLE_TRADING=false
```

---

## Step 3: Run the Bot

### Option A: VS Code (Easiest)
1. Open project in VS Code
2. Press **F5**
3. Select "Run Bot (dev)"
4. Check Debug Console for logs

### Option B: Command Line
```powershell
python -m src.bot.main
```

---

## Step 4: Test Commands

Once the bot is online (you'll see "Bot is ready!" in logs), test in Discord:

```
>help
```

This will show all available commands.

### Try These Commands:

```
>signal BTC
```
Get the latest BTC signal (1h timeframe by default)

```
>signal ETH 4h
```
Get ETH signal for 4-hour timeframe

```
>status
```
Check bot status and statistics

```
>signals 5
```
Show last 5 signals across all symbols

---

## Expected Bot Output

When starting, you should see logs like:

```
2024-10-24 10:30:00 - INFO - Bot starting...
2024-10-24 10:30:01 - INFO - Supabase connected
2024-10-24 10:30:02 - INFO - Downloading historical candles...
2024-10-24 10:30:05 - INFO - Downloaded 500 candles for BTCUSDT 1h
2024-10-24 10:30:06 - INFO - Downloaded 500 candles for ETHUSDT 1h
2024-10-24 10:30:08 - INFO - WebSocket connected
2024-10-24 10:30:09 - INFO - Discord bot logged in as WyEliBot#1234
2024-10-24 10:30:09 - INFO - Bot is ready! Use commands like: >signal BTC
```

---

## Troubleshooting

### ❌ "Missing required environment variable"
- Check `.env` file exists in project root
- Verify all required variables are set
- No spaces around `=` in `.env`

### ❌ "Supabase connection failed"
- Verify `SUPABASE_URL` format: `https://xxxxx.supabase.co`
- Make sure you're using `SUPABASE_SERVICE_KEY` (not anon key)
- Check Supabase project isn't paused

### ❌ "Invalid DISCORD_TOKEN"
- Token is correct and not expired
- Bot has "Message Content Intent" enabled
- Bot is added to your server

### ❌ Bot doesn't respond to commands
- Check bot is online (green dot in Discord)
- Verify "Message Content Intent" is enabled
- Make sure bot has "Send Messages" permission in the channel
- Command prefix is `>` not `/`

### ❌ No signals appearing
- This is normal! Signals are generated when Wyckoff/Elliott patterns appear
- These patterns are rare and require specific market conditions
- Wait 10-15 minutes after startup for enough data
- Check database for historical signals: `>signals 10`

---

## Next Steps

Once everything is working:

1. **Monitor for signals** - Wait for real-time signals to appear
2. **Check signal quality** - Review confidence scores and analysis
3. **Adjust settings** - Lower `MIN_CONFIDENCE` if too few signals
4. **Add more symbols** - Edit `SYMBOLS` in `.env`
5. **Try different timeframes** - Experiment with 15m, 1h, 4h

---

## Command Reference

| Command | Description | Example |
|---------|-------------|---------|
| `>signal <symbol> [timeframe]` | Get latest signal | `>signal BTC 1h` |
| `>status` | Bot statistics | `>status` |
| `>signals [limit]` | Recent signals | `>signals 10` |
| `>help` | Show help | `>help` |

---

## Important Notes

⚠️ **This bot is for educational purposes only - not financial advice!**

- Default mode is **alerts-only** (no actual trading)
- Signals are based on technical analysis, not guaranteed to be profitable
- Always do your own research before trading
- Never trade with money you can't afford to lose

---

## Need Help?

- 📖 Check `README.md` for full documentation
- 🔧 See `docs/RUNBOOK.md` for operational procedures
- 🔒 Read `docs/SECURITY.md` for security best practices
- 🏗️ Review `docs/ARCHITECTURE.md` for system design

---

**Happy Trading! 🚀**
