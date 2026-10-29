import urllib.request
import json
import datetime
import MetaTrader5 as mt5

print("=== 1. FULL WEB APP SNAPSHOT ===")
try:
    with urllib.request.urlopen("http://localhost:8000/api/state", timeout=3) as resp:
        data = json.loads(resp.read().decode())
        print(f"is_running: {data.get('is_running')}")
        print(f"symbol: {data.get('symbol')}")
        bot = data.get("bot", {})
        print(f"Bot Status: {bot.get('status')}")
        print(f"Bot Nopen: {bot.get('nopen')}")
        print(f"Bot Basket: {bot.get('basket')}")
        print(f"Bot Exposure: {bot.get('exposure')}%")
        print(f"Bot Peak: {bot.get('peak')}")
        print(f"Bot Trail Stop: {bot.get('trail_stop')}")
        print(f"Bot TP Price: {bot.get('tp_price')}")
        print(f"Eff Trail Arm: {bot.get('eff_trail_arm')}")
        print(f"Eff Grid SL: {bot.get('eff_grid_sl')}")
        print(f"Eff Grid TP: {bot.get('eff_grid_tp')}")
        print(f"Eff Grid Step Loss: {bot.get('eff_grid_step_loss')}")
        print(f"Eff Target Profit: {bot.get('eff_target_profit')}")
        print(f"Eff Bailout Target: {bot.get('eff_bailout_target')}")
        print("\nTelemetry:")
        telem = data.get("telemetry", {})
        for k, v in telem.items():
            print(f"  {k}: {v}")
        print("\nLast 5 events:")
        for ev in data.get("events", [])[-5:]:
            print(f"  {ev}")
        print("\nOpen Positions in web app:")
        for p in data.get("positions", []):
            print(f"  {p}")
except Exception as e:
    print(f"Web App request failed: {e}")

print("\n=== 2. MT5 DIRECT FORENSICS ===")
if mt5.initialize():
    positions = mt5.positions_get()
    print(f"Positions count: {len(positions) if positions else 0}")
    if positions:
        for p in positions:
            t_open = datetime.datetime.fromtimestamp(p.time)
            print(f"Ticket: {p.ticket}")
            print(f"  Symbol: {p.symbol}")
            print(f"  Type: {'BUY' if p.type == 0 else 'SELL'}")
            print(f"  Volume: {p.volume}")
            print(f"  Magic: {p.magic}")
            print(f"  Open Price: {p.price_open}")
            print(f"  Current Price: {p.price_current}")
            print(f"  Profit: ${p.profit:.2f}")
            print(f"  Swap: ${p.swap:.2f}")
            print(f"  SL: {p.sl} | TP: {p.tp}")
            print(f"  Open Time (Server): {t_open}")
            age_min = (datetime.datetime.now() - t_open).total_seconds() / 60
            print(f"  Local age approx: {age_min:.1f} min")
            
    # Also check latest deals from today
    now = datetime.datetime.now()
    deals = mt5.history_deals_get(now - datetime.timedelta(hours=6), now + datetime.timedelta(hours=1))
    print(f"\nDeals in last 6 hours count: {len(deals) if deals else 0}")
    if deals:
        for d in deals[-5:]:
            dt_deal = datetime.datetime.fromtimestamp(d.time)
            print(f"  Deal {d.ticket} | Order {d.order} | Sym: {d.symbol} | Type: {d.type} | Entry: {d.entry} | Vol: {d.volume} | Price: {d.price} | Profit: ${d.profit:.2f} | Time: {dt_deal} | Comment: {d.comment}")
    mt5.shutdown()

