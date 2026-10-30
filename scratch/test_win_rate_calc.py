import csv
import datetime

filepath = "closed_trades.csv"
now_ist = datetime.datetime.now()
today_date = now_ist.date()
yesterday_date = today_date - datetime.timedelta(days=1)

# Start of week (Monday)
week_start = today_date - datetime.timedelta(days=today_date.weekday())

# Start of month
month_start = today_date.replace(day=1)

print(f"Reference Times (IST):")
print(f"  Now: {now_ist}")
print(f"  Today: {today_date}")
print(f"  Yesterday: {yesterday_date}")
print(f"  Week Start (Monday): {week_start}")
print(f"  Month Start: {month_start}")

stats = {
    "today": {"wins": 0, "losses": 0, "be": 0, "total": 0, "pnl": 0.0},
    "yesterday": {"wins": 0, "losses": 0, "be": 0, "total": 0, "pnl": 0.0},
    "this_week": {"wins": 0, "losses": 0, "be": 0, "total": 0, "pnl": 0.0},
    "this_month": {"wins": 0, "losses": 0, "be": 0, "total": 0, "pnl": 0.0},
}

with open(filepath, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for r in reader:
        # e.g. "2026-10-29 12:54:56 IST"
        close_str = r.get("close_time_ist", "")
        if not close_str:
            continue
        # parse date part
        date_part = close_str.split(" ")[0]
        try:
            d_obj = datetime.datetime.strptime(date_part, "%Y-%m-%d").date()
        except Exception:
            continue
            
        pnl = float(r.get("net_pnl", 0.0))
        is_win = pnl > 0.001
        is_loss = pnl < -0.001
        is_be = not is_win and not is_loss
        
        # Check buckets
        # 1. Today
        if d_obj == today_date:
            stats["today"]["total"] += 1
            stats["today"]["pnl"] += pnl
            if is_win: stats["today"]["wins"] += 1
            elif is_loss: stats["today"]["losses"] += 1
            else: stats["today"]["be"] += 1
            
        # 2. Yesterday
        if d_obj == yesterday_date:
            stats["yesterday"]["total"] += 1
            stats["yesterday"]["pnl"] += pnl
            if is_win: stats["yesterday"]["wins"] += 1
            elif is_loss: stats["yesterday"]["losses"] += 1
            else: stats["yesterday"]["be"] += 1
            
        # 3. This Week
        if d_obj >= week_start and d_obj <= today_date:
            stats["this_week"]["total"] += 1
            stats["this_week"]["pnl"] += pnl
            if is_win: stats["this_week"]["wins"] += 1
            elif is_loss: stats["this_week"]["losses"] += 1
            else: stats["this_week"]["be"] += 1
            
        # 4. This Month
        if d_obj >= month_start and d_obj <= today_date:
            stats["this_month"]["total"] += 1
            stats["this_month"]["pnl"] += pnl
            if is_win: stats["this_month"]["wins"] += 1
            elif is_loss: stats["this_month"]["losses"] += 1
            else: stats["this_month"]["be"] += 1

for period, s in stats.items():
    tot = s["total"]
    w = s["wins"]
    l = s["losses"]
    win_pct = round((w / tot * 100.0), 1) if tot > 0 else 0.0
    loss_pct = round((l / tot * 100.0), 1) if tot > 0 else 0.0
    s["win_pct"] = win_pct
    s["loss_pct"] = loss_pct
    s["pnl"] = round(s["pnl"], 2)
    print(f"\n[{period.upper()}]:")
    print(f"  Total: {tot} trades | Net PnL: ${s['pnl']:+.2f}")
    print(f"  Wins: {w} ({win_pct}%) | Losses: {l} ({loss_pct}%) | Scratch/BE: {s['be']}")

