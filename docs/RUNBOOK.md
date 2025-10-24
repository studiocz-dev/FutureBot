# Runbook - Operational Procedures

This runbook provides step-by-step instructions for deploying, running, monitoring, and troubleshooting the Wyckoff-Elliott Trading Signals Bot.

---

## 📋 Table of Contents

1. [Initial Setup](#initial-setup)
2. [Configuration](#configuration)
3. [Running Locally](#running-locally)
4. [Monitoring](#monitoring)
5. [Troubleshooting](#troubleshooting)
6. [Deployment](#deployment)
7. [Maintenance](#maintenance)
8. [Emergency Procedures](#emergency-procedures)

---

## 🚀 Initial Setup

### 1. Create Supabase Project

#### Step 1: Sign Up
1. Go to [supabase.com](https://supabase.com)
2. Click "Start your project"
3. Sign up with GitHub or email

#### Step 2: Create Project
1. Click "New Project"
2. Fill in details:
   - **Name**: `wyeli-bot` (or your choice)
   - **Database Password**: Generate a strong password (save it!)
   - **Region**: Choose closest to your server location
   - **Pricing Plan**: Free tier is sufficient for development

3. Wait for project to provision (2-3 minutes)

#### Step 3: Run Database Migration

1. In Supabase Dashboard, go to **SQL Editor**
2. Click "New query"
3. Copy contents of `src/storage/migrations/001_create_schema.sql`
4. Paste into SQL editor
5. Click "Run" (Ctrl+Enter)
6. Verify success message: "Success. No rows returned"

#### Step 4: Get API Credentials

1. Go to **Settings** → **API**
2. Copy the following:
   - **Project URL** (e.g., `https://abcdefgh.supabase.co`)
   - **anon public** key (for dev/testing)
   - **service_role** key (for production - keep secret!)

#### Step 5: Enable Realtime (Optional)

1. Go to **Database** → **Replication**
2. Enable replication for `signals` table
3. This allows external apps to subscribe to signal events

---

### 2. Create Discord Bot

#### Step 1: Create Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Enter name: `WyEli Trading Bot`
4. Click "Create"

#### Step 2: Create Bot User

1. In left sidebar, click "Bot"
2. Click "Add Bot" → "Yes, do it!"
3. **Copy the token** (click "Reset Token" if needed)
   - ⚠️ **NEVER share this token publicly!**
4. Enable **Privileged Gateway Intents**:
   - ✅ **Message Content Intent** (required)
   - ❌ Presence Intent (optional)
   - ❌ Server Members Intent (optional)

#### Step 3: Generate Invite URL

1. Go to "OAuth2" → "URL Generator"
2. Select **Scopes**:
   - ✅ `bot`
3. Select **Bot Permissions**:
   - ✅ Send Messages
   - ✅ Embed Links
   - ✅ Read Message History
4. Copy generated URL at bottom

#### Step 4: Add Bot to Server

1. Paste the invite URL into browser
2. Select your server from dropdown
3. Click "Continue" → "Authorize"
4. Complete CAPTCHA

#### Step 5: Get Guild and Channel IDs

1. Enable Developer Mode in Discord:
   - User Settings → Advanced → Developer Mode
2. Right-click your server icon → "Copy ID" (Guild ID)
3. Right-click the channel for signals → "Copy ID" (Channel ID)

---

## ⚙️ Configuration

### Environment Variables

Create `.env` file in project root:

```env
# ============================================
# Supabase Configuration
# ============================================
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key-here  # Production
# SUPABASE_ANON_KEY=your-anon-key-here  # Development (optional)

# ============================================
# Discord Configuration
# ============================================
DISCORD_TOKEN=your-discord-bot-token-here
DISCORD_GUILD_ID=123456789012345678
DISCORD_SIGNALS_CHANNEL_ID=987654321098765432

# ============================================
# Binance Configuration
# ============================================
# For alerts-only mode, no API keys needed!
# Uncomment below only if enabling trading:
# BINANCE_API_KEY=your-api-key-here
# BINANCE_API_SECRET=your-api-secret-here
# BINANCE_TESTNET=true  # Use testnet first!

# ============================================
# Trading Symbols & Timeframes
# ============================================
SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,ADAUSDT
TIMEFRAMES=15m,1h,4h

# ============================================
# Signal Configuration
# ============================================
MIN_CONFIDENCE=0.65            # 0.0-1.0 (higher = fewer signals)
ENABLE_WYCKOFF=true           # Enable Wyckoff analysis
ENABLE_ELLIOTT=true           # Enable Elliott Wave analysis
SIGNAL_COOLDOWN_SECONDS=300   # 5 minutes between signals per symbol

# ============================================
# Trading Configuration (DISABLED by default)
# ============================================
ENABLE_TRADING=false          # ⚠️ Set to true to enable actual trading
POSITION_SIZE_USDT=100.0      # Position size per trade
MAX_OPEN_POSITIONS=3          # Max concurrent positions
LEVERAGE=1                    # Futures leverage (1 = no leverage)

# ============================================
# Cache Configuration (Optional)
# ============================================
# CACHE_TYPE=redis
# REDIS_HOST=localhost
# REDIS_PORT=6379
# REDIS_DB=0
# REDIS_PASSWORD=

# ============================================
# Logging
# ============================================
LOG_LEVEL=INFO                # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=json               # json or text

# ============================================
# WebSocket Configuration
# ============================================
WS_RECONNECT_DELAY=5          # Initial reconnect delay (seconds)
WS_MAX_RECONNECT_DELAY=60     # Max reconnect delay (seconds)

# ============================================
# Backtest Configuration
# ============================================
BACKTEST_INITIAL_BALANCE=10000.0
BACKTEST_COMMISSION=0.0004    # 0.04% taker fee on Binance
```

### Configuration Validation

Run validation script:

```powershell
python -c "from src.bot.config import Config; Config.from_env().validate(); print('✅ Configuration valid!')"
```

Expected output:
```
✅ Configuration valid!
```

If errors occur, check:
- All required environment variables are set
- Values have correct types (e.g., numbers not strings)
- URLs are properly formatted

---

## 🏃 Running Locally

### Option 1: VS Code (Recommended)

1. Open project in VS Code
2. Install recommended extensions (if prompted)
3. Press **F5** or click **Run → Start Debugging**
4. Select **"Run Bot (dev)"** configuration
5. Check Debug Console for logs

**Output should show:**
```
2024-01-15 10:30:00 - INFO - Bot starting...
2024-01-15 10:30:01 - INFO - Supabase connected
2024-01-15 10:30:02 - INFO - Downloaded 500 candles for BTCUSDT 1h
2024-01-15 10:30:03 - INFO - WebSocket connected
2024-01-15 10:30:04 - INFO - Discord bot ready
```

### Option 2: Command Line

#### Activate Virtual Environment

```powershell
# PowerShell
.\venv\Scripts\Activate.ps1

# Command Prompt
venv\Scripts\activate.bat
```

#### Run Bot

```powershell
python -m src.bot.main
```

#### Run in Background (Windows)

```powershell
Start-Process python -ArgumentList "-m", "src.bot.main" -NoNewWindow -RedirectStandardOutput "logs\bot.log" -RedirectStandardError "logs\bot_errors.log"
```

#### Stop Bot

Press **Ctrl+C** for graceful shutdown.

---

## 📊 Monitoring

### 1. Check Bot Status

In Discord, use the command:
```
>status
```

Output shows:
- Bot uptime
- WebSocket connection status
- Signals sent (total and per symbol)
- Last signal timestamp
- Database connection status

### 2. View Logs

Logs are printed to console by default. To save to file:

```powershell
python -m src.bot.main 2>&1 | Tee-Object -FilePath "logs\bot.log"
```

**Log Levels:**
- `DEBUG`: Detailed diagnostic information
- `INFO`: General informational messages
- `WARNING`: Potential issues (e.g., API rate limit approaching)
- `ERROR`: Errors that don't stop the bot
- `CRITICAL`: Fatal errors requiring restart

### 3. Monitor Database

#### Supabase Dashboard

1. Go to Supabase Dashboard → **Database** → **Tables**
2. View recent signals:
   - Click `signals` table
   - Click "View data"
   - Sort by `generated_at` descending

#### SQL Queries

Run in Supabase SQL Editor:

**Recent Signals (Last 24 hours):**
```sql
SELECT * FROM v_recent_signals
WHERE generated_at > NOW() - INTERVAL '24 hours'
ORDER BY generated_at DESC;
```

**Signal Statistics:**
```sql
SELECT * FROM v_signal_stats
ORDER BY total_signals DESC;
```

**Win Rate (if tracking outcomes):**
```sql
SELECT 
  symbol_name,
  AVG(CASE WHEN outcome = 'WIN' THEN 1.0 ELSE 0.0 END) * 100 as win_rate_pct,
  COUNT(*) as total_signals
FROM signal_performance
GROUP BY symbol_name
ORDER BY total_signals DESC;
```

### 4. Discord Notifications

Ensure signals are being posted:
1. Check configured channel (`DISCORD_SIGNALS_CHANNEL_ID`)
2. Verify bot has "Send Messages" permission
3. Test with `>signal BTC` command

### 5. WebSocket Health

If no signals appear:
1. Check logs for "WebSocket connected" message
2. Look for reconnection attempts (should be rare)
3. Verify Binance API is accessible:

```powershell
python -c "import aiohttp, asyncio; asyncio.run(aiohttp.ClientSession().get('https://fapi.binance.com/fapi/v1/ping'))"
```

---

## 🐛 Troubleshooting

### Problem: Bot Won't Start

#### Error: "Missing required environment variable"

**Cause:** `.env` file not configured

**Solution:**
1. Copy `.env.example` to `.env`
2. Fill in all required values
3. Run validation: `python -c "from src.bot.config import Config; Config.from_env().validate()"`

#### Error: "Invalid DISCORD_TOKEN"

**Cause:** Token is incorrect or expired

**Solution:**
1. Go to Discord Developer Portal
2. Regenerate bot token
3. Update `DISCORD_TOKEN` in `.env`

#### Error: "Supabase connection failed"

**Cause:** Incorrect Supabase credentials

**Solution:**
1. Verify `SUPABASE_URL` format: `https://[project-ref].supabase.co`
2. Ensure `SUPABASE_SERVICE_KEY` is the **service_role** key, not anon key
3. Check Supabase project is not paused (free tier pauses after 1 week inactivity)

---

### Problem: No Signals Generated

#### Possible Causes & Solutions

**1. MIN_CONFIDENCE too high**
- Lower `MIN_CONFIDENCE` in `.env` (try 0.50 instead of 0.65)
- Restart bot

**2. Insufficient historical data**
- Bot needs 50+ candles for analysis
- Wait 5-10 minutes after startup
- Check logs: "Downloaded X candles for SYMBOL TIMEFRAME"

**3. Market conditions not favorable**
- Wyckoff/Elliott patterns are rare
- Check if any signals in database: `>signal BTC 1h`
- Consider adding more symbols or lower timeframes

**4. Analyzers disabled**
- Verify `ENABLE_WYCKOFF=true` and `ENABLE_ELLIOTT=true`
- Restart bot after changes

**5. Cooldown active**
- Check `SIGNAL_COOLDOWN_SECONDS` (default: 300s)
- Wait 5 minutes between signals per symbol

---

### Problem: WebSocket Disconnections

#### Symptoms
- Logs show: "WebSocket disconnected, reconnecting..."
- Frequent reconnection attempts

#### Causes & Solutions

**1. Network instability**
- Check internet connection
- If on VPS, verify network status with hosting provider

**2. Firewall blocking WebSocket**
- Ensure outbound connections to `fstream.binance.com` allowed
- Check corporate firewall settings

**3. Binance API maintenance**
- Check [Binance Status](https://www.binance.com/en/support/announcement)
- Bot will auto-reconnect when service restored

**4. Too many streams (>200)**
- Reduce number of symbols or timeframes
- Binance limits 200 streams per connection

---

### Problem: Discord Rate Limiting

#### Error: "429 Too Many Requests"

**Cause:** Sending messages too quickly

**Solutions:**
1. Bot has built-in 1-second delay between messages
2. If using multiple bots, coordinate timing
3. Increase `SIGNAL_COOLDOWN_SECONDS` to reduce frequency

---

### Problem: Database Errors

#### Error: "Duplicate key value violates unique constraint"

**Cause:** Trying to insert same candle twice

**Solution:**
- This is logged but non-fatal
- Bot continues processing
- If persistent, check for duplicate WebSocket streams

#### Error: "Permission denied for table signals"

**Cause:** Using anon key instead of service_role key

**Solution:**
- Update `.env` with `SUPABASE_SERVICE_KEY` (not anon key)
- Service role has full access, required for writes

#### Error: "Connection pool exhausted"

**Cause:** Too many concurrent database operations

**Solution:**
- Reduce number of symbols/timeframes
- Increase Supabase connection limit (requires paid plan)

---

### Problem: High Memory Usage

#### Cause:** Storing too many candles in memory

**Solutions:**
1. Reduce candle cache size in `candle_aggregator.py`:
   ```python
   self.max_candles = 200  # Default is 500
   ```
2. Enable Redis caching to share memory across instances
3. Restart bot periodically (e.g., daily cron job)

---

## 🚀 Deployment

### Option 1: bot-hosting.net

#### Step 1: Prepare Files

Ensure these files exist:
- `requirements.txt`
- `.env.example`
- `src/bot/main.py`

#### Step 2: Create Account

1. Sign up at [bot-hosting.net](https://bot-hosting.net)
2. Choose a plan (Basic should suffice)

#### Step 3: Upload Bot

1. Create new bot instance
2. Upload project files (or connect GitHub repo)
3. Set Python version to **3.11**

#### Step 4: Configure Environment

1. Go to "Environment Variables"
2. Add all variables from `.env`:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY`
   - `DISCORD_TOKEN`
   - etc.

#### Step 5: Set Start Command

```bash
python -m src.bot.main
```

#### Step 6: Start Bot

1. Click "Start Bot"
2. Monitor logs in web console
3. Check Discord for `/status` command

---

### Option 2: Self-Hosted VPS (Ubuntu)

#### Prerequisites
- Ubuntu 20.04+ server
- Root or sudo access
- Python 3.11+ installed

#### Step 1: Install Dependencies

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip git
```

#### Step 2: Clone Repository

```bash
git clone https://github.com/yourusername/wyeli-bot.git
cd wyeli-bot
```

#### Step 3: Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 4: Configure Environment

```bash
cp .env.example .env
nano .env  # Fill in your credentials
```

#### Step 5: Create Systemd Service

```bash
sudo nano /etc/systemd/system/wyeli-bot.service
```

Paste:
```ini
[Unit]
Description=Wyckoff-Elliott Trading Signals Bot
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/your-username/wyeli-bot
EnvironmentFile=/home/your-username/wyeli-bot/.env
ExecStart=/home/your-username/wyeli-bot/venv/bin/python -m src.bot.main
Restart=always
RestartSec=10
StandardOutput=append:/var/log/wyeli-bot.log
StandardError=append:/var/log/wyeli-bot-error.log

[Install]
WantedBy=multi-user.target
```

#### Step 6: Enable and Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable wyeli-bot
sudo systemctl start wyeli-bot
```

#### Step 7: Monitor Logs

```bash
# View logs
sudo journalctl -u wyeli-bot -f

# Or direct log files
tail -f /var/log/wyeli-bot.log
```

#### Step 8: Manage Service

```bash
# Stop bot
sudo systemctl stop wyeli-bot

# Restart bot
sudo systemctl restart wyeli-bot

# Check status
sudo systemctl status wyeli-bot
```

---

### Option 3: Docker (Advanced)

#### Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY .env .

# Run bot
CMD ["python", "-m", "src.bot.main"]
```

#### Build and Run:

```bash
docker build -t wyeli-bot .
docker run -d --name wyeli-bot --restart unless-stopped wyeli-bot
```

---

## 🔧 Maintenance

### Regular Tasks

#### Daily
- ✅ Check Discord for signals
- ✅ Run `>status` command
- ✅ Monitor error logs

#### Weekly
- ✅ Review signal performance in Supabase
- ✅ Check for Binance API changes
- ✅ Update dependencies (if needed)

#### Monthly
- ✅ Review and optimize MIN_CONFIDENCE
- ✅ Analyze backtest results
- ✅ Check Supabase storage usage (free tier: 500 MB)

### Updating the Bot

#### Local Development

```powershell
git pull origin main
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt --upgrade
python -m src.bot.main
```

#### Production (Systemd)

```bash
cd /home/your-username/wyeli-bot
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart wyeli-bot
```

### Database Maintenance

#### Vacuum Old Data (Optional)

If database grows too large, delete old candles:

```sql
-- Delete candles older than 90 days
DELETE FROM candles
WHERE open_time < NOW() - INTERVAL '90 days';

-- Vacuum to reclaim space
VACUUM ANALYZE candles;
```

---

## 🚨 Emergency Procedures

### Bot Crash / Won't Start

1. **Check Logs:**
   ```powershell
   # If running in terminal, check console output
   # If systemd: sudo journalctl -u wyeli-bot --no-pager -n 100
   ```

2. **Verify Configuration:**
   ```powershell
   python -c "from src.bot.config import Config; Config.from_env().validate()"
   ```

3. **Test Database Connection:**
   ```powershell
   python -c "from src.storage.supabase_client import SupabaseClient; import asyncio; asyncio.run(SupabaseClient().get_recent_signals('BTCUSDT', '1h', 1))"
   ```

4. **Restart Bot:**
   - Local: Press Ctrl+C, then run again
   - Systemd: `sudo systemctl restart wyeli-bot`

### Accidental Trading Enabled

**If you accidentally enabled trading and need to stop:**

1. **Immediate Stop:**
   ```powershell
   # Kill bot process
   Get-Process python | Stop-Process -Force
   ```

2. **Verify in Binance:**
   - Log into Binance account
   - Check open positions
   - Manually close if needed

3. **Disable Trading:**
   ```env
   ENABLE_TRADING=false
   ```

4. **Restart Safely:**
   - Verify `ENABLE_TRADING=false`
   - Restart bot

### Database Corruption

1. **Verify Tables Exist:**
   ```sql
   SELECT table_name FROM information_schema.tables
   WHERE table_schema = 'public';
   ```

2. **Re-run Migration if Needed:**
   - Go to Supabase SQL Editor
   - Run `src/storage/migrations/001_create_schema.sql`

3. **Restore from Backup (if available):**
   - Supabase automatic backups available on paid plans

### Discord Token Leaked

**If your Discord token is exposed publicly:**

1. **Immediate Revocation:**
   - Go to Discord Developer Portal
   - Bot → Reset Token
   - Copy new token

2. **Update Environment:**
   ```env
   DISCORD_TOKEN=new-token-here
   ```

3. **Restart Bot:**
   ```powershell
   python -m src.bot.main
   ```

4. **Audit Logs:**
   - Check Discord server audit logs for unauthorized activity

---

## 📞 Support

If issues persist:

1. **Check Documentation:**
   - README.md
   - ARCHITECTURE.md
   - SECURITY.md

2. **Search GitHub Issues:**
   - [GitHub Issues](https://github.com/yourusername/wyeli-bot/issues)

3. **Ask Community:**
   - [GitHub Discussions](https://github.com/yourusername/wyeli-bot/discussions)

4. **Create Issue:**
   - Provide logs, configuration (redact secrets!), and steps to reproduce

---

**Remember:** Always test changes in a development environment before deploying to production!
