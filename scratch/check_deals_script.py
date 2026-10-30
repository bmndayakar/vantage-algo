import MetaTrader5 as mt5
from datetime import datetime

if not mt5.initialize():
    quit()

deals = mt5.history_deals_get(datetime(2026, 10, 30, 0, 0), datetime.now())
for d in (deals or []):
    if d.entry == 1:
        dt_str = datetime.fromtimestamp(d.time).strftime('%Y-%m-%d %H:%M:%S')
        print(f"{dt_str} | Pos: {d.position_id} | Vol: {d.volume} | Profit: ${d.profit:+.2f}")

mt5.shutdown()

