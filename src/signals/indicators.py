"""
Technical indicators module.

Computes various technical indicators used for signal confirmation.
"""

from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd

try:
    import pandas_ta as ta
except ImportError:
    ta = None

from ..bot.logger import get_logger

logger = get_logger(__name__)


def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
    """
    Calculate RSI (Relative Strength Index).
    
    Args:
        prices: List of closing prices
        period: RSI period
    
    Returns:
        RSI value or None
    """
    if len(prices) < period + 1:
        return None
    
    try:
        df = pd.DataFrame({"close": prices})
        
        if ta:
            rsi = ta.rsi(df["close"], length=period)
            return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None
        else:
            # Manual RSI calculation
            deltas = np.diff(prices)
            gain = np.where(deltas > 0, deltas, 0)
            loss = np.where(deltas < 0, -deltas, 0)
            
            avg_gain = np.mean(gain[-period:])
            avg_loss = np.mean(loss[-period:])
            
            if avg_loss == 0:
                return 100.0
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            return float(rsi)
    
    except Exception as e:
        logger.error(f"Error calculating RSI: {e}")
        return None


def calculate_ema(prices: List[float], period: int) -> Optional[float]:
    """
    Calculate EMA (Exponential Moving Average).
    
    Args:
        prices: List of closing prices
        period: EMA period
    
    Returns:
        EMA value or None
    """
    if len(prices) < period:
        return None
    
    try:
        df = pd.DataFrame({"close": prices})
        
        if ta:
            ema = ta.ema(df["close"], length=period)
            return float(ema.iloc[-1]) if not pd.isna(ema.iloc[-1]) else None
        else:
            # Manual EMA calculation
            ema_values = pd.Series(prices).ewm(span=period, adjust=False).mean()
            return float(ema_values.iloc[-1])
    
    except Exception as e:
        logger.error(f"Error calculating EMA: {e}")
        return None


def calculate_vwap(candles: List[Dict[str, Any]]) -> Optional[float]:
    """
    Calculate VWAP (Volume Weighted Average Price).
    
    Args:
        candles: List of candle dictionaries with OHLCV data
    
    Returns:
        VWAP value or None
    """
    if not candles:
        return None
    
    try:
        df = pd.DataFrame(candles)
        
        # Typical price = (H + L + C) / 3
        df["typical_price"] = (df["high"] + df["low"] + df["close"]) / 3
        df["tp_volume"] = df["typical_price"] * df["volume"]
        
        vwap = df["tp_volume"].sum() / df["volume"].sum()
        return float(vwap)
    
    except Exception as e:
        logger.error(f"Error calculating VWAP: {e}")
        return None


def calculate_atr(candles: List[Dict[str, Any]], period: int = 14) -> Optional[float]:
    """
    Calculate ATR (Average True Range).
    
    Args:
        candles: List of candle dictionaries
        period: ATR period
    
    Returns:
        ATR value or None
    """
    if len(candles) < period + 1:
        return None
    
    try:
        df = pd.DataFrame(candles)
        
        if ta:
            atr = ta.atr(df["high"], df["low"], df["close"], length=period)
            return float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else None
        else:
            # Manual ATR calculation
            df["h_l"] = df["high"] - df["low"]
            df["h_pc"] = abs(df["high"] - df["close"].shift(1))
            df["l_pc"] = abs(df["low"] - df["close"].shift(1))
            df["tr"] = df[["h_l", "h_pc", "l_pc"]].max(axis=1)
            
            atr = df["tr"].rolling(window=period).mean()
            return float(atr.iloc[-1])
    
    except Exception as e:
        logger.error(f"Error calculating ATR: {e}")
        return None


def calculate_volume_profile(candles: List[Dict[str, Any]], bins: int = 20) -> Dict[str, Any]:
    """
    Calculate volume profile (price levels with most volume).
    
    Args:
        candles: List of candle dictionaries
        bins: Number of price bins
    
    Returns:
        Dictionary with volume profile data
    """
    if not candles:
        return {}
    
    try:
        df = pd.DataFrame(candles)
        
        # Create price bins
        price_min = df["low"].min()
        price_max = df["high"].max()
        price_range = price_max - price_min
        bin_size = price_range / bins
        
        # Assign each candle to bins and sum volume
        volume_by_price = {}
        for _, candle in df.iterrows():
            candle_range = candle["high"] - candle["low"]
            if candle_range == 0:
                bin_idx = int((candle["close"] - price_min) / bin_size)
                bin_price = price_min + (bin_idx * bin_size)
                volume_by_price[bin_price] = volume_by_price.get(bin_price, 0) + candle["volume"]
            else:
                # Distribute volume across price range
                for i in range(bins):
                    bin_price = price_min + (i * bin_size)
                    bin_high = bin_price + bin_size
                    
                    if bin_price <= candle["high"] and bin_high >= candle["low"]:
                        overlap = min(candle["high"], bin_high) - max(candle["low"], bin_price)
                        volume_contribution = (overlap / candle_range) * candle["volume"]
                        volume_by_price[bin_price] = volume_by_price.get(bin_price, 0) + volume_contribution
        
        # Find POC (Point of Control) - price level with most volume
        poc_price = max(volume_by_price, key=volume_by_price.get)
        poc_volume = volume_by_price[poc_price]
        
        return {
            "poc_price": poc_price,
            "poc_volume": poc_volume,
            "volume_by_price": volume_by_price,
        }
    
    except Exception as e:
        logger.error(f"Error calculating volume profile: {e}")
        return {}


