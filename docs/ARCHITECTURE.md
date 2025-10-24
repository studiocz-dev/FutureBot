# Architecture Overview

This document describes the high-level architecture, design patterns, and technical decisions behind the Wyckoff-Elliott Trading Signals Bot.

---

## 🎯 Design Principles

1. **Separation of Concerns**: Each module has a single, well-defined responsibility
2. **Async-First**: All I/O operations use `asyncio` for concurrent processing
3. **Fail-Safe**: Trading disabled by default; extensive error handling
4. **Testability**: Dependency injection and mocking for unit tests
5. **Observability**: Structured JSON logging with contextual fields
6. **Scalability**: Stateless signal generation; horizontal scaling possible

---

## 📊 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Discord (User Interface)                │
│  ┌──────────────┐                        ┌──────────────┐  │
│  │   Notifier   │ ◄─── Signal Embeds ────┤   Commands   │  │
│  └──────┬───────┘                        └──────▲───────┘  │
│         │                                        │           │
└─────────┼────────────────────────────────────────┼───────────┘
          │                                        │
          │ Send Signal                            │ User Input
          ▼                                        │
┌─────────────────────────────────────────────────┼───────────┐
│                    Core Bot (main.py)           │           │
│  ┌───────────────────────────────────────────────────────┐ │
│  │              TradingBot Orchestrator                  │ │
│  │  • Coordinates all subsystems                         │ │
│  │  • Manages async lifecycle                            │ │
│  │  • Handles graceful shutdown                          │ │
│  └───┬────────────────────────┬────────────────────┬─────┘ │
│      │                        │                    │        │
└──────┼────────────────────────┼────────────────────┼────────┘
       │                        │                    │
       │ Config                 │ Candles            │ Signals
       ▼                        ▼                    ▼
┌─────────────┐       ┌─────────────────┐  ┌─────────────────┐
│   Config    │       │  Candle         │  │  Signal Fuser   │
│   Loader    │       │  Aggregator     │  │  (Fusion Logic) │
└─────────────┘       └────────┬────────┘  └────────┬────────┘
                              │                      │
                              │ New Candle           │ Generate
                              ▼                      ▼
                    ┌──────────────────┐   ┌─────────────────┐
                    │ Binance WebSocket│   │   Wyckoff       │
                    │     Manager      │   │   Elliott       │
                    └──────────────────┘   │   Indicators    │
                              ▲            └────────┬────────┘
                              │                     │
                              │ Stream Data         │ Analysis
                              │                     ▼
┌─────────────────────────────┼──────────────────────────────┐
│                    Data Layer                     │         │
│  ┌─────────────────┐                    ┌─────────┴──────┐ │
│  │  Binance REST   │                    │    Supabase    │ │
│  │   (Historical)  │                    │  (PostgreSQL)  │ │
│  └─────────────────┘                    └────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔧 Module Breakdown

### 1. **Bot Core** (`src/bot/`)

#### `main.py` - Orchestrator
**Responsibilities:**
- Initialize all subsystems (Supabase, Binance clients, signal fuser, Discord bot)
- Download historical candles on startup (default: 500 candles)
- Register callback for candle close events
- Coordinate graceful shutdown with signal handlers

**Key Components:**
```python
class TradingBot:
    async def start()              # Main entrypoint
    async def _startup()           # Initialize subsystems
    async def _on_candle_close()   # Triggered on each candle close
    async def shutdown()           # Cleanup resources
```

**Data Flow:**
1. Load configuration from `.env`
2. Connect to Supabase
3. Initialize Binance REST client
4. Download historical data for each symbol/timeframe
5. Start WebSocket streams
6. Register candle close callback → signal generation
7. Start Discord bot

#### `config.py` - Configuration Management
**Responsibilities:**
- Define Pydantic models for type-safe configuration
- Validate required environment variables
- Provide factory methods for loading from `.env`

