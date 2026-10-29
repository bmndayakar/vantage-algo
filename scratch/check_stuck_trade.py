import MetaTrader5 as mt5
import urllib.request
import json
import datetime

print("--- MT5 CHECK ---")
if mt5.initialize():
    positions = mt5.positions_get(symbol="XAUUSD")
    print(f"MT5 Connected. Open positions count: {len(positions) if positions else 0}")
    if positions:
        for p in positions:
            t = datetime.datetime.fromtimestamp(p.time)
            side = "BUY" if p.type == 0 else "SELL"
            print(f"Ticket: {p.ticket} | Side: {side} | Vol: {p.volume} | Open: {p.price_open} | Current: {p.price_current} | Profit: ${p.profit:.2f} | OpenTime: {t}")
    mt5.shutdown()
else:
    print("Failed to initialize MT5")

print("\n--- WEB APP STATE CHECK ---")
try:
    with urllib.request.urlopen("http://localhost:8000/api/state", timeout=3) as resp:
        data = json.loads(resp.read().decode())
        print(f"Running: {data.get('running')}")
        print(f"Status: {data.get('status')}")
        print(f"Positions Count (nopen): {data.get('nopen')}")
        print(f"Basket Value: {data.get('basket_val')}")
        print(f"HTF Dir: {data.get('htf_dir')} | HTF Fast: {data.get('htf_fast')} | HTF Slow: {data.get('htf_slow')}")
        print(f"Last Msg: {data.get('last_msg')}")
        print(f"Error Msg: {data.get('error_msg')}")
        print(f"Telemetry: {json.dumps(data.get('telemetry', {}), indent=2)}")
except Exception as e:
    print(f"Web App check failed: {e}")