def check_volume_surge(candles: List[Dict[str, Any]], threshold: float = 1.5) -> bool:
    """
    Check if recent volume is significantly above average.
    
    Args:
        candles: List of candle dictionaries
        threshold: Volume multiplier threshold
    
    Returns:
        True if volume surge detected
    """
    if len(candles) < 20:
        return False
    
    try:
        df = pd.DataFrame(candles)
        
        recent_volume = df["volume"].iloc[-1]
        avg_volume = df["volume"].iloc[-20:-1].mean()
        
        return recent_volume > (avg_volume * threshold)
    
    except Exception as e:
        logger.error(f"Error checking volume surge: {e}")
        return False


def calculate_bollinger_bands(
    prices: List[float],
    period: int = 20,
    std_dev: float = 2.0
) -> Optional[Dict[str, float]]:
    """
    Calculate Bollinger Bands.
    
    Args:
        prices: List of closing prices
        period: Moving average period
        std_dev: Number of standard deviations
    
    Returns:
        Dictionary with upper, middle, lower bands
    """
    if len(prices) < period:
        return None
    
    try:
        df = pd.DataFrame({"close": prices})
        
        if ta:
            bbands = ta.bbands(df["close"], length=period, std=std_dev)
            return {
                "upper": float(bbands[f"BBU_{period}_{std_dev}"].iloc[-1]),
                "middle": float(bbands[f"BBM_{period}_{std_dev}"].iloc[-1]),
                "lower": float(bbands[f"BBL_{period}_{std_dev}"].iloc[-1]),
            }
        else:
            # Manual calculation
            sma = df["close"].rolling(window=period).mean()
            std = df["close"].rolling(window=period).std()
            
            upper = sma + (std * std_dev)
            lower = sma - (std * std_dev)
            
            return {
                "upper": float(upper.iloc[-1]),
                "middle": float(sma.iloc[-1]),
                "lower": float(lower.iloc[-1]),
            }
    
    except Exception as e:
        logger.error(f"Error calculating Bollinger Bands: {e}")
        return None


def calculate_macd(
    prices: List[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> Optional[Dict[str, float]]:
    """
    Calculate MACD (Moving Average Convergence Divergence).
    
    Args:
        prices: List of closing prices
        fast: Fast EMA period
        slow: Slow EMA period
        signal: Signal line period
    
    Returns:
        Dictionary with MACD line, signal line, histogram
    """
    if len(prices) < slow + signal:
        return None
    
    try:
        df = pd.DataFrame({"close": prices})
        
        if ta:
            macd = ta.macd(df["close"], fast=fast, slow=slow, signal=signal)
            return {
                "macd": float(macd[f"MACD_{fast}_{slow}_{signal}"].iloc[-1]),
                "signal": float(macd[f"MACDs_{fast}_{slow}_{signal}"].iloc[-1]),
                "histogram": float(macd[f"MACDh_{fast}_{slow}_{signal}"].iloc[-1]),
            }
        else:
            # Manual MACD calculation
            ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
            ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal, adjust=False).mean()
            histogram = macd_line - signal_line
            
            return {
                "macd": float(macd_line.iloc[-1]),
                "signal": float(signal_line.iloc[-1]),
                "histogram": float(histogram.iloc[-1]),
            }
    
    except Exception as e:
        logger.error(f"Error calculating MACD: {e}")
        return None


def get_indicator_confirmations(
    candles: List[Dict[str, Any]],
    signal_type: str,
    current_price: float
) -> Dict[str, Any]:
    """
    Get indicator confirmations for a signal.
    
    Args:
        candles: List of recent candles
        signal_type: LONG or SHORT
        current_price: Current price
    
    Returns:
        Dictionary with indicator values and confirmations
    """
    if len(candles) < 30:
        return {"confirmations": [], "indicators": {}}
    
    confirmations = []
    indicators = {}
    
    try:
        prices = [float(c["close"]) for c in candles]
        
        # RSI
        rsi = calculate_rsi(prices)
        if rsi:
            indicators["rsi"] = rsi
            if signal_type == "LONG" and rsi < 40:
                confirmations.append("RSI oversold (bullish)")
            elif signal_type == "SHORT" and rsi > 60:
                confirmations.append("RSI overbought (bearish)")
        
        # EMA crossover
        ema_9 = calculate_ema(prices, 9)
        ema_21 = calculate_ema(prices, 21)
        if ema_9 and ema_21:
            indicators["ema_9"] = ema_9
            indicators["ema_21"] = ema_21
            if signal_type == "LONG" and ema_9 > ema_21:
                confirmations.append("EMA bullish crossover")
            elif signal_type == "SHORT" and ema_9 < ema_21:
                confirmations.append("EMA bearish crossover")
        
        # VWAP
        vwap = calculate_vwap(candles[-20:])
        if vwap:
            indicators["vwap"] = vwap
            if signal_type == "LONG" and current_price < vwap:
                confirmations.append("Price below VWAP (potential support)")
            elif signal_type == "SHORT" and current_price > vwap:
                confirmations.append("Price above VWAP (potential resistance)")
        
        # Volume
        if check_volume_surge(candles):
            confirmations.append("Volume surge detected")
        
        # MACD
        macd = calculate_macd(prices)
        if macd:
            indicators["macd"] = macd
            if signal_type == "LONG" and macd["histogram"] > 0:
                confirmations.append("MACD bullish")
            elif signal_type == "SHORT" and macd["histogram"] < 0:
                confirmations.append("MACD bearish")
    
    except Exception as e:
        logger.error(f"Error getting indicator confirmations: {e}")
    
    return {
        "confirmations": confirmations,
        "indicators": indicators,
    }
