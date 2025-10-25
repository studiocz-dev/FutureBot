"""
Signal fuser module.

Combines Wyckoff, Elliott Wave, and indicator analysis to generate final trading signals.
"""

import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from .wyckoff import WyckoffAnalyzer
from .elliott import ElliottWaveAnalyzer
from .indicators import get_indicator_confirmations, calculate_atr
from ..storage.models import calculate_signal_risk_reward
from ..bot.logger import get_logger

logger = get_logger(__name__)


class SignalFuser:
    """
    Fuses multiple analysis methods into final trading signals.
    
    Combines:
    - Wyckoff Method analysis
    - Elliott Wave counting
    - Technical indicators
    - Risk/reward calculations
    """
    
    def __init__(
        self,
        supabase: Any,  # SupabaseClient
        min_confidence: float = 0.65,
        enable_wyckoff: bool = True,
        enable_elliott: bool = True,
        cooldown: int = 300,
        prevent_conflicts: bool = True,
    ):
        """
        Initialize signal fuser.
        
        Args:
            supabase: Supabase client
            min_confidence: Minimum confidence threshold for signals
            enable_wyckoff: Enable Wyckoff analysis
            enable_elliott: Enable Elliott Wave analysis
            cooldown: Cooldown period in seconds between signals for same symbol/timeframe
            prevent_conflicts: Prevent conflicting signals (SHORT/LONG) for same symbol within 1 hour
        """
        self.supabase = supabase
        self.min_confidence = min_confidence
        self.enable_wyckoff = enable_wyckoff
        self.enable_elliott = enable_elliott
        self.cooldown = cooldown
        self.prevent_conflicts = prevent_conflicts
        
        # Initialize analyzers
        self.wyckoff = WyckoffAnalyzer() if enable_wyckoff else None
        self.elliott = ElliottWaveAnalyzer() if enable_elliott else None
        
        # Track last signal time for cooldown: {(symbol, timeframe): timestamp}
        self.last_signal_time: Dict[tuple, float] = {}
        
        # Track last signal type for conflict prevention: {symbol: (signal_type, timestamp)}
        self.last_signal_type: Dict[str, tuple] = {}
    
    async def generate_signal(
        self,
        symbol: str,
        timeframe: str,
        current_candle: Dict[str, Any],
        historical_candles: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a trading signal by fusing multiple analysis methods.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            current_candle: Current closed candle
            historical_candles: Historical candles (if None, will fetch from DB)
        
        Returns:
            Signal dictionary or None if no signal generated
        """
        try:
            # Check cooldown
            key = (symbol, timeframe)
            now = time.time()
            
            if key in self.last_signal_time:
                elapsed = now - self.last_signal_time[key]
                if elapsed < self.cooldown:
                    logger.debug(f"Signal cooldown active for {symbol} {timeframe} ({elapsed:.0f}s / {self.cooldown}s)")
                    return None
            
            # Get historical candles if not provided
            if historical_candles is None:
                historical_candles = await self._fetch_candles(symbol, timeframe, limit=100)
            
            # Ensure current candle is included
            all_candles = historical_candles + [current_candle]
            
            if len(all_candles) < 50:
                logger.warning(f"Insufficient candles for analysis: {symbol} {timeframe}")
                return None
            
            current_price = float(current_candle["close"])
            
            # Run analyses
            wyckoff_result = None
            elliott_result = None
            
            if self.enable_wyckoff and self.wyckoff:
                wyckoff_result = self.wyckoff.analyze(all_candles, symbol, timeframe)
                logger.debug(f"Wyckoff result for {symbol} {timeframe}: {wyckoff_result.get('signal')}")
            
            if self.enable_elliott and self.elliott:
                elliott_result = self.elliott.analyze(all_candles, symbol, timeframe)
                logger.debug(f"Elliott result for {symbol} {timeframe}: {elliott_result.get('signal')}")
            
            # Fuse signals
            signal = self._fuse_signals(
                wyckoff=wyckoff_result,
                elliott=elliott_result,
                candles=all_candles,
                symbol=symbol,
                timeframe=timeframe,
                current_price=current_price,
            )
            
            if signal and signal["confidence"] >= self.min_confidence:
                # Check for conflicting signals (same symbol, opposite direction, within 1 hour)
                if self.prevent_conflicts and symbol in self.last_signal_type:
                    last_type, last_time = self.last_signal_type[symbol]
                    time_since_last = now - last_time
                    
                    if time_since_last < 3600 and last_type != signal["type"]:  # 1 hour = 3600 seconds
                        logger.warning(
                            f"🚫 Conflicting signal blocked: {signal['type']} {symbol} {timeframe} "
                            f"(last signal: {last_type} {time_since_last/60:.1f}m ago). "
                            f"Waiting {(3600-time_since_last)/60:.1f}m before allowing opposite signal."
                        )
                        return None
                    
                    # ANTI-SPAM: Prevent same-direction signals within 4 hours unless significant price movement
                    if time_since_last < 14400 and last_type == signal["type"]:  # 4 hours = 14400 seconds
                        # Get the price when last signal was generated
                        last_signals = await self.supabase.get_recent_signals(symbol, limit=1)
                        if last_signals:
                            last_entry_price = float(last_signals[0]["entry_price"])
                            price_change_pct = abs((current_price - last_entry_price) / last_entry_price)
                            
                            # Require at least 3% price movement to re-signal same direction
                            min_movement_required = 0.03
                            
                            if price_change_pct < min_movement_required:
                                logger.info(
                                    f"⏭️  Skipping {signal['type']} {symbol}: Same direction signal too soon "
                                    f"({time_since_last/3600:.1f}h ago, only {price_change_pct:.1%} price change, need >{min_movement_required:.1%})"
                                )
                                return None
                            else:
                                logger.debug(
                                    f"✓ Allowing {signal['type']} {symbol}: Sufficient price movement "
                                    f"({price_change_pct:.1%} > {min_movement_required:.1%})"
                                )
                
                # Store signal in database
                signal_id = await self.supabase.insert_signal(signal)
                if signal_id:
                    signal["id"] = signal_id
                    
                    # Update cooldown
                    self.last_signal_time[key] = now
                    
                    # Update last signal type for this symbol
                    self.last_signal_type[symbol] = (signal["type"], now)
                    
                    # Log with detailed info
                    entry = signal['entry_price']
                    tp = signal['take_profit']
                    sl = signal['stop_loss']
                    conf_pct = signal['confidence'] * 100
                    
                    logger.info(
                        f"✅ {signal['type']} {symbol} {timeframe} | "
                        f"Entry: ${entry:.4f} | TP: ${tp:.4f} | SL: ${sl:.4f} | "
                        f"Confidence: {conf_pct:.1f}%"
                    )
                    
                    return signal
            else:
                if signal:
                    logger.debug(
                        f"⏸️  {symbol} {timeframe}: Confidence {signal['confidence']:.1%} < {self.min_confidence:.1%} (skipped)"
                    )
            
            return None
        
        except Exception as e:
            logger.error(f"Error generating signal: {e}", exc_info=True)
            return None
    
    def _fuse_signals(
        self,
        wyckoff: Optional[Dict[str, Any]],
        elliott: Optional[Dict[str, Any]],
        candles: List[Dict[str, Any]],
        symbol: str,
        timeframe: str,
        current_price: float,
    ) -> Optional[Dict[str, Any]]:
        """
        Fuse analysis results into a final signal.
        
        Args:
            wyckoff: Wyckoff analysis result
            elliott: Elliott Wave analysis result
            candles: Historical candles
            symbol: Trading symbol
            timeframe: Timeframe
            current_price: Current price
        
        Returns:
            Fused signal or None
        """
        try:
            # Extract signals and confidences
            wyckoff_signal = wyckoff.get("signal") if wyckoff else None
            elliott_signal = elliott.get("signal") if elliott else None
            
            wyckoff_conf = wyckoff.get("confidence", 0) if wyckoff else 0
            elliott_conf = elliott.get("confidence", 0) if elliott else 0
            
            # Determine final direction
            # Both methods must agree, or one must be very strong
            final_signal = None
            
            if wyckoff_signal and elliott_signal:
                if wyckoff_signal == elliott_signal:
                    # Strong agreement
                    final_signal = wyckoff_signal
                    base_confidence = (wyckoff_conf + elliott_conf) / 2
                else:
                    # Disagreement - no signal
                    logger.debug(f"Wyckoff and Elliott disagree: {wyckoff_signal} vs {elliott_signal}")
                    return None
            
            elif wyckoff_signal and wyckoff_conf >= 0.75:
                # Strong Wyckoff signal alone
                final_signal = wyckoff_signal
                base_confidence = wyckoff_conf * 0.9  # Slight penalty for lack of confirmation
            
            elif elliott_signal and elliott_conf >= 0.75:
                # Strong Elliott signal alone
                final_signal = elliott_signal
                base_confidence = elliott_conf * 0.9
            
            else:
                # No strong signals
                return None
            
            # Get indicator confirmations
            indicator_data = get_indicator_confirmations(candles, final_signal, current_price)
            confirmations = indicator_data.get("confirmations", [])
            indicators = indicator_data.get("indicators", {})
            
            # Adjust confidence based on indicator confirmations
            confirmation_bonus = min(0.15, len(confirmations) * 0.03)
            final_confidence = min(1.0, base_confidence + confirmation_bonus)
            
            # Calculate stop loss and take profit
            atr = calculate_atr(candles[-30:], period=14)
            
            if final_signal == "LONG":
                stop_loss = current_price - (atr * 2) if atr else current_price * 0.98
                take_profit = current_price + (atr * 4) if atr else current_price * 1.04
                take_profit_2 = current_price + (atr * 6) if atr else current_price * 1.06
                take_profit_3 = current_price + (atr * 8) if atr else current_price * 1.08
            else:  # SHORT
                stop_loss = current_price + (atr * 2) if atr else current_price * 1.02
                take_profit = current_price - (atr * 4) if atr else current_price * 0.96
                take_profit_2 = current_price - (atr * 6) if atr else current_price * 0.94
                take_profit_3 = current_price - (atr * 8) if atr else current_price * 0.92
            
            # Calculate risk/reward
            rr_metrics = calculate_signal_risk_reward(
                entry=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                signal_type=final_signal,
            )
            
            # Build rationale
            rationale_parts = []
            
            if wyckoff and wyckoff.get("signal") == final_signal:
                rationale_parts.append(f"**Wyckoff ({wyckoff_conf:.0%}):** {'; '.join(wyckoff.get('rationale', []))}")
            
            if elliott and elliott.get("signal") == final_signal:
                rationale_parts.append(f"**Elliott Wave ({elliott_conf:.0%}):** {'; '.join(elliott.get('rationale', []))}")
            
            if confirmations:
                rationale_parts.append(f"**Indicators:** {', '.join(confirmations)}")
            
            rationale_parts.append(f"**Risk/Reward:** {rr_metrics['risk_reward_ratio']:.2f}:1")
            
            rationale = "\n".join(rationale_parts)
            
            # Create signal object
            signal = {
                "symbol": symbol,
                "timeframe": timeframe,
                "type": final_signal,
                "entry_price": current_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "take_profit_2": take_profit_2,
                "take_profit_3": take_profit_3,
                "confidence": final_confidence,
                "wyckoff_phase": wyckoff.get("phase") if wyckoff else None,
                "elliott_wave_count": elliott.get("wave_count") if elliott else None,
                "indicators": indicators,
                "rationale": rationale,
                "atr": atr,
                "risk_reward": rr_metrics,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            return signal
        
        except Exception as e:
            logger.error(f"Error fusing signals: {e}", exc_info=True)
            return None
    
    async def _fetch_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical candles from database.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            limit: Number of candles to fetch
        
        Returns:
            List of candles
        """
        try:
            candles = await self.supabase.get_candles(symbol, timeframe, limit=limit)
            return candles
        except Exception as e:
            logger.error(f"Error fetching candles: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get fuser statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            "min_confidence": self.min_confidence,
            "wyckoff_enabled": self.enable_wyckoff,
            "elliott_enabled": self.enable_elliott,
            "cooldown_seconds": self.cooldown,
            "active_cooldowns": len(self.last_signal_time),
        }
