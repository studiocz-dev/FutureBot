-- ============================================================================
-- Wyckoff-Elliott Trading Bot - Database Schema
-- ============================================================================
-- This migration creates the initial database schema for the trading bot.
-- Run this SQL in your Supabase SQL editor.
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- SYMBOLS TABLE
-- ============================================================================
-- Stores trading symbols configuration
CREATE TABLE IF NOT EXISTS symbols (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) NOT NULL UNIQUE,
    exchange VARCHAR(50) DEFAULT 'BINANCE_FUTURES',
    quote_asset VARCHAR(10) DEFAULT 'USDT',
    active BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_symbols_active ON symbols(active);
CREATE INDEX idx_symbols_symbol ON symbols(symbol);

-- ============================================================================
-- CANDLES TABLE
-- ============================================================================
-- Stores historical and real-time candlestick data
CREATE TABLE IF NOT EXISTS candles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol_id UUID NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    timeframe VARCHAR(10) NOT NULL,
    open_time BIGINT NOT NULL,
    close_time BIGINT NOT NULL,
    open DECIMAL(20, 8) NOT NULL,
    high DECIMAL(20, 8) NOT NULL,
    low DECIMAL(20, 8) NOT NULL,
    close DECIMAL(20, 8) NOT NULL,
    volume DECIMAL(20, 8) NOT NULL,
    quote_volume DECIMAL(20, 8),
    trades INTEGER,
    taker_buy_base DECIMAL(20, 8),
    taker_buy_quote DECIMAL(20, 8),
    json_raw JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(symbol_id, timeframe, open_time)
);

-- Composite index for efficient queries
CREATE INDEX idx_candles_symbol_timeframe_time ON candles(symbol_id, timeframe, open_time DESC);
CREATE INDEX idx_candles_open_time ON candles(open_time DESC);
CREATE INDEX idx_candles_symbol_timeframe ON candles(symbol_id, timeframe);

-- ============================================================================
-- SIGNALS TABLE
-- ============================================================================
-- Stores generated trading signals
CREATE TABLE IF NOT EXISTS signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol_id UUID NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    timeframe VARCHAR(10) NOT NULL,
    signal_type VARCHAR(10) NOT NULL CHECK (signal_type IN ('LONG', 'SHORT')),
    entry_price DECIMAL(20, 8) NOT NULL,
    stop_loss DECIMAL(20, 8),
    take_profit DECIMAL(20, 8),
    take_profit_2 DECIMAL(20, 8),
    take_profit_3 DECIMAL(20, 8),
    confidence DECIMAL(5, 4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    wyckoff_phase VARCHAR(50),
    elliott_wave_count VARCHAR(50),
    indicators JSONB DEFAULT '{}',
    rationale TEXT,
    payload_json JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'HIT', 'STOPPED', 'CANCELLED')),
    discord_message_id VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_signals_symbol_timeframe ON signals(symbol_id, timeframe);
CREATE INDEX idx_signals_created_at ON signals(created_at DESC);
CREATE INDEX idx_signals_status ON signals(status);
CREATE INDEX idx_signals_confidence ON signals(confidence DESC);

-- ============================================================================
-- BACKTESTS TABLE
-- ============================================================================
-- Stores backtest configurations and results
CREATE TABLE IF NOT EXISTS backtests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    symbols TEXT[] NOT NULL,
    timeframes TEXT[] NOT NULL,
    initial_balance DECIMAL(20, 8) NOT NULL,
    params_json JSONB NOT NULL,
    results_json JSONB,
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    win_rate DECIMAL(5, 4),
    total_pnl DECIMAL(20, 8),
    max_drawdown DECIMAL(20, 8),
    sharpe_ratio DECIMAL(10, 4),
    status VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_backtests_status ON backtests(status);
CREATE INDEX idx_backtests_created_at ON backtests(created_at DESC);

-- ============================================================================
-- USER SUBSCRIPTIONS TABLE
-- ============================================================================
-- Stores Discord user preferences for signal notifications
CREATE TABLE IF NOT EXISTS user_subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    discord_user_id VARCHAR(50) NOT NULL,
    discord_username VARCHAR(100),
    symbol_id UUID REFERENCES symbols(id) ON DELETE CASCADE,
    timeframes TEXT[],
    min_confidence DECIMAL(5, 4) DEFAULT 0.65,
    preferences_json JSONB DEFAULT '{}',
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(discord_user_id, symbol_id)
);

