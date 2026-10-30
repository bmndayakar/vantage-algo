import MetaTrader5 as mt5
from datetime import datetime

if not mt5.initialize():
    print("mt5 init failed")
    quit()

rates = mt5.copy_rates_from_pos('XAUUSD', mt5.TIMEFRAME_M1, 0, 180)
if rates is None or len(rates) == 0:
    print("no rates")
    quit()

highs = [r[2] for r in rates]
lows = [r[3] for r in rates]
closes = [r[4] for r in rates]
times = [datetime.fromtimestamp(r[0]) for r in rates]

print(f"Count: {len(rates)} bars from {times[0]} to {times[-1]}")
print(f"Overall High: {max(highs)}, Low: {min(lows)}, Total Range: {max(highs) - min(lows):.2f}")
print(f"Last 60 bars (1 hr): High: {max(highs[-60:])}, Low: {min(lows[-60:])}, Range: {max(highs[-60:]) - min(lows[-60:]):.2f}")
print(f"Last 30 bars (30 min): High: {max(highs[-30:])}, Low: {min(lows[-30:])}, Range: {max(highs[-30:]) - min(lows[-30:]):.2f}")
print(f"Latest Close: {closes[-1]}")
mt5.shutdown()

