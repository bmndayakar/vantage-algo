import os
import MetaTrader5 as mt5
import datetime as dt

print("MetaTrader5 version:", mt5.__version__)

# Read .env
env = {}
if os.path.exists(".env"):
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            k, sep, v = line.strip().partition("=")
            if sep and not k.startswith("#"):
                env[k.strip()] = v.strip().strip("'\"")

path = env.get("MT5_PATH")
login = int(env.get("MT5_LOGIN", 0))
password = env.get("MT5_PASSWORD")
server = env.get("MT5_SERVER")

print(f"Connecting to MT5 at {path} for account {login} on {server}...")
# Try attaching first
res = mt5.initialize()
if not res:
    res = mt5.initialize(path=path, login=login, password=password, server=server, timeout=10000)

print(f"Init result: {res}, last error: {mt5.last_error()}")
if res:
    acc = mt5.account_info()
    print(f"Logged into: {acc.login} ({acc.server}), Balance: {acc.balance}, Equity: {acc.equity}")
    
    # Check open positions
    open_pos = mt5.positions_get()
    print(f"\n--- OPEN POSITIONS ({len(open_pos) if open_pos else 0}) ---")
    if open_pos:
        for p in open_pos:
            print(f"Ticket: {p.ticket}, Symbol: {p.symbol}, Type: {p.type}, Vol: {p.volume}, OpenPrice: {p.price_open}, Profit: {p.profit}, Magic: {p.magic}, Time: {p.time}")
            
    # Check history deals for last 7 days
    now = dt.datetime.now()
    start = now - dt.timedelta(days=7)
    deals = mt5.history_deals_get(start, now + dt.timedelta(days=1))
    print(f"\n--- HISTORY DEALS LAST 7 DAYS ({len(deals) if deals else 0}) ---")
    if deals:
        for d in deals:
            print(f"DealTicket: {d.ticket}, Order: {d.order}, PosID: {d.position_id}, Symbol: {d.symbol}, Type: {d.type}, Entry: {d.entry}, Vol: {d.volume}, Price: {d.price}, Profit: {d.profit}, Magic: {d.magic}, Time: {d.time}")
            
    # Check history orders
    orders = mt5.history_orders_get(start, now + dt.timedelta(days=1))
    print(f"\n--- HISTORY ORDERS LAST 7 DAYS ({len(orders) if orders else 0}) ---")
    if orders:
        for o in orders:
            print(f"OrderTicket: {o.ticket}, PosID: {getattr(o, 'position_id', 'N/A')}, Symbol: {o.symbol}, Type: {o.type}, State: {o.state}, VolDone: {o.volume_done}, PriceOpen: {o.price_open}, Magic: {o.magic}, Time: {o.time_done}")

    mt5.shutdown()

