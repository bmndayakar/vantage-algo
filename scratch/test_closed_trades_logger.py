import datetime as dt
import csv
import os
from typing import List, Dict, Any

CSV_HEADERS = [
    "ticket",
    "symbol",
    "type",
    "volume",
    "open_time_ist",
    "open_time_server",
    "close_time_ist",
    "close_time_server",
    "open_hour_ist",
    "close_hour_ist",
    "day_of_week",
    "session_tag",
    "duration_sec",
    "duration_str",
    "timeframe_tag",
    "open_price",
    "close_price",
    "price_diff",
    "gross_profit",
    "commission",
    "swap",
    "net_pnl",
    "pnl_per_lot",
    "outcome",
    "mfe",
    "mae",
    "mfe_mae_ratio",
    "magic",
    "trade_tag",
]

def classify_session(dt_ist: dt.datetime) -> str:
    h = dt_ist.hour + dt_ist.minute / 60.0
    if 5.5 <= h < 13.5:
        return "Asian (Tokyo)"
    elif 13.5 <= h < 18.5:
        return "London"
    elif 18.5 <= h < 21.5:
        return "London/NY Overlap"
    elif 21.5 <= h or h < 2.5:
        return "New York"
    else:
        return "Pacific/Late US"

def classify_duration(sec: int) -> str:
    if sec < 60:
        return "< 1 min (Hyper Scalp)"
    elif sec < 300:
        return "1 - 5 min (Fast Scalp)"
    elif sec < 900:
        return "5 - 15 min (Standard Scalp)"
    elif sec < 3600:
        return "15 - 60 min (Intraday Swing)"
    else:
        return "> 1 hr (Extended Swing)"

