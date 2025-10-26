"""
RSI (Relative Strength Index) Analyzer

Detects oversold/overbought conditions for trading signals.
- RSI < 30: Oversold → LONG signal (price likely to bounce up)
- RSI > 70: Overbought → SHORT signal (price likely to pull back)

Works well on all timeframes, especially 15m for swing trading.
"""

import numpy as np
from typing import List, Dict, Any, Optional
from src.bot.logger import get_logger

logger = get_logger(__name__)


class RSIAnalyzer:
    """
    Analyze price data using RSI (Relative Strength Index).
    
    RSI measures momentum on a scale of 0-100:
    - RSI < 30: Oversold (potential buy)
    - RSI > 70: Overbought (potential sell)
    - RSI 30-70: Neutral
    
    Confidence increases the further RSI is from neutral zone.
    """
    
    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70):
        """
        Initialize RSI analyzer.
        
        Args:
            period: RSI calculation period (default 14)
            oversold: Oversold threshold (default 30)
            overbought: Overbought threshold (default 70)
        """
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.min_candles = period + 1
    
    def analyze(
        self,
        candles: List[Dict[str, Any]],
        symbol: str,
        timeframe: str
    ) -> Dict[str, Any]:
        """
        Analyze candles using RSI.
        
        Args:
            candles: List of candle dictionaries
            symbol: Trading symbol
            timeframe: Timeframe
        
        Returns:
            Dictionary with RSI analysis results
        """
        if len(candles) < self.min_candles:
            return self._empty_result()
        
        try:
            # Calculate RSI
            closes = np.array([float(c["close"]) for c in candles])
            rsi = self._calculate_rsi(closes, self.period)
            current_rsi = rsi[-1]
            
            logger.debug(f"RSI for {symbol}: {current_rsi:.1f}")
            
            # Determine signal and confidence
            signal = None
            confidence = 0.0
            rationale = []
            
            if current_rsi < self.oversold:
                # Oversold → LONG signal
                signal = "LONG"
                # Confidence increases the lower RSI goes (RSI 20 = 67%, RSI 10 = 100%)
                confidence = min(1.0, (self.oversold - current_rsi) / self.oversold + 0.5)
                rationale.extend([
                    f"RSI oversold: {current_rsi:.1f} < {self.oversold}",
                    f"Strong buying opportunity (price oversold)",
                    f"Expected bounce: RSI likely to revert toward 50",
                ])
                
            elif current_rsi > self.overbought:
                # Overbought → SHORT signal
                signal = "SHORT"
                # Confidence increases the higher RSI goes (RSI 80 = 67%, RSI 90 = 100%)
                confidence = min(1.0, (current_rsi - self.overbought) / (100 - self.overbought) + 0.5)
                rationale.extend([
                    f"RSI overbought: {current_rsi:.1f} > {self.overbought}",
                    f"Strong selling opportunity (price overbought)",
                    f"Expected pullback: RSI likely to revert toward 50",
                ])
            
            # Calculate RSI trend (is it diverging or confirming?)
            rsi_trend = "rising" if rsi[-1] > rsi[-2] else "falling"
            
            return {
                "signal": signal,
                "confidence": confidence,
                "rsi": current_rsi,
                "rsi_trend": rsi_trend,
                "oversold_level": self.oversold,
                "overbought_level": self.overbought,
                "rationale": rationale,
                "details": {
                    "analyzed_candles": len(candles),
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "rsi_period": self.period,
                }
            }
        
        except Exception as e:
            logger.error(f"Error in RSI analysis: {e}", exc_info=True)
            return self._empty_result()
    
    def _calculate_rsi(self, prices: np.ndarray, period: int) -> np.ndarray:
        """
        Calculate RSI using the standard formula.
        
        Args:
            prices: Array of closing prices
            period: RSI period
        
        Returns:
            Array of RSI values
        """
        # Calculate price changes
        deltas = np.diff(prices)
        
        # Separate gains and losses
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # Calculate average gains and losses using EMA
        avg_gains = np.zeros(len(gains))
        avg_losses = np.zeros(len(losses))
        
        # First average is SMA
        avg_gains[period - 1] = np.mean(gains[:period])
        avg_losses[period - 1] = np.mean(losses[:period])
        
        # Subsequent averages use EMA (Wilder's smoothing)
        for i in range(period, len(gains)):
            avg_gains[i] = (avg_gains[i - 1] * (period - 1) + gains[i]) / period
            avg_losses[i] = (avg_losses[i - 1] * (period - 1) + losses[i]) / period
        
        # Calculate RS and RSI
        rs = np.zeros(len(avg_gains))
        rsi = np.zeros(len(avg_gains))
        
        for i in range(period - 1, len(avg_gains)):
            if avg_losses[i] == 0:
                rsi[i] = 100
            else:
                rs[i] = avg_gains[i] / avg_losses[i]
                rsi[i] = 100 - (100 / (1 + rs[i]))
        
        # Return RSI starting from where we have valid values
        return rsi[period - 1:]
    
    def _empty_result(self) -> Dict[str, Any]:
        """Return empty analysis result."""
        return {
            "signal": None,
            "confidence": 0.0,
            "rsi": 50.0,  # Neutral
            "rsi_trend": "unknown",
            "oversold_level": self.oversold,
            "overbought_level": self.overbought,
            "rationale": [],
            "details": {},
        }
