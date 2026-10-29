import sys, os
sys.path.insert(0, os.path.abspath("."))
from web_app import sync_closed_trades_to_csv, CLOSED_TRADES_FILE

# Test calling with a simulated trade
fake_trade = [{
    "ticket": 999999999,
    "symbol": "XAUUSD",
    "type": "SELL",
    "volume": 0.1,
    "price_open": 4040.0,
    "price_close": 4039.0,
    "profit": 10.0,
    "open_time_ts": 1793250000,
    "close_time_ts": 1793250100,
    "duration_sec": 100,
    "magic": 123790,
    "origin": "B",
}]

cnt = sync_closed_trades_to_csv(CLOSED_TRADES_FILE, fake_trade, server_offset=2.0)
print(f"Sync successful! Added count: {cnt}")

