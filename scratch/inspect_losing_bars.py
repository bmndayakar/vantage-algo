import MetaTrader5 as mt5
from datetime import datetime, timezone

if not mt5.initialize():
    print("MT5 init failed")
    exit(1)

symbol = "XAUUSD"

for name, t_start, t_end in [
    ("Sequence 1 (SELL loss: 03:00 - 03:30 UTC)", datetime(2026, 10, 29, 3, 0, tzinfo=timezone.utc), datetime(2026, 10, 29, 3, 30, tzinfo=timezone.utc)),
    ("Sequence 2 (BUY loss: 04:00 - 04:40 UTC)", datetime(2026, 10, 29, 4, 0, tzinfo=timezone.utc), datetime(2026, 10, 29, 4, 35, tzinfo=timezone.utc))
]:
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, t_start, t_end)
    print(f"\n=================== {name} ===================")
    if rates is not None and len(rates) > 0:
        highs = [r['high'] for r in rates]
        lows = [r['low'] for r in rates]
        print(f"Total M1 bars: {len(rates)}")
        print(f"Price range: Low {min(lows):.2f} -> High {max(highs):.2f} (Delta = ${max(highs) - min(lows):.2f})")
        for i in [0, len(rates)//4, len(rates)//2, 3*len(rates)//4, len(rates)-1]:
            r = rates[i]
            t_str = datetime.fromtimestamp(r['time'], tz=timezone.utc).strftime("%H:%M")
            print(f"  Bar {t_str} UTC: Open={r['open']:.2f}, High={r['high']:.2f}, Low={r['low']:.2f}, Close={r['close']:.2f}")

mt5.shutdown()
