import MetaTrader5 as mt5
import datetime

if mt5.initialize():
    now = datetime.datetime.now()
    deals = mt5.history_deals_get(now - datetime.timedelta(hours=4), now + datetime.timedelta(hours=1))
    
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
                
        trades_list = []
        for pos_id, t_data in trades.items():
            if t_data["out"]:
                in_deals = t_data["in"]
                out_deals = t_data["out"]
                profit = sum(d.profit + d.swap + d.commission for d in out_deals)
                in_time = datetime.datetime.fromtimestamp(in_deals[0].time) if in_deals else None
                out_time = datetime.datetime.fromtimestamp(out_deals[-1].time)
                side = "BUY" if in_deals and in_deals[0].type == 0 else "SELL"
                in_price = in_deals[0].price if in_deals else 0.0
                out_price = out_deals[-1].price if out_deals else 0.0
                vol = sum(d.volume for d in in_deals) if in_deals else out_deals[-1].volume
                comment = out_deals[-1].comment
                trades_list.append({
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
        
        trades_list.sort(key=lambda x: x["out_time"])
        print(f"=== ALL DEALS IN LAST 4 HOURS (COUNT: {len(trades_list)}) ===")
        for i, t in enumerate(trades_list, 1):
            dur = (t['out_time'] - t['in_time']).total_seconds() if t['in_time'] else 0
            dur_str = f"{int(dur//60)}m {int(dur%60)}s" if dur < 3600 else f"{dur/3600:.1f}h"
            outcome = "WIN " if t['profit'] > 0 else ("SCRATCH" if t['profit'] == 0 else "LOSS")
            t_out_str = t['out_time'].strftime('%H:%M:%S')
            print(f"{i:2d}. #{t['pos_id']} | {t['side']} {t['vol']:.2f} | In: {t['in_price']:.2f} -> Out: {t['out_price']:.2f} ({t_out_str}) | Dur: {dur_str:7s} | PnL: ${t['profit']:+6.2f} [{outcome}] | {t['comment']}")

    mt5.shutdown()

