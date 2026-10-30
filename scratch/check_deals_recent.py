import MetaTrader5 as mt5
from datetime import datetime, timezone, timedelta

if not mt5.initialize():
    quit()

deals = mt5.history_deals_get(datetime.now() - timedelta(hours=6), datetime.now())
# Let's inspect the last 15 deals
for d in deals[-15:]:
    # d.time is broker unix timestamp
    dt_utc = datetime.fromtimestamp(d.time, tz=timezone.utc)
    # Server is UTC+3 (or UTC+2)
    print(f"Deal {d.ticket}: time={datetime.fromtimestamp(d.time)} type={'BUY' if d.type==0 else 'SELL'} entry={'IN' if d.entry==0 else 'OUT'} profit={d.profit:.2f} comment={d.comment}")

mt5.shutdown()

