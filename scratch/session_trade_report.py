import MetaTrader5 as mt5
import datetime

if mt5.initialize():
    # Session started at 09:34:59 IST today
    # Broker server time was ~06:04 Server time (offset ~3.5h)
    now = datetime.datetime.now()
    deals = mt5.history_deals_get(now - datetime.timedelta(hours=6), now + datetime.timedelta(hours=1))
    
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
            if d.entry == 0:
                trades[pos_id]["in"].append(d)
            elif d.entry == 1:
                trades[pos_id]["out"].append(d)
                
        session_trades = []
        for pos_id, t_data in trades.items():
            if t_data["out"]:
                in_deals = t_data["in"]
                out_deals = t_data["out"]
                profit = sum(d.profit + d.swap + d.commission for d in out_deals)
                in_time = datetime.datetime.fromtimestamp(in_deals[0].time) if in_deals else None
                out_time = datetime.datetime.fromtimestamp(out_deals[-1].time)
                # Filter for trades closed after 11:30 Server time (09:00 IST)
                if out_time >= now - datetime.timedelta(hours=5):
                    side = "BUY" if in_deals and in_deals[0].type == 0 else "SELL"
                    in_price = in_deals[0].price if in_deals else 0.0
                    out_price = out_deals[-1].price if out_deals else 0.0
                    vol = sum(d.volume for d in in_deals) if in_deals else out_deals[-1].volume
                    comment = out_deals[-1].comment
                    session_trades.append({
                        "pos_id": pos_id,
                        "side": side,
                        "vol": vol,
                        "in_price": in_price,
                        "out_price": out_price,
                        "profit": profit,
                        "in_time": in_time,
                        "out_time": out_time,
                        "comment": comment
                    })
        
        session_trades.sort(key=lambda x: x["out_time"])
        print(f"=== TRADES IN CURRENT SESSION (COUNT: {len(session_trades)}) ===")
        win_count = 0
        loss_count = 0
        total_pnl = 0.0
        for i, t in enumerate(session_trades, 1):
            dur = (t['out_time'] - t['in_time']).total_seconds() if t['in_time'] else 0
            dur_str = f"{int(dur//60)}m {int(dur%60)}s" if dur < 3600 else f"{dur/3600:.1f}h"
            outcome = "WIN " if t['profit'] > 0 else ("SCRATCH" if t['profit'] == 0 else "LOSS")
            if t['profit'] > 0: win_count += 1
            elif t['profit'] < 0: loss_count += 1
            total_pnl += t['profit']
            print(f"{i:2d}. #{t['pos_id']} | {t['side']} {t['vol']:.2f} | In: {t['in_price']:.2f} -> Out: {t['out_price']:.2f} | Dur: {dur_str:7s} | PnL: ${t['profit']:+6.2f} [{outcome}] | {t['comment']}")
        
        print("\n=== SESSION SUMMARY ===")
        print(f"Total Session Trades: {len(session_trades)}")
        print(f"Wins: {win_count} | Losses: {loss_count}")
        print(f"Session Win Rate: {win_count / len(session_trades) * 100:.1f}%")
        print(f"Session Net PnL: ${total_pnl:+.2f}")
    mt5.shutdown()

