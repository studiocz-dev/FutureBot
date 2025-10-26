"""
Elliott Wave analysis module.

Implements simplified Elliott Wave pattern recognition and counting.
"""

from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import numpy as np

from ..bot.logger import get_logger

logger = get_logger(__name__)


class WaveType(Enum):
    """Elliott Wave types."""
    IMPULSE = "impulse"  # 5-wave trending move
    CORRECTIVE = "corrective"  # 3-wave counter-trend move
    UNKNOWN = "unknown"


class ElliottWaveAnalyzer:
    """
    Elliott Wave analyzer.
    
    Implements simplified Elliott Wave counting:
    - Identifies potential 5-wave impulse patterns
    - Detects 3-wave corrections (ABC)
    - Finds potential reversal zones (PRZ)
    - Generates signals based on wave completion
    """
    
    def __init__(self):
        """Initialize Elliott Wave analyzer."""
        self.min_candles = 50
        self.wave_tolerance = 0.15  # 15% tolerance for wave relationships
    
    def analyze(
        self,
        candles: List[Dict[str, Any]],
        symbol: str,
        timeframe: str
    ) -> Dict[str, Any]:
        """
        Analyze candles using Elliott Wave theory.
        
        Args:
            candles: List of candle dictionaries
            symbol: Trading symbol
            timeframe: Timeframe
        
        Returns:
            Dictionary with Elliott Wave analysis results
        """
        if len(candles) < self.min_candles:
            return self._empty_result()
        
        try:
            # Find significant pivot points (swing highs/lows)
            pivots = self._find_pivots(candles)
            logger.debug(f"Elliott Wave for {symbol}: found {len(pivots)} pivots (need ≥5)")
            
            if len(pivots) < 5:
                return self._empty_result()
            
            # Attempt to count waves
            wave_count = self._count_waves(pivots, candles)
            
            if wave_count:
                logger.debug(f"Elliott Wave count for {symbol}: type={wave_count.get('type')}, valid={wave_count.get('valid')}, confidence={wave_count.get('confidence', 0):.2f}")
            else:
                logger.debug(f"Elliott Wave for {symbol}: no valid wave count found")
            
            # Generate signal if we're at a potential reversal point
            signal = None
            confidence = 0.0
            rationale = []
            
            if wave_count and wave_count["valid"]:
                if wave_count["type"] == "impulse_up_complete":
                    signal = "SHORT"
                    confidence = wave_count["confidence"]
                    rationale.extend([
                        f"Elliott Wave: Completed 5-wave impulse UP",
                        f"Wave 5 target: {wave_count['wave_5_target']:.2f}",
                        f"Expecting ABC correction (down)",
                        f"Confidence based on: {wave_count['confidence_factors']}",
                    ])
                
                elif wave_count["type"] == "impulse_down_complete":
                    signal = "LONG"
                    confidence = wave_count["confidence"]
                    rationale.extend([
                        f"Elliott Wave: Completed 5-wave impulse DOWN",
                        f"Wave 5 target: {wave_count['wave_5_target']:.2f}",
                        f"Expecting ABC correction (up)",
                        f"Confidence based on: {wave_count['confidence_factors']}",
                    ])
                
                elif wave_count["type"] == "correction_complete":
                    direction = wave_count.get("next_trend", "").upper()
                    if direction in ["LONG", "SHORT"]:
                        signal = direction
                        confidence = wave_count["confidence"]
                        rationale.extend([
                            f"Elliott Wave: ABC correction appears complete",
                            f"Expecting resumption of {direction.lower()} trend",
                            f"Entry zone: {wave_count.get('entry_zone', 'N/A')}",
                        ])
            
            return {
                "signal": signal,
                "confidence": confidence,
                "wave_count": wave_count.get("count", "unknown") if wave_count else "unknown",
                "wave_type": wave_count.get("type", "unknown") if wave_count else "unknown",
                "rationale": rationale,
                "pivots": len(pivots),
                "details": {
                    "analyzed_candles": len(candles),
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "wave_count_detail": wave_count,
                }
            }
        
        except Exception as e:
            logger.error(f"Error in Elliott Wave analysis: {e}", exc_info=True)
            return self._empty_result()
    
    def _empty_result(self) -> Dict[str, Any]:
        """Return empty analysis result."""
        return {
            "signal": None,
            "confidence": 0.0,
            "wave_count": "unknown",
            "wave_type": "unknown",
            "rationale": [],
            "pivots": 0,
            "details": {},
        }
    
    def _find_pivots(
        self,
        candles: List[Dict[str, Any]],
        window: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find significant pivot points (swing highs and lows).
        
        Args:
            candles: List of candle dictionaries
            window: Window size for pivot detection
        
        Returns:
            List of pivot points
        """
        pivots = []
        
        try:
            for i in range(window, len(candles) - window):
                candle = candles[i]
                
                # Check for swing high
                is_high = True
                for j in range(i - window, i + window + 1):
                    if j != i and candles[j]["high"] >= candle["high"]:
                        is_high = False
                        break
                
                if is_high:
                    pivots.append({
                        "type": "high",
                        "price": candle["high"],
                        "index": i,
                        "time": candle.get("open_time", i),
                    })
                    continue
                
                # Check for swing low
                is_low = True
                for j in range(i - window, i + window + 1):
                    if j != i and candles[j]["low"] <= candle["low"]:
                        is_low = False
                        break
                
                if is_low:
                    pivots.append({
                        "type": "low",
                        "price": candle["low"],
                        "index": i,
                        "time": candle.get("open_time", i),
                    })
        
        except Exception as e:
            logger.error(f"Error finding pivots: {e}")
        
        return pivots
    
    def _count_waves(
        self,
        pivots: List[Dict[str, Any]],
        candles: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Attempt to count Elliott Waves from pivot points.
        
        Args:
            pivots: List of pivot points
            candles: Original candle data
        
        Returns:
            Wave count information or None
        """
        try:
            # Take the most recent pivots
            recent_pivots = pivots[-10:]  # Last 10 pivots
            
            # Try to identify 5-wave impulse pattern
            impulse = self._find_impulse_pattern(recent_pivots)
            if impulse:
                return impulse
            
            # Try to identify 3-wave correction pattern
            correction = self._find_correction_pattern(recent_pivots)
            if correction:
                return correction
            
            return None
        
        except Exception as e:
            logger.error(f"Error counting waves: {e}")
            return None
    
    def _find_impulse_pattern(
        self,
        pivots: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Find completed 5-wave impulse pattern.
        
        Impulse rules:
        - Wave 2 cannot retrace more than 100% of wave 1
        - Wave 3 cannot be the shortest of waves 1, 3, 5
        - Wave 4 cannot overlap wave 1
        
        Args:
            pivots: List of pivot points
        
        Returns:
            Impulse pattern details or None
        """
        if len(pivots) < 6:
            return None
        
        try:
            # Check for upward impulse (low-high-low-high-low-high)
            if (pivots[-6]["type"] == "low" and
                pivots[-5]["type"] == "high" and
                pivots[-4]["type"] == "low" and
                pivots[-3]["type"] == "high" and
                pivots[-2]["type"] == "low" and
                pivots[-1]["type"] == "high"):
                
                p0 = pivots[-6]["price"]  # Start
                p1 = pivots[-5]["price"]  # Wave 1 end
                p2 = pivots[-4]["price"]  # Wave 2 end
                p3 = pivots[-3]["price"]  # Wave 3 end
                p4 = pivots[-2]["price"]  # Wave 4 end
                p5 = pivots[-1]["price"]  # Wave 5 end
                
                wave1 = p1 - p0
                wave2 = p1 - p2
                wave3 = p3 - p2
                wave4 = p3 - p4
                wave5 = p5 - p4
                
                # Check Elliott Wave rules
                rule1 = wave2 / wave1 < 1.0  # Wave 2 doesn't exceed wave 1
                rule2 = wave3 >= wave1 and wave3 >= wave5  # Wave 3 not shortest
                rule3 = p4 > p1  # Wave 4 doesn't overlap wave 1
                
                if rule1 and rule2 and rule3:
                    confidence = self._calculate_wave_confidence([wave1, wave2, wave3, wave4, wave5], "impulse")
                    
                    return {
                        "valid": True,
                        "type": "impulse_up_complete",
                        "count": "5 waves up",
                        "wave_5_target": p5,
                        "confidence": confidence,
                        "confidence_factors": f"Rules: {[rule1, rule2, rule3]}",
                        "waves": {
                            "wave_1": wave1,
                            "wave_2": wave2,
                            "wave_3": wave3,
                            "wave_4": wave4,
                            "wave_5": wave5,
                        }
                    }
            
            # Check for downward impulse (high-low-high-low-high-low)
            if (pivots[-6]["type"] == "high" and
                pivots[-5]["type"] == "low" and
                pivots[-4]["type"] == "high" and
                pivots[-3]["type"] == "low" and
                pivots[-2]["type"] == "high" and
                pivots[-1]["type"] == "low"):
                
                p0 = pivots[-6]["price"]
                p1 = pivots[-5]["price"]
                p2 = pivots[-4]["price"]
                p3 = pivots[-3]["price"]
                p4 = pivots[-2]["price"]
                p5 = pivots[-1]["price"]
                
                wave1 = p0 - p1
                wave2 = p2 - p1
                wave3 = p2 - p3
                wave4 = p4 - p3
                wave5 = p4 - p5
                
                rule1 = wave2 / wave1 < 1.0
                rule2 = wave3 >= wave1 and wave3 >= wave5
                rule3 = p4 < p1
                
                if rule1 and rule2 and rule3:
                    confidence = self._calculate_wave_confidence([wave1, wave2, wave3, wave4, wave5], "impulse")
                    
                    return {
                        "valid": True,
                        "type": "impulse_down_complete",
                        "count": "5 waves down",
                        "wave_5_target": p5,
                        "confidence": confidence,
                        "confidence_factors": f"Rules: {[rule1, rule2, rule3]}",
                        "waves": {
                            "wave_1": wave1,
                            "wave_2": wave2,
                            "wave_3": wave3,
                            "wave_4": wave4,
                            "wave_5": wave5,
                        }
                    }
            
            return None
        
        except Exception as e:
            logger.error(f"Error finding impulse pattern: {e}")
            return None
    
    def _find_correction_pattern(
        self,
        pivots: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Find completed ABC correction pattern.
        
        Args:
            pivots: List of pivot points
        
        Returns:
            Correction pattern details or None
        """
        if len(pivots) < 4:
            return None
        
        try:
            # ABC correction after uptrend: high-low-high-low
            if (pivots[-4]["type"] == "high" and
                pivots[-3]["type"] == "low" and
                pivots[-2]["type"] == "high" and
                pivots[-1]["type"] == "low"):
                
                pA_start = pivots[-4]["price"]
                pA_end = pivots[-3]["price"]
                pB = pivots[-2]["price"]
                pC = pivots[-1]["price"]
                
                wave_a = pA_start - pA_end
                wave_b = pB - pA_end
                wave_c = pB - pC
                
                # Typical ABC relationships
                # Wave C often equals or extends beyond Wave A
                c_to_a_ratio = wave_c / wave_a if wave_a > 0 else 0
                
                if 0.8 <= c_to_a_ratio <= 1.618:  # Common Fibonacci ratios
                    confidence = min(0.8, 0.5 + (0.3 if 0.95 <= c_to_a_ratio <= 1.05 else 0))
                    
                    return {
                        "valid": True,
                        "type": "correction_complete",
                        "count": "ABC correction",
                        "next_trend": "LONG",
                        "entry_zone": pC,
                        "confidence": confidence,
                        "c_to_a_ratio": c_to_a_ratio,
                    }
            
            # ABC correction after downtrend: low-high-low-high
            if (pivots[-4]["type"] == "low" and
                pivots[-3]["type"] == "high" and
                pivots[-2]["type"] == "low" and
                pivots[-1]["type"] == "high"):
                
                pA_start = pivots[-4]["price"]
                pA_end = pivots[-3]["price"]
                pB = pivots[-2]["price"]
                pC = pivots[-1]["price"]
                
                wave_a = pA_end - pA_start
                wave_b = pA_end - pB
                wave_c = pC - pB
                
                c_to_a_ratio = wave_c / wave_a if wave_a > 0 else 0
                
                if 0.8 <= c_to_a_ratio <= 1.618:
                    confidence = min(0.8, 0.5 + (0.3 if 0.95 <= c_to_a_ratio <= 1.05 else 0))
                    
                    return {
                        "valid": True,
                        "type": "correction_complete",
                        "count": "ABC correction",
                        "next_trend": "SHORT",
                        "entry_zone": pC,
                        "confidence": confidence,
                        "c_to_a_ratio": c_to_a_ratio,
                    }
            
            return None
        
        except Exception as e:
            logger.error(f"Error finding correction pattern: {e}")
            return None
    
    def _calculate_wave_confidence(
        self,
        waves: List[float],
        pattern_type: str
    ) -> float:
        """
        Calculate confidence score for a wave pattern.
        
        Args:
            waves: List of wave magnitudes
            pattern_type: Type of pattern (impulse or correction)
        
        Returns:
            Confidence score (0-1)
        """
        try:
            if pattern_type == "impulse" and len(waves) == 5:
                # Higher confidence if waves follow typical proportions
                # Wave 3 is often the longest
                # Wave 5 is often shorter than wave 3
                
                wave3_longest = waves[2] == max(waves)
                wave3_extended = waves[2] > 1.618 * waves[0]
                wave5_reasonable = waves[4] < waves[2]
                
                confidence = 0.5  # Base confidence
                if wave3_longest:
                    confidence += 0.2
                if wave3_extended:
                    confidence += 0.15
                if wave5_reasonable:
                    confidence += 0.15
                
                return min(1.0, confidence)
            
            return 0.6  # Default moderate confidence
        
        except Exception as e:
            logger.error(f"Error calculating wave confidence: {e}")
            return 0.5