def sync_closed_trades_to_csv(filepath: str, closed_positions: List[Dict[str, Any]], server_offset: float = 2.0) -> int:
    existing_rows: Dict[str, Dict[str, Any]] = {}
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    t = str(row.get("ticket", "")).strip()
                    if t:
                        existing_rows[t] = row
        except Exception as e:
            print(f"Error reading existing csv: {e}")

    added_count = 0
    updated_count = 0

    for pos in closed_positions:
        ticket = str(pos.get("ticket", "")).strip()
        if not ticket:
            continue

        open_ts = int(pos.get("open_time_ts", 0))
        close_ts = int(pos.get("close_time_ts", 0))
        duration_sec = int(pos.get("duration_sec", 0))
        vol = float(pos.get("volume", 0.0))
        p_open = float(pos.get("price_open", 0.0))
        p_close = float(pos.get("price_close", 0.0))
        net_pnl = float(pos.get("profit", 0.0))
        pos_type = str(pos.get("type", "BUY")).upper()

        if open_ts > 0:
            dt_open_server = dt.datetime.utcfromtimestamp(open_ts)
            dt_open_utc = dt_open_server - dt.timedelta(hours=server_offset)
            dt_open_ist = dt_open_utc + dt.timedelta(hours=5, minutes=30)
        else:
            dt_open_server = dt.datetime.utcfromtimestamp(close_ts)
            dt_open_ist = dt_open_server

        if close_ts > 0:
            dt_close_server = dt.datetime.utcfromtimestamp(close_ts)
            dt_close_utc = dt_close_server - dt.timedelta(hours=server_offset)
            dt_close_ist = dt_close_utc + dt.timedelta(hours=5, minutes=30)
        else:
            dt_close_server = dt_open_server
            dt_close_ist = dt_open_ist

        open_time_ist_str = dt_open_ist.strftime("%Y-%m-%d %H:%M:%S IST")
        open_time_srv_str = dt_open_server.strftime("%Y-%m-%d %H:%M:%S")
        close_time_ist_str = dt_close_ist.strftime("%Y-%m-%d %H:%M:%S IST")
        close_time_srv_str = dt_close_server.strftime("%Y-%m-%d %H:%M:%S")

        day_of_week = dt_open_ist.strftime("%A")
        session_tag = classify_session(dt_open_ist)
        timeframe_tag = classify_duration(duration_sec)

        price_diff = round(p_close - p_open if pos_type == "BUY" else p_open - p_close, 2)
        pnl_per_lot = round(net_pnl / vol, 2) if vol > 0 else 0.0
        outcome = "WIN" if net_pnl > 0.001 else ("LOSS" if net_pnl < -0.001 else "BE")

        mfe = pos.get("mfe")
        mae = pos.get("mae")
        mfe_val_str = f"{float(mfe):+.2f}" if mfe is not None else ""
        mae_val_str = f"{float(mae):+.2f}" if mae is not None else ""
        if mfe is not None and mae is not None and abs(float(mae)) > 0.001:
            ratio_str = f"{abs(float(mfe) / float(mae)):.2f}"
        else:
            ratio_str = ""

        row_data = {
            "ticket": ticket,
            "symbol": str(pos.get("symbol", "XAUUSD")),
            "type": pos_type,
            "volume": f"{vol:.2f}",
            "open_time_ist": open_time_ist_str,
            "open_time_server": open_time_srv_str,
            "close_time_ist": close_time_ist_str,
            "close_time_server": close_time_srv_str,
            "open_hour_ist": str(dt_open_ist.hour),
            "close_hour_ist": str(dt_close_ist.hour),
            "day_of_week": day_of_week,
            "session_tag": session_tag,
            "duration_sec": str(duration_sec),
            "duration_str": str(pos.get("duration", "")),
            "timeframe_tag": timeframe_tag,
            "open_price": f"{p_open:.2f}",
            "close_price": f"{p_close:.2f}",
            "price_diff": f"{price_diff:+.2f}",
            "gross_profit": f"{float(pos.get('gross_profit', 0.0)):.2f}",
            "commission": f"{float(pos.get('commission', 0.0)):.2f}",
            "swap": f"{float(pos.get('swap', 0.0)):.2f}",
            "net_pnl": f"{net_pnl:+.2f}",
            "pnl_per_lot": f"{pnl_per_lot:+.2f}",
            "outcome": outcome,
            "mfe": mfe_val_str,
            "mae": mae_val_str,
            "mfe_mae_ratio": ratio_str,
            "magic": str(pos.get("magic", 0)),
            "trade_tag": str(pos.get("origin", "B")),
            "_close_ts": close_ts,
        }

        if ticket not in existing_rows:
            existing_rows[ticket] = row_data
            added_count += 1
        else:
            # Check if MFE/MAE or duration updated
            curr = existing_rows[ticket]
            if (not curr.get("mfe") and mfe_val_str) or (not curr.get("mae") and mae_val_str):
                curr["mfe"] = mfe_val_str
                curr["mae"] = mae_val_str
                curr["mfe_mae_ratio"] = ratio_str
                updated_count += 1

    if added_count > 0 or updated_count > 0 or not os.path.exists(filepath):
        # Sort rows by close timestamp descending (newest first)
        sorted_rows = sorted(
            existing_rows.values(),
            key=lambda r: int(r.get("_close_ts", 0)) if "_close_ts" in r else r.get("close_time_server", ""),
            reverse=True,
        )

        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS, extrasaction="ignore")
            writer.writeheader()
            for r in sorted_rows:
                writer.writerow(r)

    return added_count

# Run test
test_file = "scratch/test_closed_trades.csv"
test_positions = [
    {
        "ticket": 50321894,
        "symbol": "XAUUSD",
        "type": "BUY",
        "volume": 0.1,
        "price_open": 4041.5,
        "price_close": 4043.2,
        "profit": 16.3,
        "gross_profit": 17.0,
        "commission": -0.7,
        "swap": 0.0,
        "duration": "4m 23s",
        "duration_sec": 263,
        "open_time_ts": 1793217262,
        "close_time_ts": 1793217525,
        "magic": 123790,
        "origin": "B",
        "mfe": 22.5,
        "mae": -5.2,
    },
    {
        "ticket": 50321895,
        "symbol": "XAUUSD",
        "type": "SELL",
        "volume": 0.1,
        "price_open": 4045.0,
        "price_close": 4048.5,
        "profit": -35.0,
        "gross_profit": -34.3,
        "commission": -0.7,
        "swap": 0.0,
        "duration": "1m 15s",
        "duration_sec": 75,
        "open_time_ts": 1793218000,
        "close_time_ts": 1793218075,
        "magic": 123790,
        "origin": "B",
        "mfe": 4.0,
        "mae": -36.0,
    }
]

added = sync_closed_trades_to_csv(test_file, test_positions)
print(f"Added {added} rows to {test_file}")

# Read back and print
with open(test_file, "r") as f:
    lines = f.readlines()
print(f"Total lines in CSV: {len(lines)}")
for l in lines[:3]:
    print(l.strip())
