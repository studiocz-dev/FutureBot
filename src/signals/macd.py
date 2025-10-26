"""
MACD (Moving Average Convergence Divergence) Analyzer

Detects trend changes and momentum shifts using MACD crossovers.
- MACD crosses above Signal → Bullish (LONG signal)
- MACD crosses below Signal → Bearish (SHORT signal)

Works well on all timeframes, especially 15m for swing trading.
"""

import numpy as np
from typing import List, Dict, Any, Optional
from src.bot.logger import get_logger

logger = get_logger(__name__)


class MACDAnalyzer:
    """
    Analyze price data using MACD (Moving Average Convergence Divergence).
    
    MACD consists of:
    - MACD Line: 12-period EMA - 26-period EMA
    - Signal Line: 9-period EMA of MACD Line
    - Histogram: MACD Line - Signal Line
    
    Signals:
    - MACD crosses above Signal → Bullish crossover (LONG)
    - MACD crosses below Signal → Bearish crossover (SHORT)
    
    Confidence increases with:
    - Histogram magnitude (stronger crossover)
    - MACD distance from zero line
    """
    
    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ):
        """
        Initialize MACD analyzer.
        
        Args:
            fast_period: Fast EMA period (default 12)
            slow_period: Slow EMA period (default 26)
            signal_period: Signal line EMA period (default 9)
        """
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.min_candles = slow_period + signal_period + 10  # ~45 candles minimum
    
    def analyze(
        self,
        candles: List[Dict[str, Any]],
        symbol: str,
        timeframe: str
    ) -> Dict[str, Any]:
        """
        Analyze candles using MACD.
        
        Args:
            candles: List of candle dictionaries
            symbol: Trading symbol
            timeframe: Timeframe
        
        Returns:
            Dictionary with MACD analysis results
        """
        if len(candles) < self.min_candles:
            return self._empty_result()
        
        try:
            # Calculate MACD
            closes = np.array([float(c["close"]) for c in candles])
            macd_line, signal_line, histogram = self._calculate_macd(
                closes, 
                self.fast_period, 
                self.slow_period, 
                self.signal_period
            )
            
            current_macd = macd_line[-1]
            current_signal = signal_line[-1]
            current_histogram = histogram[-1]
            prev_histogram = histogram[-2] if len(histogram) > 1 else 0
            
            logger.debug(f"MACD for {symbol}: Line={current_macd:.4f}, Signal={current_signal:.4f}, Histogram={current_histogram:.4f}")
            
            # Detect crossover
            signal = None
            confidence = 0.0
            rationale = []
            
            # Bullish crossover: MACD crosses above Signal
            if prev_histogram < 0 and current_histogram > 0:
                signal = "LONG"
                # Confidence based on:
                # 1. Histogram magnitude (stronger crossover = higher confidence)
                # 2. MACD position relative to zero (positive MACD = stronger)
                histogram_strength = min(abs(current_histogram) * 100, 0.4)  # Up to 40%
                zero_line_bonus = 0.2 if current_macd > 0 else 0.1
                confidence = min(1.0, 0.5 + histogram_strength + zero_line_bonus)
                
                rationale.extend([
                    f"MACD bullish crossover detected",
                    f"MACD ({current_macd:.4f}) crossed above Signal ({current_signal:.4f})",
                    f"Histogram positive: {current_histogram:.4f}",
                    f"Momentum shifting bullish (upward trend)",
                ])
            
            # Bearish crossover: MACD crosses below Signal
            elif prev_histogram > 0 and current_histogram < 0:
                signal = "SHORT"
                histogram_strength = min(abs(current_histogram) * 100, 0.4)
                zero_line_bonus = 0.2 if current_macd < 0 else 0.1
                confidence = min(1.0, 0.5 + histogram_strength + zero_line_bonus)
                
                rationale.extend([
                    f"MACD bearish crossover detected",
                    f"MACD ({current_macd:.4f}) crossed below Signal ({current_signal:.4f})",
                    f"Histogram negative: {current_histogram:.4f}",
                    f"Momentum shifting bearish (downward trend)",
                ])
            
            # Determine trend direction
            macd_trend = "bullish" if current_histogram > 0 else "bearish"
            macd_strength = "strong" if abs(current_histogram) > abs(prev_histogram) else "weakening"
            
            return {
                "signal": signal,
                "confidence": confidence,
                "macd_line": current_macd,
                "signal_line": current_signal,
                "histogram": current_histogram,
                "macd_trend": macd_trend,
                "macd_strength": macd_strength,
                "rationale": rationale,
                "details": {
                    "analyzed_candles": len(candles),
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "fast_period": self.fast_period,
                    "slow_period": self.slow_period,
                    "signal_period": self.signal_period,
                }
            }
        
        except Exception as e:
            logger.error(f"Error in MACD analysis: {e}", exc_info=True)
            return self._empty_result()
    
    def _calculate_ema(self, prices: np.ndarray, period: int) -> np.ndarray:
        """
        Calculate Exponential Moving Average.
        
        Args:
            prices: Array of prices
            period: EMA period
        
        Returns:
            Array of EMA values
        """
        ema = np.zeros(len(prices))
        multiplier = 2 / (period + 1)
        
        # First EMA value is SMA
        ema[period - 1] = np.mean(prices[:period])
        
        # Calculate EMA for remaining values
        for i in range(period, len(prices)):
            ema[i] = (prices[i] - ema[i - 1]) * multiplier + ema[i - 1]
        
        return ema
    
    def _calculate_macd(
        self,
        prices: np.ndarray,
        fast_period: int,
        slow_period: int,
        signal_period: int
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculate MACD, Signal line, and Histogram.
        
        Args:
            prices: Array of closing prices
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            signal_period: Signal line EMA period
        
        Returns:
            (macd_line, signal_line, histogram)
        """
        # Calculate fast and slow EMAs
        fast_ema = self._calculate_ema(prices, fast_period)
        slow_ema = self._calculate_ema(prices, slow_period)
        
        # MACD Line = Fast EMA - Slow EMA
        macd_line = fast_ema - slow_ema
        
        # Signal Line = EMA of MACD Line
        # Start calculation after slow_period
        macd_for_signal = macd_line[slow_period - 1:]
        signal_line_partial = self._calculate_ema(macd_for_signal, signal_period)
        
        # Pad signal line to match macd_line length
        signal_line = np.zeros(len(macd_line))
        signal_line[slow_period - 1:] = signal_line_partial
        
        # Histogram = MACD Line - Signal Line
        histogram = macd_line - signal_line
        
        # Return values from where we have valid data
        start_idx = slow_period + signal_period - 2
        return (
            macd_line[start_idx:],
            signal_line[start_idx:],
            histogram[start_idx:]
        )
    
    def _empty_result(self) -> Dict[str, Any]:
        """Return empty analysis result."""
        return {
            "signal": None,
            "confidence": 0.0,
            "macd_line": 0.0,
            "signal_line": 0.0,
            "histogram": 0.0,
            "macd_trend": "unknown",
            "macd_strength": "unknown",
            "rationale": [],
            "details": {},
        }
