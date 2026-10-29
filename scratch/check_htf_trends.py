import MetaTrader5 as mt5
from datetime import datetime, timezone

if not mt5.initialize():
    print("MT5 init failed")
    exit(1)

symbol = "XAUUSD"

for tf_name, tf in [("M5", mt5.TIMEFRAME_M5), ("M15", mt5.TIMEFRAME_M15)]:
    rates1 = mt5.copy_rates_range(symbol, tf, datetime(2026, 10, 29, 3, 0, tzinfo=timezone.utc), datetime(2026, 10, 29, 3, 30, tzinfo=timezone.utc))
    print(f"\n--- {tf_name} during Sequence 1 (03:00 - 03:30 UTC: SELL loss) ---")
    if rates1 is not None:
        for r in rates1:
            t_str = datetime.fromtimestamp(r['time'], tz=timezone.utc).strftime("%H:%M")
            direction = "BULLISH (GREEN)" if r['close'] > r['open'] else "BEARISH (RED)"
            print(f"  {t_str} UTC: Open={r['open']:.2f}, Close={r['close']:.2f}, High={r['high']:.2f}, Low={r['low']:.2f} -> {direction}")

    rates2 = mt5.copy_rates_range(symbol, tf, datetime(2026, 10, 29, 4, 0, tzinfo=timezone.utc), datetime(2026, 10, 29, 4, 35, tzinfo=timezone.utc))
    print(f"\n--- {tf_name} during Sequence 2 (04:00 - 04:35 UTC: BUY loss) ---")
    if rates2 is not None:
        for r in rates2:
            t_str = datetime.fromtimestamp(r['time'], tz=timezone.utc).strftime("%H:%M")
            direction = "BULLISH (GREEN)" if r['close'] > r['open'] else "BEARISH (RED)"
            print(f"  {t_str} UTC: Open={r['open']:.2f}, Close={r['close']:.2f}, High={r['high']:.2f}, Low={r['low']:.2f} -> {direction}")

mt5.shutdown()

