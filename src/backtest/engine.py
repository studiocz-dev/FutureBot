"""
Backtesting engine module.

Provides simple backtesting functionality for signal strategies.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd

from ..signals.wyckoff import WyckoffAnalyzer
from ..signals.elliott import ElliottWaveAnalyzer
from ..signals.fuse import SignalFuser
from ..bot.logger import get_logger

logger = get_logger(__name__)


class BacktestEngine:
    """
    Simple backtesting engine for trading signals.
    
    Simulates signal generation on historical data and tracks performance.
    """
    
    def __init__(
        self,
        initial_balance: float = 10000.0,
        position_size_percent: float = 0.02,  # 2% per trade
        commission: float = 0.001,  # 0.1% commission
    ):
        """
        Initialize backtest engine.
        
        Args:
            initial_balance: Starting balance
            position_size_percent: Position size as % of balance
            commission: Trading commission
        """
        self.initial_balance = initial_balance
        self.position_size_percent = position_size_percent
        self.commission = commission
        
        # Initialize analyzers (not connected to live systems)
        self.wyckoff = WyckoffAnalyzer()
        self.elliott = ElliottWaveAnalyzer()
    
    async def run_backtest(
        self,
        candles: List[Dict[str, Any]],
        symbol: str,
        timeframe: str,
        enable_wyckoff: bool = True,
        enable_elliott: bool = True,
        min_confidence: float = 0.65,
        allow_single_method: bool = False,
        single_method_confidence: float = 0.75,
    ) -> Dict[str, Any]:
        """
        Run backtest on historical candles.
        
        Args:
            candles: Historical candles
            symbol: Trading symbol
            timeframe: Timeframe
            enable_wyckoff: Use Wyckoff analysis
            enable_elliott: Use Elliott Wave analysis
            min_confidence: Minimum confidence threshold (for combined signals)
            allow_single_method: Allow signals from single method if confidence is very high
            single_method_confidence: Minimum confidence for single-method signals
        
        Returns:
            Backtest results dictionary
        """
        logger.info(f"Starting backtest: {symbol} {timeframe} ({len(candles)} candles)")
        
        balance = self.initial_balance
        trades: List[Dict[str, Any]] = []
        open_position: Optional[Dict[str, Any]] = None
        
        # Need enough candles for analysis
        min_candles = 50
        
        for i in range(min_candles, len(candles)):
            historical = candles[:i]
            current_candle = candles[i]
            current_price = float(current_candle["close"])
            
            # Check for open position exit
            if open_position:
                exit_reason = None
                exit_price = None
                
                if open_position["type"] == "LONG":
                    if current_candle["high"] >= open_position["take_profit"]:
                        exit_reason = "TP"
                        exit_price = open_position["take_profit"]
                    elif current_candle["low"] <= open_position["stop_loss"]:
                        exit_reason = "SL"
                        exit_price = open_position["stop_loss"]
                
                else:  # SHORT
                    if current_candle["low"] <= open_position["take_profit"]:
                        exit_reason = "TP"
                        exit_price = open_position["take_profit"]
                    elif current_candle["high"] >= open_position["stop_loss"]:
                        exit_reason = "SL"
                        exit_price = open_position["stop_loss"]
                
                if exit_reason:
                    # Close position
                    entry_price = open_position["entry_price"]
                    position_size = open_position["size"]
                    
                    if open_position["type"] == "LONG":
                        pnl = (exit_price - entry_price) * position_size
                    else:
                        pnl = (entry_price - exit_price) * position_size
                    
                    # Subtract commissions
                    pnl -= (entry_price * position_size * self.commission)
                    pnl -= (exit_price * position_size * self.commission)
                    
                    balance += pnl
                    
                    open_position["exit_price"] = exit_price
                    open_position["exit_reason"] = exit_reason
                    open_position["pnl"] = pnl
                    open_position["balance_after"] = balance
                    
                    logger.debug(f"Closed {open_position['type']} at {exit_price} ({exit_reason}), PnL: {pnl:.2f}")
                    
                    trades.append(open_position)
                    open_position = None
            
            # Generate signal if no open position
            if not open_position:
                # Run analyses
                wyckoff_result = self.wyckoff.analyze(historical, symbol, timeframe) if enable_wyckoff else None
                elliott_result = self.elliott.analyze(historical, symbol, timeframe) if enable_elliott else None
                
                # Determine signal
                signal = self._simple_fuse(
                    wyckoff_result, 
                    elliott_result, 
                    min_confidence, 
                    current_price,
                    allow_single_method,
                    single_method_confidence
                )
                
                if signal:
                    # Open position
                    position_value = balance * self.position_size_percent
                    position_size = position_value / current_price
                    
                    open_position = {
                        "type": signal["type"],
                        "entry_price": current_price,
                        "stop_loss": signal["stop_loss"],
                        "take_profit": signal["take_profit"],
                        "size": position_size,
                        "confidence": signal["confidence"],
                        "entry_time": current_candle.get("open_time"),
                        "balance_before": balance,
                    }
                    
                    logger.debug(f"Opened {signal['type']} at {current_price}")
        
        # Close any remaining open position at final price
        if open_position:
            final_price = float(candles[-1]["close"])
            if open_position["type"] == "LONG":
                pnl = (final_price - open_position["entry_price"]) * open_position["size"]
            else:
                pnl = (open_position["entry_price"] - final_price) * open_position["size"]
            
            balance += pnl
            open_position["exit_price"] = final_price
            open_position["exit_reason"] = "EOD"
            open_position["pnl"] = pnl
            open_position["balance_after"] = balance
            trades.append(open_position)
        
        # Calculate statistics
        results = self._calculate_results(trades, balance)
        
        logger.info(f"Backtest complete: {len(trades)} trades, Final balance: ${balance:.2f}")
        
        return results
    
    def _simple_fuse(
        self,
        wyckoff: Optional[Dict[str, Any]],
        elliott: Optional[Dict[str, Any]],
        min_confidence: float,
        current_price: float,
        allow_single_method: bool = False,
        single_method_confidence: float = 0.75
    ) -> Optional[Dict[str, Any]]:
        """
        Simple signal fusion for backtesting.
        
        Args:
            wyckoff: Wyckoff result
            elliott: Elliott result
            min_confidence: Minimum confidence for combined signals
            current_price: Current price for SL/TP calculation
            allow_single_method: Allow single-method signals
            single_method_confidence: Min confidence for single-method
        
        Returns:
            Signal or None
        """
        wyckoff_signal = wyckoff.get("signal") if wyckoff else None
        elliott_signal = elliott.get("signal") if elliott else None
        wyckoff_conf = wyckoff.get("confidence", 0) if wyckoff else 0
        elliott_conf = elliott.get("confidence", 0) if elliott else 0
        
        signal_type = None
        confidence = 0
        
        # Priority 1: Both methods agree (use lower confidence threshold)
        if wyckoff_signal and elliott_signal and wyckoff_signal == elliott_signal:
            avg_confidence = (wyckoff_conf + elliott_conf) / 2
            if avg_confidence >= min_confidence:
                signal_type = wyckoff_signal
                confidence = avg_confidence
        
        # Priority 2: Single method with very high confidence (if enabled)
        elif allow_single_method:
            if wyckoff_signal and wyckoff_conf >= single_method_confidence:
                signal_type = wyckoff_signal
                confidence = wyckoff_conf
            elif elliott_signal and elliott_conf >= single_method_confidence:
                signal_type = elliott_signal
                confidence = elliott_conf
        
        # No valid signal
        if not signal_type:
            return None
        
        # Calculate stop loss and take profit (simplified, no ATR in backtest)
        if signal_type == "LONG":
            stop_loss = current_price * 0.98  # 2% below
            take_profit = current_price * 1.04  # 4% above
        else:  # SHORT
            stop_loss = current_price * 1.02  # 2% above
            take_profit = current_price * 0.96  # 4% below
        
        return {
            "type": signal_type,
            "confidence": confidence,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
        }
    
    def _calculate_results(
        self,
        trades: List[Dict[str, Any]],
        final_balance: float
    ) -> Dict[str, Any]:
        """
        Calculate backtest statistics.
        
        Args:
            trades: List of completed trades
            final_balance: Final account balance
        
        Returns:
            Results dictionary
        """
        if not trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "total_pnl_percent": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "largest_win": 0.0,
                "largest_loss": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "final_balance": final_balance,
                "trades": trades,
            }
        
        winning_trades = [t for t in trades if t["pnl"] > 0]
        losing_trades = [t for t in trades if t["pnl"] <= 0]
        
        total_pnl = sum(t["pnl"] for t in trades)
        total_pnl_percent = ((final_balance - self.initial_balance) / self.initial_balance) * 100
        
        # Calculate max drawdown
        peak = self.initial_balance
        max_dd = 0.0
        
        for trade in trades:
            balance = trade["balance_after"]
            if balance > peak:
                peak = balance
            dd = ((peak - balance) / peak) * 100
            max_dd = max(max_dd, dd)
        
        results = {
            "total_trades": len(trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": len(winning_trades) / len(trades) if trades else 0.0,
            "total_pnl": total_pnl,
            "total_pnl_percent": total_pnl_percent,
            "avg_win": sum(t["pnl"] for t in winning_trades) / len(winning_trades) if winning_trades else 0.0,
            "avg_loss": sum(t["pnl"] for t in losing_trades) / len(losing_trades) if losing_trades else 0.0,
            "largest_win": max((t["pnl"] for t in winning_trades), default=0.0),
            "largest_loss": min((t["pnl"] for t in losing_trades), default=0.0),
            "max_drawdown": max_dd,
            "sharpe_ratio": 0.0,  # TODO: Implement Sharpe ratio calculation
            "final_balance": final_balance,
            "trades": trades,
        }
        
        return results


def print_backtest_results(results: Dict[str, Any]) -> None:
    """
    Print backtest results in a formatted way.
    
    Args:
        results: Backtest results dictionary
    """
    print("\n" + "="*60)
    print("BACKTEST RESULTS")
    print("="*60)
    print(f"Total Trades:      {results['total_trades']}")
    print(f"Winning Trades:    {results['winning_trades']}")
    print(f"Losing Trades:     {results['losing_trades']}")
    print(f"Win Rate:          {results['win_rate']:.2%}")
    print(f"Total PnL:         ${results['total_pnl']:.2f} ({results['total_pnl_percent']:.2f}%)")
    print(f"Average Win:       ${results['avg_win']:.2f}")
    print(f"Average Loss:      ${results['avg_loss']:.2f}")
    print(f"Largest Win:       ${results['largest_win']:.2f}")
    print(f"Largest Loss:      ${results['largest_loss']:.2f}")
    print(f"Max Drawdown:      {results['max_drawdown']:.2f}%")
    print(f"Final Balance:     ${results['final_balance']:.2f}")
    print("="*60 + "\n")
