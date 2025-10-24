"""
Test if trading symbols are valid on Binance Futures.

Usage: python test_symbols.py
"""

import requests
import sys

def test_symbol(symbol):
    """Test if a symbol is valid on Binance Futures."""
    # Ensure it ends with USDT
    if not symbol.endswith("USDT"):
        symbol = f"{symbol}USDT"
    
    url = f"https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={symbol}"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                'valid': True,
                'symbol': symbol,
                'price': float(data['lastPrice']),
                'change': float(data['priceChangePercent']),
                'volume': float(data['quoteVolume'])
            }
        else:
            return {'valid': False, 'symbol': symbol, 'error': 'Not found on Binance Futures'}
    except Exception as e:
        return {'valid': False, 'symbol': symbol, 'error': str(e)}


def test_multiple_symbols(symbols):
    """Test multiple symbols and show results."""
    print("=" * 80)
    print("Binance Futures Symbol Validator")
    print("=" * 80)
    print()
    
    valid_symbols = []
    invalid_symbols = []
    
    for symbol in symbols:
        result = test_symbol(symbol)
        
        if result['valid']:
            valid_symbols.append(result['symbol'])
            print(f"✅ {result['symbol']:<15} "
                  f"${result['price']:>12,.4f}  "
                  f"{result['change']:>8.2f}%  "
                  f"Vol: ${result['volume']:>15,.0f}")
        else:
            invalid_symbols.append(result['symbol'])
            print(f"❌ {result['symbol']:<15} {result['error']}")
    
    print()
    print("=" * 80)
    print(f"Valid: {len(valid_symbols)}/{len(symbols)}")
    print("=" * 80)
    
    if valid_symbols:
        print()
        print("✅ Add these to your .env SYMBOLS line:")
        print()
        print("SYMBOLS=" + ",".join(valid_symbols))
    
    if invalid_symbols:
        print()
        print(f"❌ Invalid symbols ({len(invalid_symbols)}):")
        for sym in invalid_symbols:
            print(f"   - {sym}")
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    # Test popular symbols
    print()
    print("Testing popular trading symbols...")
    print()
    
    # You can customize this list
    test_symbols = [
        # Top Market Cap
        "BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOGE", "DOT", "LINK",
        
        # Popular Altcoins
        "MATIC", "UNI", "LTC", "ATOM", "ARB", "OP", "SUI", "SEI",
        
        # DeFi
        "AAVE", "MKR", "COMP", "CRV", "SNX",
        
        # Meme Coins (High volatility)
        "SHIB", "PEPE", "FLOKI", "WIF", "BONK",
        
        # Layer 1s
        "NEAR", "APT", "INJ", "TIA", "FTM",
        
        # Metaverse/Gaming
        "SAND", "MANA", "GALA", "AXS", "IMX",
        
        # Other Popular
        "FIL", "ICP", "RNDR", "WLD", "STX", "LDO"
    ]
    
    test_multiple_symbols(test_symbols)
    
    print()
    print("💡 TIP: To test custom symbols, edit the test_symbols list in this file")
    print()
