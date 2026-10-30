import MetaTrader5 as mt5
import datetime

if mt5.initialize():
    # Broker server midnight to tomorrow
    t_start = datetime.datetime(2026, 10, 29, 0, 0, 0)
    t_end = datetime.datetime(2026, 10, 30, 0, 0, 0)
    deals = mt5.history_deals_get(t_start, t_end)
    
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
                
        closed_trades = []
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
                closed_trades.append({
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
        
        closed_trades.sort(key=lambda x: x["out_time"])
        
        # We want to see all trades executed after the user restarted the bot today (~09:35 IST / ~06:05 Server time or after trade #152828312040)
        # Let's find index where ticket == 152828312040 (the stuck trade we resolved earlier)
        stuck_idx = -1
        for idx, t in enumerate(closed_trades):
            if t['pos_id'] == 152828312040:
                stuck_idx = idx
                break
        
        print(f"Total Closed Trades Today: {len(closed_trades)}")
        print(f"Stuck trade #152828312040 index: {stuck_idx}")
        
        recent_trades = closed_trades[stuck_idx:] if stuck_idx != -1 else closed_trades[-20:]
        print(f"\n=== TRADES FROM STUCK TRADE RESOLUTION ONWARD (COUNT: {len(recent_trades)}) ===")
        win_count = 0
        loss_count = 0
        total_pnl = 0.0
        
        # Server to IST offset: server time is 2.5 hours ahead of UTC, or let's check exact difference
        # Earlier: entry 09:44:23 IST was 11:44:23 or 06:14:23 in logs. Let's print out_time directly.
        for i, t in enumerate(recent_trades, 1):
            dur = (t['out_time'] - t['in_time']).total_seconds() if t['in_time'] else 0
            dur_str = f"{int(dur//60)}m {int(dur%60)}s" if dur < 3600 else f"{dur/3600:.1f}h"
            outcome = "WIN " if t['profit'] > 0 else ("SCRATCH" if t['profit'] == 0 else "LOSS")
            if t['profit'] > 0: win_count += 1
            elif t['profit'] < 0: loss_count += 1
            total_pnl += t['profit']
            t_in_str = t['in_time'].strftime('%H:%M:%S') if t['in_time'] else '?'
            t_out_str = t['out_time'].strftime('%H:%M:%S')
            print(f"{i:2d}. Ticket #{t['pos_id']} | {t['side']} {t['vol']:.2f} lot | In: {t['in_price']:.2f} ({t_in_str}) -> Out: {t['out_price']:.2f} ({t_out_str}) | Dur: {dur_str:7s} | PnL: ${t['profit']:+6.2f} [{outcome}] | {t['comment']}")
            
        print("\n=== PERFORMANCE FROM STUCK TRADE ONWARD ===")
        print(f"Trades Count: {len(recent_trades)}")
        print(f"Wins: {win_count} | Losses: {loss_count}")
        print(f"Win Rate: {win_count / len(recent_trades) * 100:.1f}%")
        print(f"Net Realized PnL: ${total_pnl:+.2f}")
        
    mt5.shutdown()

