import MetaTrader5 as mt5
from datetime import datetime, timedelta
import numpy as np

if not mt5.initialize():
    print("mt5 fail")
    quit()

# Look at M1 bars from 16:00 to now (last ~8 hours)
# 8 hours = 480 bars
rates = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M1, 0, 500)
print(f"Total M1 bars fetched: {len(rates)}")

# Check last trade deal time
deals = mt5.history_deals_get(datetime.now() - timedelta(hours=10), datetime.now())
out_deals = [d for d in (deals or []) if d.entry == 1]
print(f"Total closed deals in last 10 hours: {len(out_deals)}")
if out_deals:
    last_d = out_deals[-1]
    print(f"Last closed deal: {datetime.fromtimestamp(last_d.time)} Pos #{last_d.position_id} Profit: ${last_d.profit:.2f}")

mt5.shutdown()
