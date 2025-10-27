"""
Signal fuser module.

Combines Wyckoff, Elliott Wave, RSI, MACD analysis to generate final trading signals.
"""

import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from .wyckoff import WyckoffAnalyzer
from .elliott import ElliottWaveAnalyzer
from .rsi import RSIAnalyzer
from .macd import MACDAnalyzer
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
        enable_rsi: bool = True,
        enable_macd: bool = True,
        cooldown: int = 300,
        prevent_conflicts: bool = True,
        analysis_candles: int = 2000,
        min_candles: int = 500,
        atr_candles: int = 30,
        tpsl_config: Any = None,  # TPSLConfig
    ):
        """
        Initialize signal fuser.
        
        Args:
            supabase: Supabase client
            min_confidence: Minimum confidence threshold for signals
            enable_wyckoff: Enable Wyckoff analysis
            enable_elliott: Enable Elliott Wave analysis
            enable_rsi: Enable RSI analysis
            enable_macd: Enable MACD analysis
            cooldown: Cooldown period in seconds between signals for same symbol/timeframe
            prevent_conflicts: Prevent conflicting signals (SHORT/LONG) for same symbol within 1 hour
            analysis_candles: Number of candles to fetch for analysis
            min_candles: Minimum candles required for analysis
            atr_candles: Number of candles for ATR calculation
            tpsl_config: Take Profit / Stop Loss configuration
        """
        self.supabase = supabase
        self.min_confidence = min_confidence
        self.enable_wyckoff = enable_wyckoff
        self.enable_elliott = enable_elliott
        self.enable_rsi = enable_rsi
        self.enable_macd = enable_macd
        self.cooldown = cooldown
        self.prevent_conflicts = prevent_conflicts
        self.analysis_candles = analysis_candles
        self.min_candles = min_candles
        self.atr_candles = atr_candles
        self.tpsl_config = tpsl_config
        
        # Initialize analyzers
        self.wyckoff = WyckoffAnalyzer() if enable_wyckoff else None
        self.elliott = ElliottWaveAnalyzer() if enable_elliott else None
        self.rsi = RSIAnalyzer() if enable_rsi else None
        self.macd = MACDAnalyzer() if enable_macd else None
        
        # Track last signal time for cooldown: {(symbol, timeframe): timestamp}
        self.last_signal_time: Dict[tuple, float] = {}
        
        # Track last signal type for conflict prevention: {symbol: (signal_type, timestamp)}
        self.last_signal_type: Dict[str, tuple] = {}
        
        # Per-symbol cooldown to prevent spam from volatile symbols (1 hour)
        self.symbol_cooldown = 3600  # 1 hour in seconds
        self.last_symbol_signal: Dict[str, float] = {}  # {symbol: timestamp}
    
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
            # Check global cooldown (any signal from this symbol+timeframe)
            key = (symbol, timeframe)
            now = time.time()
            
            if key in self.last_signal_time:
                elapsed = now - self.last_signal_time[key]
                if elapsed < self.cooldown:
                    logger.debug(f"Signal cooldown active for {symbol} {timeframe} ({elapsed:.0f}s / {self.cooldown}s)")
                    return None
            
            # Check per-symbol cooldown (prevents spam from volatile symbols)
            if symbol in self.last_symbol_signal:
                elapsed = now - self.last_symbol_signal[symbol]
                if elapsed < self.symbol_cooldown:
                    remaining = self.symbol_cooldown - elapsed
                    logger.debug(f"Symbol cooldown: {symbol} signaled {elapsed/60:.0f}m ago (wait {remaining/60:.0f}m)")
                    return None
            
            # Get historical candles if not provided
            if historical_candles is None:
                historical_candles = await self._fetch_candles(symbol, timeframe, limit=self.analysis_candles)
            
            # Ensure current candle is included
            all_candles = historical_candles + [current_candle]
            
            if len(all_candles) < self.min_candles:
                logger.warning(f"Insufficient candles for analysis: {symbol} {timeframe} (have {len(all_candles)}, need {self.min_candles})")
                return None
            
            current_price = float(current_candle["close"])
            
            # Log analysis start
            logger.info(f"🔍 Analyzing {symbol} {timeframe} @ ${current_price:.4f}")
            
            # Run analyses with error handling
            wyckoff_result = None
            elliott_result = None
            rsi_result = None
            macd_result = None
            
            if self.enable_wyckoff and self.wyckoff:
                try:
                    wyckoff_result = self.wyckoff.analyze(all_candles, symbol, timeframe)
                    wyckoff_signal = wyckoff_result.get('signal')
                    wyckoff_conf = wyckoff_result.get('confidence', 0.0) * 100
                    logger.info(f"  📊 Wyckoff: {wyckoff_signal or 'NONE'} ({wyckoff_conf:.1f}%)")
                except Exception as e:
                    logger.error(f"  📊 Wyckoff: ERROR - {str(e)}")
            else:
                logger.info(f"  📊 Wyckoff: DISABLED")
            
            if self.enable_elliott and self.elliott:
                try:
                    elliott_result = self.elliott.analyze(all_candles, symbol, timeframe)
                    elliott_signal = elliott_result.get('signal')
                    elliott_conf = elliott_result.get('confidence', 0.0) * 100
                    logger.info(f"  🌊 Elliott: {elliott_signal or 'NONE'} ({elliott_conf:.1f}%)")
                except Exception as e:
                    logger.error(f"  🌊 Elliott: ERROR - {str(e)}")
            else:
                logger.info(f"  🌊 Elliott: DISABLED")
            
            if self.enable_rsi and self.rsi:
                try:
                    rsi_result = self.rsi.analyze(all_candles, symbol, timeframe)
                    rsi_signal = rsi_result.get('signal')
                    rsi_conf = rsi_result.get('confidence', 0.0) * 100
                    rsi_value = rsi_result.get('rsi', 50)
                    logger.info(f"  📈 RSI: {rsi_signal or 'NONE'} ({rsi_conf:.1f}%) [RSI={rsi_value:.1f}]")
                except Exception as e:
                    logger.error(f"  📈 RSI: ERROR - {str(e)}")
            else:
                logger.info(f"  📈 RSI: DISABLED")
            
            if self.enable_macd and self.macd:
                try:
                    macd_result = self.macd.analyze(all_candles, symbol, timeframe)
                    macd_signal = macd_result.get('signal')
                    macd_conf = macd_result.get('confidence', 0.0) * 100
                    macd_hist = macd_result.get('histogram', 0)
                    logger.info(f"  📉 MACD: {macd_signal or 'NONE'} ({macd_conf:.1f}%) [Hist={macd_hist:.4f}]")
                except Exception as e:
                    logger.error(f"  📉 MACD: ERROR - {str(e)}")
            else:
                logger.info(f"  📉 MACD: DISABLED")
            
            # Fuse signals
            signal = self._fuse_signals(
                wyckoff=wyckoff_result,
                elliott=elliott_result,
                rsi=rsi_result,
                macd=macd_result,
                candles=all_candles,
                symbol=symbol,
                timeframe=timeframe,
                current_price=current_price,
            )
            
            # Log fusion result
            if not signal:
                logger.info(f"  ❌ No signal generated for {symbol}")
                return None
            
            conf_pct = signal["confidence"] * 100
            if signal["confidence"] < self.min_confidence:
                logger.info(
                    f"  ❌ Signal rejected: {signal['type']} confidence {conf_pct:.1f}% "
                    f"< threshold {self.min_confidence*100:.1f}%"
                )
                return None
            
            logger.info(f"  ✅ Signal candidate: {signal['type']} ({conf_pct:.1f}%)")
            
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
                    
                    # ANTI-SPAM: Prevent same-direction signals within 1 hour unless significant price movement
                    # Reduced from 4 hours for faster swing trading
                    if time_since_last < 3600 and last_type == signal["type"]:  # 1 hour = 3600 seconds
                        # Get the price when last signal was generated
                        last_signals = await self.supabase.get_recent_signals(symbol, limit=1)
                        if last_signals:
                            last_entry_price = float(last_signals[0]["entry_price"])
                            price_change_pct = abs((current_price - last_entry_price) / last_entry_price)
                            
                            # Require at least 1.5% price movement for faster swing (down from 3%)
                            min_movement_required = 0.015
                            
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
                    
                    # Update global cooldown
                    self.last_signal_time[key] = now
                    
                    # Update per-symbol cooldown (prevents spam)
                    self.last_symbol_signal[symbol] = now
                    
                    # Update last signal type for this symbol
                    self.last_signal_type[symbol] = (signal["type"], now)
                    
                    # Log with detailed info
                    entry = signal['entry_price']
                    tp = signal['take_profit']
                    sl = signal['stop_loss']
                    conf_pct = signal['confidence'] * 100
                    rr_ratio = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0
                    
                    logger.info(
                        f"✅ {signal['type']} {symbol} {timeframe} | "
                        f"Entry: ${entry:.4f} | TP: ${tp:.4f} | SL: ${sl:.4f} | "
                        f"Confidence: {conf_pct:.1f}% | R:R {rr_ratio:.2f}:1"
                    )
                    logger.info(f"  🚀 SIGNAL SENT TO DISCORD")
                    
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
        rsi: Optional[Dict[str, Any]],
        macd: Optional[Dict[str, Any]],
        candles: List[Dict[str, Any]],
        symbol: str,
        timeframe: str,
        current_price: float,
    ) -> Optional[Dict[str, Any]]:
        """
        Fuse analysis results into a final signal.
        
        Multi-tiered fusion logic:
        1. If Wyckoff + Elliott agree → High confidence (75-90%)
        2. If Wyckoff or Elliott signals + RSI/MACD confirm → Medium-High confidence (65-75%)
        3. If only RSI + MACD agree → Medium confidence (55-65%)
        4. If only one indicator → Low confidence (rejected)
        
        Args:
            wyckoff: Wyckoff analysis result
            elliott: Elliott Wave analysis result
            rsi: RSI analysis result
            macd: MACD analysis result
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
            rsi_signal = rsi.get("signal") if rsi else None
            macd_signal = macd.get("signal") if macd else None
            
            wyckoff_conf = wyckoff.get("confidence", 0) if wyckoff else 0
            elliott_conf = elliott.get("confidence", 0) if elliott else 0
            rsi_conf = rsi.get("confidence", 0) if rsi else 0
            macd_conf = macd.get("confidence", 0) if macd else 0
            
            # Determine final direction
            final_signal = None
            base_confidence = 0.0
            fusion_reason = ""
            
            # TIER 1: Wyckoff + Elliott Agreement (Highest Confidence: 75-90%)
            if wyckoff_signal and elliott_signal and wyckoff_signal == elliott_signal:
                final_signal = wyckoff_signal
                base_confidence = (wyckoff_conf + elliott_conf) / 2
                
                # Bonus if RSI/MACD also agree
                agreeing_indicators = []
                if rsi_signal == final_signal:
                    base_confidence += 0.05
                    agreeing_indicators.append("RSI")
                if macd_signal == final_signal:
                    base_confidence += 0.05
                    agreeing_indicators.append("MACD")
                
                base_confidence = min(0.95, base_confidence)  # Cap at 95%
                fusion_reason = f"Wyckoff+Elliott agree on {final_signal}"
                if agreeing_indicators:
                    fusion_reason += f" (confirmed by {', '.join(agreeing_indicators)})"
                logger.debug(f"  ✓ TIER 1 Fusion: {fusion_reason} (conf: {base_confidence*100:.1f}%)")
            
            # TIER 2: One Pattern Analyzer + Both Technical Indicators (65-80%)
            elif (wyckoff_signal or elliott_signal) and rsi_signal and macd_signal:
                pattern_signal = wyckoff_signal or elliott_signal
                pattern_conf = wyckoff_conf if wyckoff_signal else elliott_conf
                pattern_name = "Wyckoff" if wyckoff_signal else "Elliott"
                
                if pattern_signal == rsi_signal == macd_signal:
                    final_signal = pattern_signal
                    base_confidence = (pattern_conf + rsi_conf + macd_conf) / 3
                    fusion_reason = f"{pattern_name}+RSI+MACD agree on {final_signal}"
                    logger.debug(f"  ✓ TIER 2 Fusion: {fusion_reason} (conf: {base_confidence*100:.1f}%)")
            
            # TIER 3: RSI + MACD Agreement (55-70%)
            elif rsi_signal and macd_signal and rsi_signal == macd_signal:
                final_signal = rsi_signal
                base_confidence = (rsi_conf + macd_conf) / 2
                fusion_reason = f"RSI+MACD agree on {final_signal}"
                logger.debug(f"  ✓ TIER 3 Fusion: {fusion_reason} (conf: {base_confidence*100:.1f}%)")
            
            # TIER 3.5: Strong Single Technical Indicator (60-75%)
            # RSI alone when EXTREMELY oversold/overbought (≥90%), or MACD with strong crossover (≥75%)
            elif rsi_signal and rsi_conf >= 0.90:
                final_signal = rsi_signal
                base_confidence = rsi_conf * 0.85  # Penalty for lack of confirmation
                fusion_reason = f"Strong RSI {final_signal} alone ({rsi_conf*100:.1f}%)"
                logger.debug(f"  ✓ TIER 3.5 Fusion: {fusion_reason} (conf: {base_confidence*100:.1f}%)")
            
            elif macd_signal and macd_conf >= 0.75:
                final_signal = macd_signal
                base_confidence = macd_conf * 0.85  # Penalty for lack of confirmation
                fusion_reason = f"Strong MACD {final_signal} alone ({macd_conf*100:.1f}%)"
                logger.debug(f"  ✓ TIER 3.5 Fusion: {fusion_reason} (conf: {base_confidence*100:.1f}%)")
            
            # TIER 4: Strong Single Pattern Analyzer (>75% alone)
            elif wyckoff_signal and wyckoff_conf >= 0.75:
                final_signal = wyckoff_signal
                base_confidence = wyckoff_conf * 0.9  # Slight penalty for lack of confirmation
                fusion_reason = f"Strong Wyckoff {final_signal} alone (>75%)"
                logger.debug(f"  ✓ TIER 4 Fusion: {fusion_reason} (conf: {base_confidence*100:.1f}%)")
            
            elif elliott_signal and elliott_conf >= 0.75:
                final_signal = elliott_signal
                base_confidence = elliott_conf * 0.9
                fusion_reason = f"Strong Elliott {final_signal} alone (>75%)"
                logger.debug(f"  ✓ TIER 4 Fusion: {fusion_reason} (conf: {base_confidence*100:.1f}%)")
            
            else:
                # No strong or agreeing signals
                signals_summary = []
                if wyckoff_signal:
                    signals_summary.append(f"Wyckoff={wyckoff_signal}")
                if elliott_signal:
                    signals_summary.append(f"Elliott={elliott_signal}")
                if rsi_signal:
                    signals_summary.append(f"RSI={rsi_signal}")
                if macd_signal:
                    signals_summary.append(f"MACD={macd_signal}")
                
                fusion_reason = f"No agreement or strong signal: {', '.join(signals_summary) if signals_summary else 'No signals'}"
                logger.debug(f"  ✗ Fusion: {fusion_reason}")
                return None
            
            # Get indicator confirmations
            indicator_data = get_indicator_confirmations(candles, final_signal, current_price)
            confirmations = indicator_data.get("confirmations", [])
            indicators = indicator_data.get("indicators", {})
            
            # Adjust confidence based on indicator confirmations
            confirmation_bonus = min(0.15, len(confirmations) * 0.03)
            final_confidence = min(1.0, base_confidence + confirmation_bonus)
            
            # Calculate stop loss and take profit using configured method
            atr = calculate_atr(candles[-self.atr_candles:], period=14)
            
            if self.tpsl_config and self.tpsl_config.use_elliott_wave_targets and elliott:
                # Use Elliott Wave-based TP/SL
                stop_loss, take_profit = self._calculate_elliott_wave_tpsl(
                    entry_price=current_price,
                    signal_type=final_signal,
                    elliott_analysis=elliott,
                    atr=atr,
                )
                logger.info(f"Using Elliott Wave TP/SL for {symbol}: TP={take_profit:.4f}, SL={stop_loss:.4f}")
            else:
                # Use ATR-based TP/SL (default/fallback)
                stop_loss, take_profit = self._calculate_atr_tpsl(
                    entry_price=current_price,
                    signal_type=final_signal,
                    atr=atr,
                )
                logger.info(f"Using ATR-based TP/SL for {symbol}: TP={take_profit:.4f}, SL={stop_loss:.4f}")
            
            # Calculate additional TP levels (1.5x and 2x the main TP distance)
            tp_distance = abs(take_profit - current_price)
            if final_signal == "LONG":
                take_profit_2 = current_price + (tp_distance * 1.5)
                take_profit_3 = current_price + (tp_distance * 2.0)
            else:  # SHORT
                take_profit_2 = current_price - (tp_distance * 1.5)
                take_profit_3 = current_price - (tp_distance * 2.0)
            
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
    
    def _calculate_atr_tpsl(
        self,
        entry_price: float,
        signal_type: str,
        atr: Optional[float],
    ) -> tuple[float, float]:
        """
        Calculate TP/SL using ATR-based method.
        
        Args:
            entry_price: Signal entry price
            signal_type: "LONG" or "SHORT"
            atr: Average True Range value
        
        Returns:
            (stop_loss, take_profit)
        """
        # Get multipliers from config or use defaults
        sl_multiplier = self.tpsl_config.atr_stop_loss_multiplier if self.tpsl_config else 2.0
        tp_multiplier = self.tpsl_config.atr_take_profit_multiplier if self.tpsl_config else 3.0
        
        if signal_type == "LONG":
            stop_loss = entry_price - (atr * sl_multiplier) if atr else entry_price * 0.98
            take_profit = entry_price + (atr * tp_multiplier) if atr else entry_price * 1.04
        else:  # SHORT
            stop_loss = entry_price + (atr * sl_multiplier) if atr else entry_price * 1.02
            take_profit = entry_price - (atr * tp_multiplier) if atr else entry_price * 0.96
        
        return stop_loss, take_profit
    
    def _calculate_elliott_wave_tpsl(
        self,
        entry_price: float,
        signal_type: str,
        elliott_analysis: Dict[str, Any],
        atr: Optional[float],
    ) -> tuple[float, float]:
        """
        Calculate TP/SL using Elliott Wave theory.
        
        Uses Fibonacci relationships and wave invalidation levels.
        
        Args:
            entry_price: Signal entry price
            signal_type: "LONG" or "SHORT"
            elliott_analysis: Elliott Wave analysis data
            atr: Average True Range (used as fallback)
        
        Returns:
            (stop_loss, take_profit)
        """
        try:
            wave_data = elliott_analysis.get("wave_data", {})
            
            # Extract wave information
            wave_1 = wave_data.get("wave_1", {})
            wave_3 = wave_data.get("wave_3", {})
            wave_4 = wave_data.get("wave_4", {})
            
            # Calculate Wave 1 length
            wave_1_start = wave_1.get("start_price")
            wave_1_end = wave_1.get("end_price")
            
            if wave_1_start and wave_1_end:
                wave_1_length = abs(wave_1_end - wave_1_start)
                
                # Get Wave 5 projection ratio from config
                wave_5_ratio = self.tpsl_config.elliott_wave_5_ratio if self.tpsl_config else 1.0
                
                if signal_type == "LONG":
                    # TP: Wave 5 projection = entry + (Wave 1 length × ratio)
                    take_profit = entry_price + (wave_1_length * wave_5_ratio)
                    
                    # SL: Below Wave 4 low (invalidation level)
                    wave_4_low = wave_4.get("low_price")
                    if wave_4_low:
                        stop_loss = wave_4_low * 0.999  # 0.1% buffer
                    else:
                        # Fallback: Use Wave 1 high as invalidation
                        wave_1_high = wave_1.get("end_price", entry_price)
                        stop_loss = min(wave_1_high * 0.995, entry_price * 0.98)
                    
                else:  # SHORT
                    # TP: Wave 5 projection = entry - (Wave 1 length × ratio)
                    take_profit = entry_price - (wave_1_length * wave_5_ratio)
                    
                    # SL: Above Wave 4 high (invalidation level)
                    wave_4_high = wave_4.get("high_price")
                    if wave_4_high:
                        stop_loss = wave_4_high * 1.001  # 0.1% buffer
                    else:
                        # Fallback: Use Wave 1 low as invalidation
                        wave_1_low = wave_1.get("end_price", entry_price)
                        stop_loss = max(wave_1_low * 1.005, entry_price * 1.02)
                
                # Safety check: Ensure minimum risk/reward ratio
                min_rr = self.tpsl_config.min_risk_reward_ratio if self.tpsl_config else 1.2
                risk = abs(entry_price - stop_loss)
                reward = abs(take_profit - entry_price)
                
                if risk > 0 and reward / risk < min_rr:
                    # Adjust TP to meet minimum R:R
                    logger.warning(f"Elliott Wave R:R too low ({reward/risk:.2f}), adjusting TP to meet {min_rr}:1")
                    if signal_type == "LONG":
                        take_profit = entry_price + (risk * min_rr)
                    else:
                        take_profit = entry_price - (risk * min_rr)
                
                logger.info(
                    f"Elliott Wave TP/SL: Wave 1 length={wave_1_length:.4f}, "
                    f"Wave 5 ratio={wave_5_ratio}, R:R={(abs(take_profit-entry_price)/abs(entry_price-stop_loss)):.2f}:1"
                )
                
                return stop_loss, take_profit
            
            else:
                # Wave data incomplete, fall back to ATR
                logger.warning("Incomplete wave data, falling back to ATR-based TP/SL")
                return self._calculate_atr_tpsl(entry_price, signal_type, atr)
        
        except Exception as e:
            logger.error(f"Error calculating Elliott Wave TP/SL: {e}, falling back to ATR")
            return self._calculate_atr_tpsl(entry_price, signal_type, atr)
    
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
