import csv
import os
from collections import defaultdict

def generate_analytics_report(csv_file: str):
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} does not exist.")
        return

    trades = []
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            trades.append(r)

    if not trades:
        print("No trade data found in CSV.")
        return

    n_total = len(trades)
    n_wins = sum(1 for t in trades if t["outcome"] == "WIN")
    n_losses = sum(1 for t in trades if t["outcome"] == "LOSS")
    n_be = sum(1 for t in trades if t["outcome"] == "BE")

    win_rate = (n_wins / n_total) * 100 if n_total > 0 else 0.0
    tot_pnl = sum(float(t["net_pnl"]) for t in trades)
    tot_gross_win = sum(float(t["net_pnl"]) for t in trades if float(t["net_pnl"]) > 0)
    tot_gross_loss = abs(sum(float(t["net_pnl"]) for t in trades if float(t["net_pnl"]) < 0))
    profit_factor = (tot_gross_win / tot_gross_loss) if tot_gross_loss > 0 else (999.0 if tot_gross_win > 0 else 0.0)

    avg_win = (tot_gross_win / n_wins) if n_wins > 0 else 0.0
    avg_loss = (tot_gross_loss / n_losses) if n_losses > 0 else 0.0

    print("=" * 70)
    print("         QUANTITATIVE TRADE & TIMEFRAME PERFORMANCE REPORT")
    print("=" * 70)
    print(f"Total Trades Analyzed : {n_total}")
    print(f"Win / Loss / BE       : {n_wins} Wins | {n_losses} Losses | {n_be} Breakeven")
    print(f"Win Rate              : {win_rate:.1f}%")
    print(f"Net Realized PnL      : ${tot_pnl:+.2f}")
    print(f"Profit Factor         : {profit_factor:.2f}")
    print(f"Average Win / Loss    : +${avg_win:.2f} / -${avg_loss:.2f}")
    print("-" * 70)

    # Session breakdown
    session_data = defaultdict(lambda: {"count": 0, "wins": 0, "pnl": 0.0, "mfe": [], "mae": []})
    for t in trades:
        s = t["session_tag"]
        pnl = float(t["net_pnl"])
        session_data[s]["count"] += 1
        if t["outcome"] == "WIN": session_data[s]["wins"] += 1
        session_data[s]["pnl"] += pnl
        if t.get("mfe"): session_data[s]["mfe"].append(float(t["mfe"]))
        if t.get("mae"): session_data[s]["mae"].append(float(t["mae"]))

    print("\n[ MARKET SESSION PERFORMANCE ]")
    print(f"{'Session Name':<24} {'Trades':<8} {'Win Rate':<10} {'Net PnL':<12} {'Avg MFE':<10} {'Avg MAE':<10}")
    print("-" * 74)
    for s, d in sorted(session_data.items(), key=lambda x: x[1]["pnl"], reverse=True):
        wr = (d["wins"] / d["count"]) * 100 if d["count"] > 0 else 0.0
        avg_m = (sum(d["mfe"]) / len(d["mfe"])) if d["mfe"] else 0.0
        avg_a = (sum(d["mae"]) / len(d["mae"])) if d["mae"] else 0.0
        print(f"{s:<24} {d['count']:<8} {wr:>5.1f}%    ${d['pnl']:>+9.2f}  ${avg_m:>+7.2f}   ${avg_a:>+7.2f}")

    # Timeframe category breakdown
    tf_data = defaultdict(lambda: {"count": 0, "wins": 0, "pnl": 0.0})
    for t in trades:
        tf = t["timeframe_tag"]
        tf_data[tf]["count"] += 1
        if t["outcome"] == "WIN": tf_data[tf]["wins"] += 1
        tf_data[tf]["pnl"] += float(t["net_pnl"])

    print("\n[ HOLDING TIMEFRAME PERFORMANCE ]")
    print(f"{'Holding Time Category':<30} {'Trades':<8} {'Win Rate':<10} {'Net PnL':<12}")
    print("-" * 62)
    for tf, d in sorted(tf_data.items(), key=lambda x: x[1]["pnl"], reverse=True):
        wr = (d["wins"] / d["count"]) * 100 if d["count"] > 0 else 0.0
        print(f"{tf:<30} {d['count']:<8} {wr:>5.1f}%    ${d['pnl']:>+9.2f}")

    print("=" * 70)

generate_analytics_report("scratch/test_closed_trades.csv")

