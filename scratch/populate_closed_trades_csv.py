import os
import sys
sys.path.insert(0, os.path.abspath("."))
import MetaTrader5 as mt5
import datetime as dt
from web_app import reconstruct_closed_positions, sync_closed_trades_to_csv, load_trade_excursions, CLOSED_TRADES_FILE

if not mt5.initialize():
    print("Failed to initialize MT5")
    exit(1)

server_now = dt.datetime.now(dt.timezone.utc)
start_dt = server_now - dt.timedelta(days=90)
end_dt = server_now + dt.timedelta(days=1)

deals = mt5.history_deals_get(start_dt, end_dt)
print(f"Total history deals fetched: {len(deals) if deals else 0}")

excursions = load_trade_excursions()
magics = [123790, 789998]

closed_pos = reconstruct_closed_positions(
    deals=deals,
    fetch_pos_deals_fn=lambda pid: mt5.history_deals_get(position=pid),
    magics=magics,
    server_offset=2.0,
    trade_excursions=excursions,
)

print(f"Reconstructed closed positions: {len(closed_pos)}")
added = sync_closed_trades_to_csv(CLOSED_TRADES_FILE, closed_pos, server_offset=2.0)
print(f"Synced to {CLOSED_TRADES_FILE}: {added} trades written.")

mt5.shutdown()
