# Wyckoff-Elliott Discord Trading Signals Bot

[![CI](https://github.com/yourusername/wyeli-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/wyeli-bot/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production-quality Discord bot that generates cryptocurrency trading signals using **Wyckoff Method** and **Elliott Wave** analysis. Designed for **alerts-only** mode (no automated trading by default) with optional trading capabilities for advanced users.

## ⚠️ **DISCLAIMER**

**THIS BOT IS FOR EDUCATIONAL PURPOSES ONLY. NOT FINANCIAL ADVICE.**

Trading cryptocurrencies carries significant risk. Past performance does not guarantee future results. Always conduct your own research and never invest more than you can afford to lose.

---

## 🚀 Features

- **🔍 Multi-Method Analysis**
  - Wyckoff Method (accumulation, distribution, springs, upthrusts)
  - Elliott Wave counting (impulse & corrective patterns)
  - Technical indicators (RSI, EMA, VWAP, MACD, ATR)
  - Confidence scoring and signal fusion

- **📊 Market Data**
  - Binance Futures public REST & WebSocket streams (no API key needed)
  - Real-time candle aggregation and processing
  - Multi-symbol and multi-timeframe support

- **💾 Database & Realtime**
  - Supabase (PostgreSQL) for data persistence
  - Supabase Realtime for event broadcasting
  - Efficient caching with optional Redis support

- **🤖 Discord Integration**
  - Rich signal embeds with entry, stop-loss, and take-profit levels
  - Slash commands (`/status`, `/lastsignal`, `/subscribe`, `/backtest`)
  - Rate-limited notifications

- **📈 Backtesting**
  - Simple backtesting engine with performance metrics
  - Jupyter notebook for analysis and visualization
  - Parameter optimization tools

- **🛡️ Security**
  - Environment-based configuration (no secrets in code)
  - Trading module disabled by default
  - Testnet support for safe testing

---

## 📁 Project Structure

```
WyEli_Bot/
├── .github/workflows/       # CI/CD configuration
├── .vscode/                 # VS Code launch configurations
├── docs/                    # Documentation
│   ├── ARCHITECTURE.md
│   ├── RUNBOOK.md
│   └── SECURITY.md
├── examples/                # Example scripts and configs
├── src/
│   ├── bot/                 # Core bot modules
│   │   ├── config.py        # Configuration management
│   │   ├── logger.py        # Structured logging
│   │   └── main.py          # Main entrypoint
│   ├── ingest/              # Data ingestion
│   │   ├── binance_rest.py  # REST API client
│   │   ├── binance_ws.py    # WebSocket manager
│   │   └── candle_aggregator.py
│   ├── signals/             # Signal generation
│   │   ├── wyckoff.py       # Wyckoff analysis
│   │   ├── elliott.py       # Elliott Wave analysis
│   │   ├── indicators.py    # Technical indicators
│   │   └── fuse.py          # Signal fusion
│   ├── storage/             # Database layer
│   │   ├── supabase_client.py
│   │   ├── models.py
│   │   └── migrations/      # SQL migrations
│   ├── discord/             # Discord integration
│   │   ├── notifier.py      # Message sender
│   │   └── commands.py      # Slash commands
│   ├── backtest/            # Backtesting
│   │   ├── engine.py
│   │   └── sample_notebook.ipynb
│   └── utils/               # Utilities
│       ├── time_utils.py
│       └── metrics.py
├── tests/                   # Unit tests
├── .env.example             # Environment template
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🔧 Setup Instructions

### 1. Prerequisites

- **Python 3.11+**
- **Supabase account** (free tier works)
- **Discord bot token**
- **Git**

### 2. Clone Repository

```powershell
git clone https://github.com/yourusername/wyeli-bot.git
cd wyeli-bot
```

### 3. Create Virtual Environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows PowerShell
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Set Up Supabase

1. Create a new project at [supabase.com](https://supabase.com)
2. Go to SQL Editor and run `src/storage/migrations/001_create_schema.sql`
3. Copy your project URL and service role key

### 5. Set Up Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" → Create bot → Copy token
4. Enable these **Privileged Gateway Intents**:
   - **Message Content Intent** (REQUIRED for prefix commands)
   - Server Members Intent (optional)
5. Go to "OAuth2" → "URL Generator"
   - Scopes: `bot`
   - Bot Permissions: `Send Messages`, `Embed Links`, `Read Message History`
6. Use the generated URL to add the bot to your server

### 6. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```powershell
cp .env.example .env
```

Edit `.env`:

```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key-here

# Discord
DISCORD_TOKEN=your-discord-bot-token-here
DISCORD_GUILD_ID=your-guild-id-for-slash-commands
DISCORD_SIGNALS_CHANNEL_ID=channel-id-for-signal-alerts

# Symbols & Timeframes
SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT
TIMEFRAMES=15m,1h,4h

# Signal Settings
MIN_CONFIDENCE=0.65
ENABLE_WYCKOFF=true
ENABLE_ELLIOTT=true

# Trading (DISABLED by default)
ENABLE_TRADING=false
```

### 7. Run the Bot

#### Option A: Using VS Code

1. Open the project in VS Code
2. Press `F5` or go to Run → Start Debugging
3. Select "Run Bot (dev)" configuration

#### Option B: Command Line

```powershell
python -m src.bot.main
```

The bot will:
1. Connect to Supabase
2. Download historical candles
3. Start WebSocket streams
4. Connect to Discord
5. Begin monitoring for signals

---

## 🎯 Usage

### Available Commands

The bot uses **prefix commands** with `>` as the command prefix.

#### Main Commands:

- **`>signal <symbol> [timeframe]`** - Get the latest signal for a cryptocurrency
  - Examples: 
    - `>signal BTC` (default 1h timeframe)
    - `>signal ETH 4h`
    - `>signal BNB 15m`
  - Supported symbols: BTC, ETH, BNB, SOL, ADA (USDT is added automatically)
  - Timeframes: 15m, 1h, 4h, 1d

- **`>status`** - Show bot status and statistics

- **`>signals [limit]`** - Show recent signals across all symbols (up to 20)

- **`>help`** - Show command help

### Signal Format

Signals are posted as rich embeds containing:
- **Direction**: LONG 🚀 or SHORT 📉
- **Entry Price**: Suggested entry point
- **Stop Loss**: Risk management level
- **Take Profit**: Target price
- **Confidence Score**: 0-100%
- **Analysis Details**: Wyckoff phase, Elliott wave count, indicators
- **Risk/Reward Ratio**

---

## 🧪 Testing

### Run All Tests

```powershell
pytest tests/ -v --cov=src --cov-report=term-missing
```

### Run Specific Test

```powershell
pytest tests/test_wyckoff.py -v
```

### Code Quality

```powershell
# Format code
black src tests

# Lint code
flake8 src tests

# Type check
mypy src --ignore-missing-imports
```

---

## 📊 Backtesting

### Using Jupyter Notebook

1. Open `src/backtest/sample_notebook.ipynb` in VS Code or Jupyter
2. Follow the step-by-step cells to:
   - Load historical data
   - Run backtest
   - Visualize results
   - Optimize parameters

### Programmatic Backtesting

```python
import asyncio
from src.backtest.engine import BacktestEngine, print_backtest_results
from src.ingest.binance_rest import BinanceRESTClient

async def run_backtest():
    # Load data
    binance = BinanceRESTClient()
    candles = await binance.get_historical_klines(
        symbol="BTCUSDT",
        interval="1h",
        limit=1000
    )
    
    # Run backtest
    engine = BacktestEngine(initial_balance=10000.0)
    results = await engine.run_backtest(
        candles=candles,
        symbol="BTCUSDT",
        timeframe="1h",
        min_confidence=0.65
    )
    
    # Print results
    print_backtest_results(results)

asyncio.run(run_backtest())
```

---

## 🔒 Enabling Trading (Advanced)

**⚠️ WARNING: Trading is DISABLED by default. Enable at your own risk.**

### Step 1: Use Testnet First

1. Create a testnet account at [https://testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Generate API keys
3. Update `.env`:

```env
ENABLE_TRADING=true
BINANCE_API_KEY=your-testnet-api-key
BINANCE_API_SECRET=your-testnet-api-secret
BINANCE_TESTNET=true
```

### Step 2: Test Thoroughly

- Run for at least 1-2 weeks on testnet
- Monitor all signals and performance
- Verify risk management works correctly

### Step 3: Go Live (Optional)

1. Create real Binance Futures API keys with **restricted permissions**:
   - ✅ Enable Trading
   - ❌ Enable Withdrawals (NEVER enable)
   - ✅ Restrict to specific IPs
2. Update `.env` with real keys and set `BINANCE_TESTNET=false`

**IMPORTANT**: Start with small position sizes!

---

## 🚀 Deployment (bot-hosting.net or similar)

### Preparation

1. Ensure all secrets are in environment variables
2. Test locally first
3. Create a `Procfile` or startup script

### Example Systemd Service

```ini
[Unit]
Description=Wyckoff-Elliott Trading Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/home/botuser/wyeli-bot
EnvironmentFile=/home/botuser/wyeli-bot/.env
ExecStart=/home/botuser/wyeli-bot/venv/bin/python -m src.bot.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### bot-hosting.net Notes

- Use their environment variable management
- Ensure WebSocket connections are allowed
- Monitor logs for reconnection attempts
- Set up health checks if available

See `docs/RUNBOOK.md` for detailed deployment instructions.

---

## 📚 Documentation

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design and component details
- **[RUNBOOK.md](docs/RUNBOOK.md)** - Operational procedures and troubleshooting
- **[SECURITY.md](docs/SECURITY.md)** - Security best practices

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Ensure tests pass and code is formatted before submitting.

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Wyckoff Method by Richard D. Wyckoff
- Elliott Wave Principle by Ralph Nelson Elliott
- Binance API Documentation
- Supabase Team
- Discord.py Community

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/wyeli-bot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/wyeli-bot/discussions)

---

**Remember**: This is an educational tool. Always do your own research and trade responsibly!

🌟 If you find this project helpful, consider giving it a star!