**Configuration Classes:**
- `SupabaseConfig`: Database connection
- `DiscordConfig`: Bot token, guild ID, channel IDs
- `BinanceConfig`: API keys (optional), testnet mode
- `TradingConfig`: Enable/disable trading, position size
- `SignalsConfig`: Min confidence, enabled methods
- `CacheConfig`: Redis settings (optional)
- `LoggingConfig`: Log level, format
- `WebSocketConfig`: Reconnection, backoff
- `BacktestConfig`: Initial balance, commission

#### `logger.py` - Structured Logging
**Responsibilities:**
- JSON logging with contextual fields
- Log level management
- Thread-safe logging with adapters

**Features:**
- `LoggerAdapter` for per-request context injection
- Example: `logger.info("Signal generated", extra={"symbol": "BTCUSDT", "confidence": 0.85})`

---

### 2. **Data Ingestion** (`src/ingest/`)

#### `binance_rest.py` - REST API Client
**Responsibilities:**
- Fetch historical klines (OHLCV candles)
- Rate limiting with token bucket algorithm
- Retry logic with exponential backoff

**Key Methods:**
```python
async def get_historical_klines(symbol, interval, limit)
async def get_exchange_info()
async def _request_with_retry()  # Exponential backoff
```

**Rate Limiting:**
- 1200 requests/minute (Binance public API limit)
- Token bucket refills at 20 tokens/second
- Blocks when bucket empty

#### `binance_ws.py` - WebSocket Manager
**Responsibilities:**
- Maintain persistent WebSocket connections
- Handle reconnection with exponential backoff (5s → 60s max)
- Parse and forward kline messages to candle aggregator

**Reconnection Strategy:**
```python
backoff = min(5 * (2 ** retry_count), 60)  # Exponential with cap
```

**Message Handling:**
```python
async def _handle_kline_message(data):
    if data['k']['x']:  # Candle closed
        candle_aggregator.process_candle(candle)
```

#### `candle_aggregator.py` - Candle State Manager
**Responsibilities:**
- Aggregate incoming ticks into complete candles
- Detect candle close events (by tracking `open_time` changes)
- Maintain rolling window of recent candles (default: 500)
- Persist candles to database asynchronously

**Callback Pattern:**
```python
aggregator.on_candle_close(callback_fn)  # Register callback
# Callback signature: async def callback(symbol, timeframe, candle)
```

**Storage:**
- In-memory cache: `Dict[tuple, List[Candle]]` keyed by `(symbol, timeframe)`
- Async DB persistence: Non-blocking writes to Supabase

---

### 3. **Signal Generation** (`src/signals/`)

#### `wyckoff.py` - Wyckoff Method Analyzer
**Responsibilities:**
- Phase detection (Accumulation, Distribution, Markup, Markdown)
- Pattern recognition (Springs, Upthrusts)
- Volume confirmation analysis

**Analysis Pipeline:**
```python
1. _detect_phase()
   - Track price range and volume trends
   - Identify sideways vs trending markets
   
2. _detect_spring() / _detect_upthrust()
   - Find failed breakouts/breakdowns
   - Validate with volume surge (>1.5x average)
   - Calculate confidence (0.5-1.0)
   
3. generate_signal()
   - Return SignalResult with direction, confidence, rationale
```

**Confidence Scoring:**
- Spring with high volume: 0.9-1.0
- Spring with normal volume: 0.6-0.75
- Weak spring: 0.5-0.6

#### `elliott.py` - Elliott Wave Analyzer
**Responsibilities:**
- Pivot detection (swing highs/lows)
- 5-wave impulse pattern recognition
- ABC corrective pattern recognition
- Fibonacci ratio validation

**Wave Rules (Impulse):**
- Wave 2 cannot retrace >100% of Wave 1
- Wave 3 cannot be shortest of waves 1, 3, 5
- Wave 4 cannot overlap Wave 1 price territory
- Wave 5 often extends to 1.618x Wave 1

**Wave Rules (Correction):**
- Wave B typically 0.8-1.0x Wave A
- Wave C often 1.0-1.618x Wave A

