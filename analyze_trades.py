"""
analyze_trades.py - Institutional Quantitative Trade & Timeframe Performance Analyzer
Analyzes closed_trades.csv to reveal optimal trading sessions, peak hours,
holding durations, excursion efficiency (MFE/MAE), and directional edge.

Usage:
    python analyze_trades.py
    python analyze_trades.py --file closed_trades.csv
    python analyze_trades.py --days 7
"""
import argparse
import csv
import datetime as dt
import os
import sys
from collections import defaultdict
from typing import Dict, List, Any

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV = os.path.join(HERE, "closed_trades.csv")


def parse_float(val: Any, default: float = 0.0) -> float:
    try:
        if val is None or str(val).strip() == "":
            return default
        return float(str(val).replace("$", "").replace(",", "").replace("+", "").strip())
    except (ValueError, TypeError):
        return default


def load_trades(csv_path: str, max_days: int = 0) -> List[Dict[str, Any]]:
    if not os.path.exists(csv_path):
        print(f"[!] Warning: Trade ledger file '{csv_path}' not found.")
        print("    Ensure the trading bot or web dashboard has run, or specify --file <path>.")
        return []

    trades = []
    now_dt = dt.datetime.now()
    cutoff_dt = now_dt - dt.timedelta(days=max_days) if max_days > 0 else None

    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("ticket"):
                continue

            # Optional days filter
            if cutoff_dt and row.get("close_time_ist"):
                try:
                    close_str = row["close_time_ist"].replace(" IST", "").strip()
                    row_dt = dt.datetime.strptime(close_str, "%Y-%m-%d %H:%M:%S")
                    if row_dt < cutoff_dt:
                        continue
                except Exception:
                    pass

            trades.append(row)

    return trades


