import MetaTrader5 as mt5
import datetime as dt

if not mt5.initialize():
    exit(1)

orders = mt5.history_orders_get(position=152827470018)
print("Orders count:", len(orders) if orders else 0)
if orders:
    for o in orders:
        print(f"ORDER: ticket={o.ticket}, type={'BUY' if o.type==0 else 'SELL'}, state={o.state}, volume_initial={o.volume_initial}, price_open={o.price_open}, price_current={o.price_current}, sl={o.sl}, tp={o.tp}, time_setup={dt.datetime.fromtimestamp(o.time_setup)}, time_done={dt.datetime.fromtimestamp(o.time_done)}, comment={o.comment}")

deals = mt5.history_deals_get(position=152827470018)
if deals:
    for d in deals:
        print(f"DEAL: ticket={d.ticket}, order={d.order}, entry={d.entry}, type={'BUY' if d.type==0 else 'SELL'}, price={d.price}, profit={d.profit}, time_msc={d.time_msc}, time={dt.datetime.fromtimestamp(d.time)}")

# Check current market price
tick = mt5.symbol_info_tick("XAUUSD")
print("CURRENT TICK XAUUSD:", tick.bid, tick.ask, dt.datetime.fromtimestamp(tick.time))

mt5.shutdown()