**Analysis Pipeline:**
```python
1. _find_pivots(window=5)
   - Identify local extrema
   
2. _find_impulse_pattern()
   - Scan for 5-wave sequences
   - Validate against Elliott rules
   
3. _find_correction_pattern()
   - Scan for ABC sequences
   - Check Fibonacci ratios
   
4. generate_signal()
   - Return direction based on completed wave
```

#### `indicators.py` - Technical Indicators
**Responsibilities:**
- Calculate popular indicators (RSI, EMA, VWAP, MACD, ATR, Bollinger Bands)
- Provide confirmation for Wyckoff/Elliott signals

**Indicators Calculated:**
```python
- RSI(14): Momentum (oversold <30, overbought >70)
- EMA(20, 50, 200): Trend direction
- VWAP: Intraday fair value
- MACD(12, 26, 9): Trend momentum
- ATR(14): Volatility for stop-loss calculation
- Bollinger Bands(20, 2): Volatility squeeze
```

**Confirmation Logic:**
```python
def confirm_long(indicators):
    return (
        indicators['rsi'] < 40 and          # Oversold
        indicators['close'] > indicators['ema_20'] and  # Above fast EMA
        indicators['ema_20'] > indicators['ema_50'] and # Bullish trend
        indicators['macd'] > indicators['macd_signal']  # Bullish momentum
    )
```

#### `fuse.py` - Signal Fusion Engine
**Responsibilities:**
- Combine Wyckoff + Elliott + Indicators into final signal
- Calculate confidence score
- Determine entry, stop-loss, take-profit levels
- Cooldown management (prevent duplicate signals)
- Persist signals to database

**Fusion Logic:**
```python
1. Run all analyzers in parallel:
   - Wyckoff analysis
   - Elliott analysis
   - Indicator confirmation
   
2. Check agreement:
   - If 2+ methods agree on direction → HIGH confidence
   - If 1 method >0.75 confidence → MEDIUM confidence
   - Otherwise → NO signal
   
3. Calculate levels:
   - Stop Loss: Entry ± (2 * ATR)
   - Take Profit 1: Entry ± (4 * ATR)
   - Take Profit 2: Entry ± (6 * ATR)
   - Take Profit 3: Entry ± (8 * ATR)
   
4. Check cooldown:
   - No signal if last signal for this symbol/timeframe <5 minutes ago
   
5. Persist to database:
   - Insert into signals table
   - Trigger Supabase Realtime broadcast
```

**Confidence Calculation:**
```python
confidence = (wyckoff_conf + elliott_conf + indicator_conf) / 3
if all_agree:
    confidence = min(confidence * 1.2, 1.0)  # Boost if aligned
```

---

### 4. **Storage Layer** (`src/storage/`)

#### `supabase_client.py` - Database Client
**Responsibilities:**
- Wrapper around Supabase Python SDK
- Async operations for all queries
- Error handling and retry logic

**Key Methods:**
```python
async def insert_candle(candle)
async def insert_signal(signal)
async def get_recent_signals(symbol, timeframe, limit)
async def get_latest_candle(symbol, timeframe)
async def insert_backtest_result(result)
```

#### `models.py` - Data Models
**Responsibilities:**
- Define Pydantic models for type safety
- Validation and serialization

**Models:**
```python
class Candle(BaseModel): symbol, timeframe, open_time, OHLCV, trades
class Signal(BaseModel): symbol, timeframe, direction, entry, SL, TP, confidence
class BacktestResult(BaseModel): symbol, timeframe, trades, win_rate, pnl, max_drawdown
```

#### Database Schema (`migrations/001_create_schema.sql`)

**Tables:**
1. **symbols**: Trading pairs metadata
2. **candles**: OHLCV data with composite index `(symbol_id, timeframe, open_time)`
3. **signals**: Generated signals with rationale
4. **backtests**: Historical backtest results
5. **user_subscriptions**: User notification preferences
6. **signal_performance**: Signal outcome tracking

