import MetaTrader5 as mt5
import datetime

if mt5.initialize():
    # Fetch M1 bars from 09:30 to 11:00 IST (UTC+5:30)
    # Server time is UTC+3 (2.5 hours behind IST)
    # So 09:44 IST = 07:14 Server or similar
    rates = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M1, 0, 90)
    if rates is not None and len(rates) > 0:
        highs = [r['high'] for r in rates]
        lows = [r['low'] for r in rates]
        print(f"Total M1 bars fetched: {len(rates)}")
        print(f"Min low in last 90 bars: {min(lows)}")
        print(f"Max high in last 90 bars: {max(highs)}")
        
        # Check how many bars went below entry price 4036.60
        below_entry = [r for r in rates if r['low'] <= 4036.60]
        above_entry = [r for r in rates if r['high'] > 4036.60]
        print(f"Bars with low <= 4036.60: {len(below_entry)}")
        print(f"Bars with high > 4036.60: {len(above_entry)}")
        
        # Print first 10 and last 10 bars
        print("\nFirst 5 bars in window:")
        for r in rates[:5]:
            t = datetime.datetime.fromtimestamp(r['time'])
            print(f"  {t} | O:{r['open']:.2f} H:{r['high']:.2f} L:{r['low']:.2f} C:{r['close']:.2f}")
        print("\nLast 5 bars in window:")
        for r in rates[-5:]:
            t = datetime.datetime.fromtimestamp(r['time'])
            print(f"  {t} | O:{r['open']:.2f} H:{r['high']:.2f} L:{r['low']:.2f} C:{r['close']:.2f}")
    mt5.shutdown()