CREATE INDEX idx_subscriptions_user ON user_subscriptions(discord_user_id);
CREATE INDEX idx_subscriptions_active ON user_subscriptions(active);

-- ============================================================================
-- SIGNAL PERFORMANCE TABLE
-- ============================================================================
-- Tracks signal performance for analytics
CREATE TABLE IF NOT EXISTS signal_performance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    signal_id UUID NOT NULL REFERENCES signals(id) ON DELETE CASCADE,
    hit_tp1 BOOLEAN DEFAULT false,
    hit_tp2 BOOLEAN DEFAULT false,
    hit_tp3 BOOLEAN DEFAULT false,
    hit_sl BOOLEAN DEFAULT false,
    pnl_percent DECIMAL(10, 4),
    duration_minutes INTEGER,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_performance_signal ON signal_performance(signal_id);

-- ============================================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER update_symbols_updated_at BEFORE UPDATE ON symbols
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_signals_updated_at BEFORE UPDATE ON signals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON user_subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================
-- Enable RLS on all tables
ALTER TABLE symbols ENABLE ROW LEVEL SECURITY;
ALTER TABLE candles ENABLE ROW LEVEL SECURITY;
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE backtests ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE signal_performance ENABLE ROW LEVEL SECURITY;

-- Policy: Service role has full access
CREATE POLICY "Service role has full access" ON symbols
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role has full access" ON candles
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role has full access" ON signals
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role has full access" ON backtests
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role has full access" ON user_subscriptions
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role has full access" ON signal_performance
    FOR ALL USING (auth.role() = 'service_role');

-- Policy: Anon/authenticated users can read public data
CREATE POLICY "Public read access to symbols" ON symbols
    FOR SELECT USING (active = true);

CREATE POLICY "Public read access to signals" ON signals
    FOR SELECT USING (true);

CREATE POLICY "Public read access to candles" ON candles
    FOR SELECT USING (true);

-- ============================================================================
-- SEED DATA
-- ============================================================================
-- Insert default symbols
INSERT INTO symbols (symbol, exchange, quote_asset, active) VALUES
    ('BTCUSDT', 'BINANCE_FUTURES', 'USDT', true),
    ('ETHUSDT', 'BINANCE_FUTURES', 'USDT', true),
    ('BNBUSDT', 'BINANCE_FUTURES', 'USDT', true)
ON CONFLICT (symbol) DO NOTHING;

-- ============================================================================
-- VIEWS (Optional - for analytics)
-- ============================================================================

-- View: Recent signals with symbol info
CREATE OR REPLACE VIEW v_recent_signals AS
SELECT 
    s.id,
    sym.symbol,
    s.timeframe,
    s.signal_type,
    s.entry_price,
    s.stop_loss,
    s.take_profit,
    s.confidence,
    s.status,
    s.created_at
FROM signals s
JOIN symbols sym ON s.symbol_id = sym.id
ORDER BY s.created_at DESC;

-- View: Signal performance summary
CREATE OR REPLACE VIEW v_signal_stats AS
SELECT 
    sym.symbol,
    s.timeframe,
    COUNT(*) as total_signals,
    AVG(s.confidence) as avg_confidence,
    COUNT(CASE WHEN s.status = 'HIT' THEN 1 END) as hits,
    COUNT(CASE WHEN s.status = 'STOPPED' THEN 1 END) as stops,
    ROUND(
        COUNT(CASE WHEN s.status = 'HIT' THEN 1 END)::NUMERIC / 
        NULLIF(COUNT(CASE WHEN s.status IN ('HIT', 'STOPPED') THEN 1 END), 0) * 100,
        2
    ) as win_rate
FROM signals s
JOIN symbols sym ON s.symbol_id = sym.id
GROUP BY sym.symbol, s.timeframe;

-- ============================================================================
-- REALTIME PUBLICATION
-- ============================================================================
-- Enable Realtime for signals table (for live signal broadcasting)
ALTER PUBLICATION supabase_realtime ADD TABLE signals;

-- ============================================================================
-- COMMENTS
-- ============================================================================
COMMENT ON TABLE symbols IS 'Trading symbols configuration';
COMMENT ON TABLE candles IS 'Historical and real-time candlestick data';
COMMENT ON TABLE signals IS 'Generated trading signals from Wyckoff + Elliott analysis';
COMMENT ON TABLE backtests IS 'Backtest configurations and results';
COMMENT ON TABLE user_subscriptions IS 'Discord user notification preferences';
COMMENT ON TABLE signal_performance IS 'Historical signal performance tracking';

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
