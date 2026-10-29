import MetaTrader5 as mt5
import datetime as dt
import json

if not mt5.initialize():
    print("MT5 initialize failed:", mt5.last_error())
    exit(1)

print("MT5 Initialized successfully")
acc = mt5.account_info()
if acc:
    print(f"Account: #{acc.login} ({acc.server}), Equity: {acc.equity}, Balance: {acc.balance}, Profit: {acc.profit}")

# Check open positions
positions = mt5.positions_get()
print(f"Open Positions count: {len(positions) if positions else 0}")
if positions:
    for p in positions:
        print(f"OPEN: ticket={p.ticket}, symbol={p.symbol}, type={'BUY' if p.type==0 else 'SELL'}, volume={p.volume}, price_open={p.price_open}, price_current={p.price_current}, profit={p.profit}, magic={p.magic}, comment={p.comment}")

# Check recent history deals (last 24 hours)
now = dt.datetime.utcnow()
start = now - dt.timedelta(hours=24)
deals = mt5.history_deals_get(start, now + dt.timedelta(hours=1))
print(f"Deals count in last 24h: {len(deals) if deals else 0}")
if deals:
    for d in sorted(deals, key=lambda x: x.time, reverse=True)[:15]:
        print(f"DEAL: ticket={d.ticket}, pos_id={d.position_id}, type={'BUY' if d.type==0 else 'SELL'}, entry={d.entry}, volume={d.volume}, price={d.price}, profit={d.profit}, comm={d.commission}, swap={d.swap}, magic={d.magic}, comment={d.comment}, time={dt.datetime.fromtimestamp(d.time)}")

# Check specific position 152827470018
pos_deals = mt5.history_deals_get(position=152827470018)
print(f"Deals for pos 152827470018: {len(pos_deals) if pos_deals else 0}")
if pos_deals:
    for d in pos_deals:
        print(f"POS_DEAL 152827470018: ticket={d.ticket}, entry={d.entry}, type={'BUY' if d.type==0 else 'SELL'}, volume={d.volume}, price={d.price}, profit={d.profit}, comm={d.commission}, magic={d.magic}, comment={d.comment}, time={dt.datetime.fromtimestamp(d.time)}")

mt5.shutdown()

