import MetaTrader5 as mt5
import datetime as dt

if not mt5.initialize():
    print("MT5 init failed")
    exit(1)

# Check terminal time
tick = mt5.symbol_info_tick("XAUUSD")
print(f"XAUUSD Tick: Bid={tick.bid}, Ask={tick.ask}, Spread={round(tick.ask-tick.bid, 2)}, Time={dt.datetime.fromtimestamp(tick.time)}")

# Get all deals from today (broker midnight to future)
now_ts = tick.time
start_ts = now_ts - (12 * 3600) # last 12 hours
deals = mt5.history_deals_get(start_ts, now_ts + 3600)
print(f"Total deals in last 12h: {len(deals) if deals else 0}")

if deals:
    # Sort strictly by time_msc descending
    deals_sorted = sorted(deals, key=lambda d: getattr(d, 'time_msc', d.time * 1000), reverse=True)
    print("\n--- LATEST 25 DEALS ---")
    for d in deals_sorted[:25]:
        entry_str = "IN" if d.entry == 0 else ("OUT" if d.entry == 1 else "INOUT")
        type_str = "BUY" if d.type == 0 else ("SELL" if d.type == 1 else str(d.type))
        dt_str = dt.datetime.fromtimestamp(d.time).strftime("%Y-%m-%d %H:%M:%S")
        print(f"DEAL #{d.ticket} | Pos #{d.position_id} | {dt_str} | {entry_str:<3} {type_str:<4} | Vol: {d.volume} @ {d.price:.2f} | PnL: ${d.profit:+.2f} | Comm: ${d.commission:.2f} | Magic: {d.magic} | {d.comment}")

# Check currently open positions
pos = mt5.positions_get()
print(f"\n--- CURRENTLY OPEN POSITIONS ({len(pos) if pos else 0}) ---")
if pos:
    for p in pos:
        type_str = "BUY" if p.type == 0 else "SELL"
        print(f"OPEN #{p.ticket} | {type_str} {p.volume} @ {p.price_open:.2f} -> Current {p.price_current:.2f} | Floating PnL: ${p.profit:+.2f} | Magic: {p.magic} | Comment: {p.comment}")

mt5.shutdown()

