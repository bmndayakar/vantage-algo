import MetaTrader5 as mt5
from datetime import datetime, timedelta

if not mt5.initialize():
    quit()

pos_list = [
    152835677611,
    152835452148,
    152834516285,
    152834442873,
    152834237177,
    152833046343,
    152832755039,
    152832718282
]

print("=== FORENSIC DEEP-DIVE OF TODAY'S 8 LOSSES ===")
for pid in pos_list:
    deals = mt5.history_deals_get(position=pid)
    if not deals:
        print(f"Pos {pid}: No deals found")
        continue
    in_deal = [d for d in deals if d.entry == 0]
    out_deal = [d for d in deals if d.entry == 1]
    
    if in_deal and out_deal:
        i, o = in_deal[0], out_deal[0]
        t_in = datetime.fromtimestamp(i.time)
        t_out = datetime.fromtimestamp(o.time)
        dur_min = (o.time - i.time) / 60.0
        side = "BUY" if i.type == 0 else "SELL"
        pts = (o.price - i.price) if side == "BUY" else (i.price - o.price)
        print(f"Pos {pid}: {side} {i.volume} lots | In: {t_in.strftime('%H:%M:%S')} @ {i.price:.2f} | Out: {t_out.strftime('%H:%M:%S')} @ {o.price:.2f} ({dur_min:.1f}m) | Pts: {pts:+.2f} | PnL: ${o.profit:+.2f} | Out Comment: '{o.comment}'")
    else:
        print(f"Pos {pid}: Partial deals: {len(deals)}")

mt5.shutdown()

