import MetaTrader5 as mt5
import datetime
import urllib.request
import json
import os

print("=== 1. MT5 OPEN POSITIONS ===")
if mt5.initialize():
    pos = mt5.positions_get(symbol="XAUUSD")
    if pos is None:
        pos = mt5.positions_get()
    print(f"Open positions count: {len(pos) if pos else 0}")
    if pos:
        for p in pos:
            t = datetime.datetime.fromtimestamp(p.time)
            side = "BUY" if p.type == 0 else "SELL"
            print(f"Ticket: {p.ticket} | Side: {side} | Lots: {p.volume} | Open: {p.price_open} | Current: {p.price_current} | PnL: ${p.profit:.2f} | Time: {t}")
    
    print("\n=== 2. MT5 CLOSED DEALS TODAY ===")
    now = datetime.datetime.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    deals = mt5.history_deals_get(start - datetime.timedelta(days=1), now + datetime.timedelta(days=1))
    
    # Filter deals for XAUUSD and today
    print(f"Total deals retrieved: {len(deals) if deals else 0}")
    
    # Reconstruct positions from deals
    trades = {}
    if deals:
        for d in deals:
            if d.symbol != "XAUUSD" and d.symbol != "":
                continue
            pos_id = d.position_id
            if pos_id == 0:
                continue
            if pos_id not in trades:
                trades[pos_id] = {"in": [], "out": []}
            if d.entry == 0: # IN
                trades[pos_id]["in"].append(d)
            elif d.entry == 1: # OUT
                trades[pos_id]["out"].append(d)
        
        # Display completed closed trades today
        closed_today = []
        for pos_id, t_data in trades.items():
            if t_data["out"]:
                # calculate summary
                in_deals = t_data["in"]
                out_deals = t_data["out"]
                total_profit = sum(d.profit + d.swap + d.commission for d in out_deals)
                in_time = datetime.datetime.fromtimestamp(in_deals[0].time) if in_deals else None
                out_time = datetime.datetime.fromtimestamp(out_deals[-1].time)
                side = "BUY" if in_deals and in_deals[0].type == 0 else ("SELL" if in_deals and in_deals[0].type == 1 else "UNKNOWN")
                in_price = in_deals[0].price if in_deals else 0.0
                out_price = out_deals[-1].price if out_deals else 0.0
                vol = sum(d.volume for d in in_deals) if in_deals else out_deals[-1].volume
                comment = out_deals[-1].comment or (in_deals[0].comment if in_deals else "")
                closed_today.append({
                    "pos_id": pos_id,
                    "side": side,
                    "volume": vol,
                    "in_price": in_price,
                    "out_price": out_price,
                    "profit": total_profit,
                    "in_time": in_time,
                    "out_time": out_time,
                    "comment": comment
                })
        
        # Sort by out_time
        closed_today.sort(key=lambda x: x["out_time"])
        print(f"\nClosed positions count today: {len(closed_today)}")
        
        # Print trades from last few hours
        print("\n--- Recent Closed Trades (Last 15) ---")
        for ct in closed_today[-15:]:
            t_in = ct['in_time'].strftime('%H:%M:%S') if ct['in_time'] else '?'
            t_out = ct['out_time'].strftime('%H:%M:%S')
            dur = (ct['out_time'] - ct['in_time']).total_seconds() if ct['in_time'] else 0
            dur_str = f"{int(dur//60)}m {int(dur%60)}s" if dur < 3600 else f"{dur/3600:.1f}h"
            print(f"Ticket #{ct['pos_id']} | {ct['side']} {ct['volume']:.2f} lot | In: {ct['in_price']:.2f} ({t_in}) -> Out: {ct['out_price']:.2f} ({t_out}) | Dur: {dur_str} | PnL: ${ct['profit']:+.2f} | {ct['comment']}")
        
        # Today's net PnL summary
        tot_pnl = sum(ct['profit'] for ct in closed_today)
        wins = [ct for ct in closed_today if ct['profit'] > 0]
        losses = [ct for ct in closed_today if ct['profit'] < 0]
        print(f"\nToday's Total Closed Trades: {len(closed_today)}")
        print(f"Wins: {len(wins)} | Losses: {len(losses)} | Win Rate: {len(wins)/len(closed_today)*100 if closed_today else 0:.1f}%")
        print(f"Total Realized PnL: ${tot_pnl:+.2f}")
    
    mt5.shutdown()
else:
    print("MT5 initialization failed!")

print("\n=== 3. WEB APP RUNNING CHECK ===")
try:
    with urllib.request.urlopen("http://localhost:8000/api/state", timeout=3) as resp:
        data = json.loads(resp.read().decode())
        bot = data.get("bot", {})
        print(f"Web App Active: True")
        print(f"Bot Status: {bot.get('status')}")
        print(f"Nopen: {bot.get('nopen')}")
        print(f"Basket PnL: ${bot.get('basket')}")
        print(f"Session Deals: {bot.get('deals')}")
        print(f"Session Profit: ${bot.get('daily')}")
        print(f"HTF Dir: {data.get('telemetry', {}).get('htf_status')}")
except Exception as e:
    print(f"Web App connection failed: {e}")

