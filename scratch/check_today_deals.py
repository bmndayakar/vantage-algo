import MetaTrader5 as mt5
from datetime import datetime, timezone

if not mt5.initialize():
    print("MT5 init failed")
    exit(1)

deals = mt5.history_deals_get(datetime(2026, 10, 29, 0, 0), datetime(2026, 10, 30, 0, 0))
print(f"Deals on Oct 29: {len(deals) if deals else 0}")
if deals:
    for d in deals[-15:]:
        t_str = datetime.fromtimestamp(d.time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        entry_type = "IN" if d.entry == 0 else "OUT" if d.entry == 1 else f"E{d.entry}"
        side = "BUY" if d.type == 0 else "SELL" if d.type == 1 else f"T{d.type}"
        print(f"DEAL {d.ticket} | Pos {d.position_id} | {t_str} UTC (time={d.time}) | {entry_type:3s} {side:4s} | {d.volume:.2f} @ {d.price:.2f} | PnL: {d.profit:+.2f} | Reason: {d.reason} | Comm: '{d.comment}'")

mt5.shutdown()

