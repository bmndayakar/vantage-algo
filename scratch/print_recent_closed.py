import csv

with open("closed_trades.csv", "r", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

print(f"Total rows in CSV: {len(rows)}")
print("--- LATEST 12 CLOSED TRADES ---")
for r in rows[:12]: # remember rows are sorted reverse=True (most recent first)
    print(f"#{r['ticket']} | {r['type']:4s} {r['volume']} lot | Open: {r['open_time_ist']} @ {r['open_price']} | Close: {r['close_time_ist']} @ {r['close_price']} | PnL: ${float(r['net_pnl']):+7.2f} | Dur: {r['duration_str']:>6s} | {r['session_tag']}")

