import MetaTrader5 as mt5
import numpy as np
from datetime import datetime, timezone, timedelta

if not mt5.initialize():
    print("MT5 init failed")
    exit(1)

symbol = "XAUUSD"

def calc_ema(arr, span):
    alpha = 2.0 / (span + 1.0)
    ema = [arr[0]]
    for val in arr[1:]:
        ema.append(ema[-1] * (1.0 - alpha) + val * alpha)
    return np.array(ema)

for name, t_start, t_end in [
    ("Sequence 1 (SELL loss: 03:00 - 03:30 UTC)", datetime(2026, 10, 29, 3, 0, tzinfo=timezone.utc), datetime(2026, 10, 29, 3, 30, tzinfo=timezone.utc)),
    ("Sequence 2 (BUY loss: 04:00 - 04:35 UTC)", datetime(2026, 10, 29, 4, 0, tzinfo=timezone.utc), datetime(2026, 10, 29, 4, 35, tzinfo=timezone.utc))
]:
    # Warmup 5 hours prior
    r = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M5, t_start - timedelta(hours=6), t_end)
    print(f"\n=================== {name} ===================")
    if r is not None and len(r) >= 25:
        closes = r["close"]
        ema9 = calc_ema(closes, 9)
        ema21 = calc_ema(closes, 21)
        for i in range(len(r)):
            bar = r[i]
            b_dt = datetime.fromtimestamp(bar['time'], tz=timezone.utc)
            if b_dt >= t_start:
                t_str = b_dt.strftime("%H:%M")
                f = ema9[i]
                s = ema21[i]
                trend = "BULLISH" if f > s else "BEARISH"
                print(f"  {t_str} UTC | Close: {bar['close']:.2f} | EMA9: {f:.2f} | EMA21: {s:.2f} -> {trend}")

mt5.shutdown()
