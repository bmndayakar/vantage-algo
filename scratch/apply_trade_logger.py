import re

with open("web_app.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Add csv import and FileResponse import
if "import csv" not in code:
    code = code.replace("import asyncio", "import asyncio\nimport csv")

code = code.replace(
    "from fastapi.responses import HTMLResponse",
    "from fastapi.responses import HTMLResponse, FileResponse"
)

# 2. Add CLOSED_TRADES_FILE and helpers right after TRADE_EXCURSIONS_FILE
target_file_def = 'TRADE_EXCURSIONS_FILE = os.path.join(HERE, "trade_excursions.json")'
new_helpers = '''TRADE_EXCURSIONS_FILE = os.path.join(HERE, "trade_excursions.json")
CLOSED_TRADES_FILE = os.path.join(HERE, "closed_trades.csv")

CLOSED_TRADES_HEADERS = [
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
    """
    Classifies the trading session based on Indian Standard Time (IST):
    - Asian (Tokyo): 05:30 to 13:30 IST
    - London: 13:30 to 18:30 IST
    - London/NY Overlap: 18:30 to 21:30 IST (Prime Gold volatility)
    - New York: 21:30 to 02:30 IST
    - Pacific / Late US: 02:30 to 05:30 IST
    """
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
    """Classifies trade duration into practical scalping and swing categories."""
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
    """
    Persists closed trades offline into a structured CSV ledger with zero duplicates.
    Enriches each trade with IST/Server timestamps, session tags, duration brackets,
    and excursion telemetry (MFE/MAE) for offline quantitative analysis.
    """
    if not closed_positions:
        return 0

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
            logger.error(f"Error reading existing closed_trades.csv: {e}")

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
            dt_open_server = dt.datetime.utcfromtimestamp(close_ts) if close_ts > 0 else dt.datetime.utcnow()
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
            curr = existing_rows[ticket]
            if (not curr.get("mfe") and mfe_val_str) or (not curr.get("mae") and mae_val_str):
                curr["mfe"] = mfe_val_str
                curr["mae"] = mae_val_str
                curr["mfe_mae_ratio"] = ratio_str
                updated_count += 1

    if added_count > 0 or updated_count > 0 or not os.path.exists(filepath):
        sorted_rows = sorted(
            existing_rows.values(),
            key=lambda r: int(r.get("_close_ts", 0)) if "_close_ts" in r else r.get("close_time_server", ""),
            reverse=True,
        )
        try:
            with open(filepath, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=CLOSED_TRADES_HEADERS, extrasaction="ignore")
                writer.writeheader()
                for r in sorted_rows:
                    writer.writerow(r)
        except Exception as e:
            logger.error(f"Failed to write closed_trades.csv: {e}")

    return added_count'''

code = code.replace(target_file_def, new_helpers)

# 3. Add open_time_ts and duration_sec in reconstruct_closed_positions
target_rec_append = '''            "duration": format_duration(duration_sec),
            "magic": magic,
            "is_bot": is_bot,
            "origin": origin,
            "close_time_ts": close_time,
        })'''

new_rec_append = '''            "duration": format_duration(duration_sec),
            "duration_sec": duration_sec,
            "open_time_ts": open_time,
            "magic": magic,
            "is_bot": is_bot,
            "origin": origin,
            "close_time_ts": close_time,
        })'''

code = code.replace(target_rec_append, new_rec_append)

# 4. In BotManager.__init__, add self.has_initial_history_sync = False
target_bm_init = '''        self.history_period: str = "7d"
        self.session_profit: float = 0.0
        self.session_deals: int = 0'''

new_bm_init = '''        self.history_period: str = "7d"
        self.session_profit: float = 0.0
        self.session_deals: int = 0
        self.has_initial_history_sync: bool = False'''

code = code.replace(target_bm_init, new_bm_init)

# 5. In login_mt5, reset self.has_initial_history_sync = False
target_login = '''                self.error_msg = ""
                # Update saved_accounts.json'''

new_login = '''                self.error_msg = ""
                self.has_initial_history_sync = False
                # Update saved_accounts.json'''

code = code.replace(target_login, new_login)

# 6. In get_mt5_account_and_market, add initial 90-day catchup and auto-sync to CSV
target_deals_sync = '''            deals = mt5.history_deals_get(start_dt, end_dt) or ()
            self.closed_positions_list = reconstruct_closed_positions(
                deals=deals,
                fetch_pos_deals_fn=lambda pid: mt5.history_deals_get(position=pid),
                magics=magics,
                server_offset=server_offset,
                trade_excursions=self.trade_excursions,
            )

            if excursions_dirty and (time.time() - self.last_excursions_save > 5.0):
                self.last_excursions_save = time.time()
                save_trade_excursions(self.trade_excursions)'''

new_deals_sync = '''            # One-time startup / account switch historical catchup (last 90 days)
            if not self.has_initial_history_sync:
                try:
                    catchup_start = server_now_dt - dt.timedelta(days=90)
                    all_deals = mt5.history_deals_get(catchup_start, end_dt) or ()
                    all_closed = reconstruct_closed_positions(
                        deals=all_deals,
                        fetch_pos_deals_fn=lambda pid: mt5.history_deals_get(position=pid),
                        magics=magics,
                        server_offset=server_offset,
                        trade_excursions=self.trade_excursions,
                    )
                    if all_closed:
                        sync_closed_trades_to_csv(CLOSED_TRADES_FILE, all_closed, server_offset=server_offset)
                    self.has_initial_history_sync = True
                except Exception as ex:
                    logger.debug(f"Initial trade history sync: {ex}")

            deals = mt5.history_deals_get(start_dt, end_dt) or ()
            self.closed_positions_list = reconstruct_closed_positions(
                deals=deals,
                fetch_pos_deals_fn=lambda pid: mt5.history_deals_get(position=pid),
                magics=magics,
                server_offset=server_offset,
                trade_excursions=self.trade_excursions,
            )

            # Auto-sync closed trades to offline CSV ledger
            if self.closed_positions_list:
                sync_closed_trades_to_csv(
                    filepath=CLOSED_TRADES_FILE,
                    closed_positions=self.closed_positions_list,
                    server_offset=server_offset,
                )

            if excursions_dirty and (time.time() - self.last_excursions_save > 5.0):
                self.last_excursions_save = time.time()
                save_trade_excursions(self.trade_excursions)'''

code = code.replace(target_deals_sync, new_deals_sync)

# 7. Add endpoints: /api/export_trades_csv and /api/trade_analytics
target_endpoint = '''@app.post("/api/reset_goal")
async def reset_goal():
    return manager.reset_session_goal()'''

new_endpoint = '''@app.post("/api/reset_goal")
async def reset_goal():
    return manager.reset_session_goal()


@app.get("/api/export_trades_csv")
async def export_trades_csv():
    """Download the complete offline closed trades CSV ledger."""
    if not os.path.exists(CLOSED_TRADES_FILE):
        with open(CLOSED_TRADES_FILE, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CLOSED_TRADES_HEADERS)
            writer.writeheader()
    filename = f"closed_trades_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return FileResponse(CLOSED_TRADES_FILE, media_type="text/csv", filename=filename)


@app.get("/api/trade_analytics")
async def get_trade_analytics():
    """Returns parsed quantitative performance metrics across sessions and hours."""
    if not os.path.exists(CLOSED_TRADES_FILE):
        return {"status": "ok", "total_trades": 0, "trades": []}
    try:
        trades = []
        with open(CLOSED_TRADES_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                trades.append(r)
        n_total = len(trades)
        n_wins = sum(1 for t in trades if t.get("outcome") == "WIN")
        tot_pnl = round(sum(float(t.get("net_pnl", 0.0)) for t in trades), 2)
        win_rate = round((n_wins / n_total) * 100.0, 1) if n_total > 0 else 0.0
        return {
            "status": "ok",
            "total_trades": n_total,
            "win_rate": win_rate,
            "net_pnl": tot_pnl,
            "trades": trades[:100],
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}'''

code = code.replace(target_endpoint, new_endpoint)

with open("web_app.py", "w", encoding="utf-8") as f:
    f.write(code)

print("web_app.py updated successfully!")

