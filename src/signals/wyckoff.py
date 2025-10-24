"""
Wyckoff Method analysis module.

Implements Wyckoff phase detection and spring/upthrust pattern recognition.
"""

from typing import Dict, List, Optional, Any
from enum import Enum
import numpy as np

from ..bot.logger import get_logger

logger = get_logger(__name__)


class WyckoffPhase(Enum):
    """Wyckoff market phases."""
    ACCUMULATION = "accumulation"
    MARKUP = "markup"
    DISTRIBUTION = "distribution"
    MARKDOWN = "markdown"
    UNKNOWN = "unknown"


class WyckoffAnalyzer:
    """
    Wyckoff Method analyzer.
    
    Detects:
    - Accumulation/Distribution phases
    - Springs (failed breakdowns in accumulation)
    - Upthrusts (failed breakouts in distribution)
    - Signs of Strength (SOS) and Weakness (SOW)
    """
    
    def __init__(self):
        """Initialize Wyckoff analyzer."""
        self.min_candles = 50
    
    def analyze(
        self,
        candles: List[Dict[str, Any]],
        symbol: str,
        timeframe: str
    ) -> Dict[str, Any]:
        """
        Analyze candles using Wyckoff Method.
        
        Args:
            candles: List of candle dictionaries
            symbol: Trading symbol
            timeframe: Timeframe
        
        Returns:
            Dictionary with Wyckoff analysis results
        """
        if len(candles) < self.min_candles:
            return self._empty_result()
        
        try:
            # Detect current phase
            phase = self._detect_phase(candles)
            
            # Look for springs (bullish) or upthrusts (bearish)
            spring = self._detect_spring(candles)
            upthrust = self._detect_upthrust(candles)
            
            # Generate signal if criteria met
            signal = None
            confidence = 0.0
            rationale = []
            
            if spring and phase == WyckoffPhase.ACCUMULATION:
                signal = "LONG"
                confidence = spring["confidence"]
                rationale.extend([
                    f"Wyckoff spring detected in {phase.value} phase",
                    f"Price tested support at {spring['support_level']:.2f} and recovered",
                    f"Volume characteristics: {spring['volume_desc']}",
                ])
            
            elif upthrust and phase == WyckoffPhase.DISTRIBUTION:
                signal = "SHORT"
                confidence = upthrust["confidence"]
                rationale.extend([
                    f"Wyckoff upthrust detected in {phase.value} phase",
                    f"Price tested resistance at {upthrust['resistance_level']:.2f} and failed",
                    f"Volume characteristics: {upthrust['volume_desc']}",
                ])
            
            return {
                "signal": signal,
                "confidence": confidence,
                "phase": phase.value,
                "spring": spring,
                "upthrust": upthrust,
                "rationale": rationale,
                "details": {
                    "analyzed_candles": len(candles),
                    "symbol": symbol,
                    "timeframe": timeframe,
                }
            }
        
        except Exception as e:
            logger.error(f"Error in Wyckoff analysis: {e}", exc_info=True)
            return self._empty_result()
    
    def _empty_result(self) -> Dict[str, Any]:
        """Return empty analysis result."""
        return {
            "signal": None,
            "confidence": 0.0,
            "phase": WyckoffPhase.UNKNOWN.value,
            "spring": None,
            "upthrust": None,
            "rationale": [],
            "details": {},
        }
    
    def _detect_phase(self, candles: List[Dict[str, Any]]) -> WyckoffPhase:
        """
        Detect current Wyckoff phase.
        
        Args:
            candles: List of candle dictionaries
        
        Returns:
            Detected phase
        """
        try:
            # Use last 30 candles for phase detection
            recent = candles[-30:]
            
            highs = [c["high"] for c in recent]
            lows = [c["low"] for c in recent]
            closes = [c["close"] for c in recent]
            volumes = [c["volume"] for c in recent]
            
            # Calculate price range and trend
            price_range = max(highs) - min(lows)
            range_percent = (price_range / min(lows)) * 100
            
            # Trend analysis
            first_half_avg = np.mean(closes[:15])
            second_half_avg = np.mean(closes[15:])
            trend = second_half_avg - first_half_avg
            
            # Volume analysis
            avg_volume = np.mean(volumes)
            recent_volume = np.mean(volumes[-5:])
            volume_ratio = recent_volume / avg_volume
            
            # Phase detection logic
            if range_percent < 5 and volume_ratio > 1.2:
                # Tight range with increasing volume suggests accumulation or distribution
                if trend > 0:
                    return WyckoffPhase.ACCUMULATION
                else:
                    return WyckoffPhase.DISTRIBUTION
            
            elif trend > 0 and range_percent > 5:
                return WyckoffPhase.MARKUP
            
            elif trend < 0 and range_percent > 5:
                return WyckoffPhase.MARKDOWN
            
            return WyckoffPhase.UNKNOWN
        
        except Exception as e:
            logger.error(f"Error detecting Wyckoff phase: {e}")
            return WyckoffPhase.UNKNOWN
    
    def _detect_spring(self, candles: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Detect Wyckoff spring pattern (bullish reversal).
        
        A spring occurs when price breaks below a support level but quickly
        recovers, indicating strong buying pressure.
        
        Args:
            candles: List of candle dictionaries
        
        Returns:
            Spring details or None
        """
        try:
            if len(candles) < 30:
                return None
            
            # Find recent support level (last 20 candles)
            support_candles = candles[-20:-5]
            support_level = min(c["low"] for c in support_candles)
            
            # Check last 5 candles for spring
            recent = candles[-5:]
            
            for i, candle in enumerate(recent):
                # Check if price broke below support
                if candle["low"] < support_level:
                    # Check if it closed back above support (strong recovery)
                    if candle["close"] > support_level:
                        # Calculate confidence based on:
                        # 1. How quickly it recovered (same candle = high confidence)
                        # 2. Volume on recovery
                        # 3. Close position in candle range
                        
                        recovery_strength = (candle["close"] - candle["low"]) / (candle["high"] - candle["low"])
                        
                        # Volume analysis
                        avg_volume = np.mean([c["volume"] for c in candles[-20:-5]])
                        spring_volume = candle["volume"]
                        volume_ratio = spring_volume / avg_volume
                        
                        # Calculate confidence (0-1)
                        confidence = min(1.0, (
                            recovery_strength * 0.4 +
                            min(volume_ratio / 2, 0.4) +
                            (0.2 if i == len(recent) - 1 else 0.1)  # Recent spring is better
                        ))
                        
                        # Require minimum confidence
                        if confidence < 0.5:
                            continue
                        
                        return {
                            "support_level": support_level,
                            "spring_low": candle["low"],
                            "spring_close": candle["close"],
                            "recovery_strength": recovery_strength,
                            "volume_ratio": volume_ratio,
                            "confidence": confidence,
                            "volume_desc": "strong" if volume_ratio > 1.5 else "moderate",
                            "candles_ago": len(recent) - i - 1,
                        }
            
            return None
        
        except Exception as e:
            logger.error(f"Error detecting spring: {e}")
            return None
    
    def _detect_upthrust(self, candles: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Detect Wyckoff upthrust pattern (bearish reversal).
        
        An upthrust occurs when price breaks above resistance but quickly
        fails, indicating strong selling pressure.
        
        Args:
            candles: List of candle dictionaries
        
        Returns:
            Upthrust details or None
        """
        try:
            if len(candles) < 30:
                return None
            
            # Find recent resistance level (last 20 candles)
            resistance_candles = candles[-20:-5]
            resistance_level = max(c["high"] for c in resistance_candles)
            
            # Check last 5 candles for upthrust
            recent = candles[-5:]
            
            for i, candle in enumerate(recent):
                # Check if price broke above resistance
                if candle["high"] > resistance_level:
                    # Check if it closed back below resistance (rejection)
                    if candle["close"] < resistance_level:
                        # Calculate confidence based on rejection strength
                        rejection_strength = (candle["high"] - candle["close"]) / (candle["high"] - candle["low"])
                        
                        # Volume analysis
                        avg_volume = np.mean([c["volume"] for c in candles[-20:-5]])
                        upthrust_volume = candle["volume"]
                        volume_ratio = upthrust_volume / avg_volume
                        
                        # Calculate confidence
                        confidence = min(1.0, (
                            rejection_strength * 0.4 +
                            min(volume_ratio / 2, 0.4) +
                            (0.2 if i == len(recent) - 1 else 0.1)
                        ))
                        
                        if confidence < 0.5:
                            continue
                        
                        return {
                            "resistance_level": resistance_level,
                            "upthrust_high": candle["high"],
                            "upthrust_close": candle["close"],
                            "rejection_strength": rejection_strength,
                            "volume_ratio": volume_ratio,
                            "confidence": confidence,
                            "volume_desc": "strong" if volume_ratio > 1.5 else "moderate",
                            "candles_ago": len(recent) - i - 1,
                        }
            
            return None
        
        except Exception as e:
            logger.error(f"Error detecting upthrust: {e}")
            return None