def run_analysis(trades: List[Dict[str, Any]], title_suffix: str = ""):
    if not trades:
        print("\n[!] No trade records available to analyze in the specified ledger.")
        return

    n_total = len(trades)
    wins = [t for t in trades if t.get("outcome") == "WIN"]
    losses = [t for t in trades if t.get("outcome") == "LOSS"]
    breakevens = [t for t in trades if t.get("outcome") == "BE"]

    n_wins = len(wins)
    n_losses = len(losses)
    n_be = len(breakevens)

    win_rate = (n_wins / n_total) * 100.0 if n_total > 0 else 0.0
    loss_rate = (n_losses / n_total) * 100.0 if n_total > 0 else 0.0

    net_pnls = [parse_float(t.get("net_pnl", 0.0)) for t in trades]
    tot_pnl = sum(net_pnls)
    tot_volume = sum(parse_float(t.get("volume", 0.0)) for t in trades)

    win_pnls = [parse_float(t.get("net_pnl", 0.0)) for t in wins]
    loss_pnls = [abs(parse_float(t.get("net_pnl", 0.0))) for t in losses]

    gross_win = sum(win_pnls)
    gross_loss = sum(loss_pnls)
    profit_factor = (gross_win / gross_loss) if gross_loss > 0 else (999.0 if gross_win > 0 else 0.0)

    avg_win = (gross_win / n_wins) if n_wins > 0 else 0.0
    avg_loss = (gross_loss / n_losses) if n_losses > 0 else 0.0
    payoff_ratio = (avg_win / avg_loss) if avg_loss > 0 else 0.0
    expectancy = (tot_pnl / n_total) if n_total > 0 else 0.0

    durations = [parse_float(t.get("duration_sec", 0.0)) for t in trades]
    avg_duration_sec = sum(durations) / len(durations) if durations else 0
    avg_duration_min = avg_duration_sec / 60.0

    mfes = [parse_float(t.get("mfe")) for t in trades if t.get("mfe")]
    maes = [parse_float(t.get("mae")) for t in trades if t.get("mae")]
    avg_mfe = sum(mfes) / len(mfes) if mfes else 0.0
    avg_mae = sum(maes) / len(maes) if maes else 0.0

    print("=" * 82)
    print(f"      VANTAGE QUANTITATIVE TRADE & TIMEFRAME PERFORMANCE REPORT {title_suffix}")
    print("=" * 82)
    print(f"Total Closed Trades   : {n_total:<12} Total Volume       : {tot_volume:.2f} lots")
    print(f"Win / Loss / BE       : {n_wins}W / {n_losses}L / {n_be}BE   Win Rate           : {win_rate:.1f}% (Loss: {loss_rate:.1f}%)")
    print(f"Net Realized PnL      : ${tot_pnl:>+10.2f}    Profit Factor      : {profit_factor:.2f}")
    print(f"Expectancy / Trade    : ${expectancy:>+10.2f}    Payoff Ratio       : {payoff_ratio:.2f} (Avg Win: +${avg_win:.2f} / Loss: -${avg_loss:.2f})")
    print(f"Average Duration      : {avg_duration_min:.1f} min ({int(avg_duration_sec)}s)  Avg Excursion (MFE): +${avg_mfe:.2f}  |  Avg Drawdown (MAE): ${avg_mae:.2f}")
    print("-" * 82)

    # 1. MARKET SESSION ANALYSIS
    session_data = defaultdict(lambda: {"count": 0, "wins": 0, "losses": 0, "pnl": 0.0, "mfe": [], "mae": []})
    for t in trades:
        s = t.get("session_tag") or "Other"
        pnl = parse_float(t.get("net_pnl", 0.0))
        session_data[s]["count"] += 1
        if t.get("outcome") == "WIN":
            session_data[s]["wins"] += 1
        elif t.get("outcome") == "LOSS":
            session_data[s]["losses"] += 1
        session_data[s]["pnl"] += pnl
        if t.get("mfe"): session_data[s]["mfe"].append(parse_float(t["mfe"]))
        if t.get("mae"): session_data[s]["mae"].append(parse_float(t["mae"]))

    print("\n[ 1. PERFORMANCE BY MARKET SESSION ]")
    print(f"{'Market Session (IST Window)':<28} {'Trades':<8} {'Win Rate':<10} {'Net PnL':<12} {'Avg MFE':<10} {'Avg MAE':<10}")
    print("-" * 82)
    for s, d in sorted(session_data.items(), key=lambda x: x[1]["pnl"], reverse=True):
        wr = (d["wins"] / d["count"]) * 100 if d["count"] > 0 else 0.0
        am = (sum(d["mfe"]) / len(d["mfe"])) if d["mfe"] else 0.0
        aa = (sum(d["mae"]) / len(d["mae"])) if d["mae"] else 0.0
        tag = "[BEST]" if d["pnl"] == max(x["pnl"] for x in session_data.values()) and d["pnl"] > 0 else ""
        print(f"{s:<28} {d['count']:<8} {wr:>5.1f}%    ${d['pnl']:>+9.2f}  ${am:>+7.2f}   ${aa:>+7.2f}  {tag}")

    # 2. HOLDING TIMEFRAME ANALYSIS
    tf_data = defaultdict(lambda: {"count": 0, "wins": 0, "losses": 0, "pnl": 0.0})
    for t in trades:
        tf = t.get("timeframe_tag") or "Unclassified"
        pnl = parse_float(t.get("net_pnl", 0.0))
        tf_data[tf]["count"] += 1
        if t.get("outcome") == "WIN": tf_data[tf]["wins"] += 1
        elif t.get("outcome") == "LOSS": tf_data[tf]["losses"] += 1
        tf_data[tf]["pnl"] += pnl

    print("\n[ 2. PERFORMANCE BY HOLDING TIMEFRAME ]")
    print(f"{'Duration Category':<30} {'Trades':<8} {'Win Rate':<10} {'Net PnL':<12} {'Avg PnL/Trade':<14}")
    print("-" * 82)
    for tf, d in sorted(tf_data.items(), key=lambda x: x[1]["pnl"], reverse=True):
        wr = (d["wins"] / d["count"]) * 100 if d["count"] > 0 else 0.0
        avg_p = (d["pnl"] / d["count"]) if d["count"] > 0 else 0.0
        print(f"{tf:<30} {d['count']:<8} {wr:>5.1f}%    ${d['pnl']:>+9.2f}  ${avg_p:>+11.2f}")

    # 3. HOURLY DISTRIBUTION (IST)
    hourly_data = defaultdict(lambda: {"count": 0, "wins": 0, "losses": 0, "pnl": 0.0})
    for t in trades:
        try:
            h = int(t.get("open_hour_ist", -1))
        except Exception:
            h = -1
        if h >= 0:
            pnl = parse_float(t.get("net_pnl", 0.0))
            hourly_data[h]["count"] += 1
            if t.get("outcome") == "WIN": hourly_data[h]["wins"] += 1
            elif t.get("outcome") == "LOSS": hourly_data[h]["losses"] += 1
            hourly_data[h]["pnl"] += pnl

    if hourly_data:
        print("\n[ 3. HOURLY BREAKDOWN (INDIAN STANDARD TIME - IST) ]")
        print(f"{'Hour (IST)':<14} {'Trades':<8} {'Win Rate':<10} {'Net PnL':<12} {'Visual Distribution'}")
        print("-" * 82)
        for h in range(24):
            if h in hourly_data:
                d = hourly_data[h]
                wr = (d["wins"] / d["count"]) * 100 if d["count"] > 0 else 0.0
                bar_len = min(25, int(abs(d["pnl"]) / 5.0) if abs(d["pnl"]) > 0 else 1)
                bar_char = "#" if d["pnl"] >= 0 else "-"
                bar = bar_char * bar_len
                color_pnl = f"${d['pnl']:>+9.2f}"
                print(f"{h:02d}:00 - {h:02d}:59   {d['count']:<8} {wr:>5.1f}%    {color_pnl}   {bar}")

    # 4. DIRECTION & ORIGIN EDGE
    dir_data = defaultdict(lambda: {"count": 0, "wins": 0, "pnl": 0.0})
    for t in trades:
        pos_type = t.get("type", "UNKNOWN")
        dir_data[pos_type]["count"] += 1
        if t.get("outcome") == "WIN": dir_data[pos_type]["wins"] += 1
        dir_data[pos_type]["pnl"] += parse_float(t.get("net_pnl", 0.0))

    print("\n[ 4. DIRECTIONAL EDGE (BUY VS SELL) ]")
    print(f"{'Direction':<12} {'Trades':<8} {'Win Rate':<10} {'Net PnL':<12}")
    print("-" * 46)
    for pos_type, d in dir_data.items():
        wr = (d["wins"] / d["count"]) * 100 if d["count"] > 0 else 0.0
        print(f"{pos_type:<12} {d['count']:<8} {wr:>5.1f}%    ${d['pnl']:>+9.2f}")

    # 5. KEY QUANTITATIVE TAKEAWAYS
    print("\n" + "=" * 82)
    print("                      STRATEGIC TAKEAWAYS & OPTIMAL WINDOWS")
    print("=" * 82)

    # Best session
    if session_data:
        best_session = max(session_data.items(), key=lambda x: x[1]["pnl"])
        best_wr_session = max(session_data.items(), key=lambda x: (x[1]["wins"] / x[1]["count"] if x[1]["count"] >= 3 else 0))
        print(f"* Peak Profit Session    : {best_session[0]} (${best_session[1]['pnl']:+.2f} over {best_session[1]['count']} trades)")
        if best_wr_session[1]["count"] >= 3:
            wr_b = (best_wr_session[1]["wins"] / best_wr_session[1]["count"]) * 100
            print(f"* Highest Win Rate Session: {best_wr_session[0]} ({wr_b:.1f}% Win Rate)")

    # Best timeframe
    if tf_data:
        best_tf = max(tf_data.items(), key=lambda x: x[1]["pnl"])
        print(f"* Optimal Holding Window : {best_tf[0]} (${best_tf[1]['pnl']:+.2f})")

    # Excursion note
    if avg_mfe > 0 or avg_mae < 0:
        print(f"* Excursion Ratio (MFE/MAE): Peak favorable excursion averaged +${avg_mfe:.2f} vs drawdown -${abs(avg_mae):.2f}.")
        if abs(avg_mae) > 0 and (avg_mfe / abs(avg_mae)) < 1.0:
            print("  [!] Warning: Adverse drawdown exceeds peak profit. Tighten grid spacing or use pullback entries.")

    print("=" * 82 + "\n")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    parser = argparse.ArgumentParser(description="Analyze closed_trades.csv for optimal timeframes and sessions.")
    parser.add_argument("--file", "-f", default=DEFAULT_CSV, help="Path to closed_trades.csv")
    parser.add_argument("--days", "-d", type=int, default=0, help="Analyze only trades within the last N days (0 = all)")
    args = parser.parse_args()

    trades = load_trades(args.file, max_days=args.days)
    suffix = f"(Last {args.days} Days)" if args.days > 0 else "(All Time)"
    run_analysis(trades, title_suffix=suffix)


if __name__ == "__main__":
    main()
