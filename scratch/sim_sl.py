import csv

with open('closed_trades.csv', 'r', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

t = [r for r in rows if r.get('close_time_ist', '').startswith('2026-10-30')]
losses = [float(r['net_pnl']) for r in t if float(r.get('net_pnl', 0)) < 0]
wins = [float(r['net_pnl']) for r in t if float(r.get('net_pnl', 0)) > 0]
win_sum = sum(wins)

print(f"Actual Today: 25 Wins (+${win_sum:.2f}), 8 Losses (${sum(losses):.2f}) -> Net: ${win_sum + sum(losses):.2f}")

for sl in [3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 20.0]:
    capped = [-min(abs(l), sl) for l in losses]
    net = win_sum + sum(capped)
    avg_l = sum(capped) / len(losses)
    print(f"Capped SL at ${sl:4.1f}: Total Loss = ${sum(capped):6.2f} | Avg Loss = ${avg_l:5.2f} | Net Today = ${net:+6.2f} (Flip to PROFIT!)" if net > 0 else f"Capped SL at ${sl:4.1f}: Total Loss = ${sum(capped):6.2f} | Avg Loss = ${avg_l:5.2f} | Net Today = ${net:+6.2f}")