**Views:**
- `v_recent_signals`: Last 100 signals with symbol names
- `v_signal_stats`: Aggregated statistics per symbol/timeframe

**Row Level Security (RLS):**
- `service_role` has full access
- Public access disabled by default
- Policies for future user-level access

**Realtime:**
- `signals` table published to Realtime channel
- Enables external apps to subscribe to signals

---

### 5. **Discord Integration** (`src/discord/`)

#### `notifier.py` - Message Sender
**Responsibilities:**
- Format signals as rich embeds
- Send to configured channel
- Rate limiting (1 message/second)

**Embed Format:**
```python
Embed(
    title="🚀 LONG SIGNAL - BTCUSDT (1h)",
    color=0x00ff00,  # Green for LONG, Red for SHORT
    fields=[
        {"Entry": "50,000.00 USDT"},
        {"Stop Loss": "49,500.00 USDT"},
        {"Take Profit 1": "51,000.00 USDT"},
        {"Confidence": "85%"},
        {"Wyckoff": "Accumulation Spring"},
        {"Elliott": "Wave 5 Impulse Complete"},
        {"R:R Ratio": "2.0"}
    ],
    timestamp=datetime.utcnow()
)
```

#### `commands.py` - Slash Commands
**Responsibilities:**
- Register application commands with Discord
- Handle user interactions
- Query database for historical data

**Commands:**
- `/status`: Show bot uptime, signals sent, websocket status
- `/lastsignal <symbol> <timeframe>`: Retrieve recent signal from DB
- `/subscribe <symbol>`: Add user to notification list (placeholder)
- `/unsubscribe <symbol>`: Remove user from notifications (placeholder)
- `/backtest <symbol> <timeframe> [days]`: Run historical backtest (placeholder)
- `/help`: Display command reference

---

### 6. **Backtesting** (`src/backtest/`)

#### `engine.py` - Backtest Engine
**Responsibilities:**
- Simulate signal generation on historical data
- Track open positions and executions
- Calculate performance metrics

**Backtest Flow:**
```python
1. Load historical candles
2. For each candle:
   a. Generate signals (Wyckoff + Elliott)
   b. Check if signal meets min_confidence
   c. Open position at entry price
   d. Track position through subsequent candles
   e. Close at TP or SL
3. Calculate results:
   - Total trades
   - Win rate
   - PnL %
   - Max drawdown
   - Average R:R
```

**Limitations:**
- Assumes instant fills at specified prices (no slippage)
- No order book simulation
- No fee modeling (can add commission parameter)

#### `sample_notebook.ipynb` - Jupyter Analysis
**Responsibilities:**
- Interactive backtesting workflow
- Visualization of results
- Parameter optimization

**Cells:**
1. Setup: Load environment, import modules
2. Data Loading: Fetch historical candles from Binance
3. Run Backtest: Execute with configurable parameters
4. Visualize: Plot equity curve, drawdown, trade PnL
5. Optimize: Grid search over confidence thresholds
6. Summary: Display best parameters

---

### 7. **Utilities** (`src/utils/`)

#### `time_utils.py` - Time Conversion
**Responsibilities:**
- Convert between Binance timestamps and datetime
- Handle timezone conversions

**Functions:**
```python
def binance_timestamp_to_datetime(ts: int) -> datetime
def datetime_to_binance_timestamp(dt: datetime) -> int
def is_candle_closed(current_time, candle_open_time, interval)
```

#### `metrics.py` - Performance Tracking
**Responsibilities:**
- Track bot performance metrics
- Calculate signal statistics

**Metrics:**
- Signals generated per symbol/timeframe
- Average confidence scores
- Signal generation latency
- WebSocket reconnection count

---

## 🔄 Data Flow

### Signal Generation Pipeline

