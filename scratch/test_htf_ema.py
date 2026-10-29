import MetaTrader5 as mt5
import numpy as np

if not mt5.initialize():
    print("MT5 init failed")
    exit(1)

symbol = "XAUUSD"
# Fetch 50 bars of M5
r = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 50)
if r is not None and len(r) >= 25:
    closes = r["close"]
    
    # Calculate exponential moving averages
    def calc_ema(arr, span):
        alpha = 2.0 / (span + 1.0)
        ema = [arr[0]]
        for val in arr[1:]:
            ema.append(ema[-1] * (1.0 - alpha) + val * alpha)
        return np.array(ema)
    
    ema9 = calc_ema(closes, 9)
    ema21 = calc_ema(closes, 21)
    
    current_close = closes[-1]
    fast = ema9[-1]
    slow = ema21[-1]
    
    trend = 1 if fast > slow else (-1 if fast < slow else 0)
    print(f"Current M5: Close={current_close:.2f}, EMA9={fast:.2f}, EMA21={slow:.2f} -> Trend={'BULLISH' if trend==1 else 'BEARISH' if trend==-1 else 'NEUTRAL'}")

mt5.shutdown()