```
1. WebSocket Receives Kline Data
   ↓
2. Candle Aggregator Processes Tick
   ↓
3. Detect Candle Close (by open_time change)
   ↓
4. Trigger on_candle_close Callback
   ↓
5. Signal Fuser.generate_signal()
   ├─ Wyckoff Analyzer (parallel)
   ├─ Elliott Analyzer (parallel)
   └─ Indicators Calculator (parallel)
   ↓
6. Fuse Results
   - Check confidence threshold
   - Calculate SL/TP levels
   - Check cooldown
   ↓
7. Persist to Database
   ↓
8. Send Discord Notification
```

### Startup Sequence

```
1. Load Config from .env
   ↓
2. Initialize Logger
   ↓
3. Connect to Supabase
   ↓
4. Initialize Binance REST Client
   ↓
5. For each symbol/timeframe:
   a. Download 500 historical candles
   b. Populate candle aggregator cache
   ↓
6. Initialize WebSocket Manager
   ↓
7. Start WebSocket Streams
   ↓
8. Register Candle Close Callback
   ↓
9. Start Discord Bot
   ↓
10. Wait for SIGINT (Ctrl+C)
   ↓
11. Graceful Shutdown
```

### Shutdown Sequence

```
1. Receive SIGINT Signal
   ↓
2. Set shutdown_event
   ↓
3. Close WebSocket Connections
   ↓
4. Flush pending DB writes
   ↓
5. Close Discord Bot
   ↓
6. Close Supabase Client
   ↓
7. Exit
```

---

## 🛠️ Technology Choices

### Why Python?
- Rich ecosystem for data analysis (pandas, NumPy)
- Excellent async support (`asyncio`)
- Popular in trading/finance domain

### Why Supabase?
- Managed PostgreSQL (reduced ops overhead)
- Realtime WebSocket broadcasts
- Built-in authentication (future feature)
- Free tier suitable for development

### Why Discord?
- Easy to set up (no web hosting needed)
- Real-time notifications
- Slash commands for user interaction
- Large user base familiar with interface

### Why Async?
- Efficiently handle multiple WebSocket streams
- Non-blocking database operations
- Concurrent signal generation for multiple symbols

### Why Modular Design?
- Testability: Each module can be tested independently
- Maintainability: Changes isolated to specific modules
- Extensibility: Easy to add new analyzers or data sources

---

## 🔮 Future Enhancements

### Planned Features
1. **Machine Learning**: Train models on historical signals
2. **Multi-Exchange**: Support Bybit, OKX, etc.
3. **Web Dashboard**: Real-time monitoring UI
4. **Advanced Backtesting**: Order book simulation, realistic fills
5. **Portfolio Management**: Multi-symbol position sizing
6. **Sentiment Analysis**: Social media + news integration

### Scalability Considerations
- **Horizontal Scaling**: Run multiple bot instances with different symbols
- **Redis Caching**: Share candle data across instances
- **Message Queue**: Decouple signal generation from notification
- **Database Sharding**: Partition by symbol or timeframe

---

## 📖 References

- [Wyckoff Method](https://school.stockcharts.com/doku.php?id=market_analysis:the_wyckoff_method)
- [Elliott Wave Principle](https://www.investopedia.com/terms/e/elliottwavetheory.asp)
- [Binance API Documentation](https://binance-docs.github.io/apidocs/futures/en/)
- [Supabase Documentation](https://supabase.com/docs)
- [Discord.py Documentation](https://discordpy.readthedocs.io/)

---

## 🤔 Architectural Decisions

### Why No Redis by Default?
- Added complexity for single-instance deployment
- In-memory cache sufficient for most use cases
- Redis remains optional for multi-instance setups

### Why Service Role Key?
- Bot needs full database access for writes
- RLS policies not needed for server-side bot
- Future: Implement anon key for read-only operations

### Why Cooldown Mechanism?
- Prevents signal spam during volatile markets
- Reduces Discord rate limit risk
- Configurable per use case

### Why Confidence Threshold?
- Filters low-quality signals
- Allows users to tune signal frequency
- Higher threshold = fewer, higher-quality signals

---

This architecture balances simplicity with extensibility, making it suitable for both educational use and potential production deployment with appropriate safeguards.
