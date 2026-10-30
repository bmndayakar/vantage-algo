import sys

with open("web_app.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add compute_win_rate_stats function after sync_closed_trades_to_csv
fn_code = '''

def compute_win_rate_stats(filepath: str, server_offset: float = 2.0) -> Dict[str, Any]:
    """
    Computes institutional win rate and loss statistics across four key horizons:
    - Today (current IST calendar day)
    - Yesterday (previous IST calendar day)
    - This Week (Monday 00:00:00 to now)
    - This Month (1st day of month 00:00:00 to now)

    Returns structured metrics:
    - wins, losses, scratches/breakeven, total
    - win_pct (float), loss_pct (float)
    - net_pnl (float)
    """
    now_ist = dt.datetime.utcnow() + dt.timedelta(hours=5, minutes=30)
    today_date = now_ist.date()
    yesterday_date = today_date - dt.timedelta(days=1)
    week_start = today_date - dt.timedelta(days=today_date.weekday())
    month_start = today_date.replace(day=1)

    periods = {
        "today": {"label": "Today", "wins": 0, "losses": 0, "be": 0, "total": 0, "pnl": 0.0, "win_pct": 0.0, "loss_pct": 0.0},
        "yesterday": {"label": "Yesterday", "wins": 0, "losses": 0, "be": 0, "total": 0, "pnl": 0.0, "win_pct": 0.0, "loss_pct": 0.0},
        "this_week": {"label": "This Week", "wins": 0, "losses": 0, "be": 0, "total": 0, "pnl": 0.0, "win_pct": 0.0, "loss_pct": 0.0},
        "this_month": {"label": "This Month", "wins": 0, "losses": 0, "be": 0, "total": 0, "pnl": 0.0, "win_pct": 0.0, "loss_pct": 0.0},
    }

    if not os.path.exists(filepath):
        return periods

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                close_str = r.get("close_time_ist", "")
                if not close_str:
                    continue
                date_part = close_str.split(" ")[0]
                try:
                    d_obj = dt.datetime.strptime(date_part, "%Y-%m-%d").date()
                except Exception:
                    continue

                try:
                    pnl = float(r.get("net_pnl", 0.0))
                except Exception:
                    pnl = 0.0

                is_win = pnl > 0.001
                is_loss = pnl < -0.001
                is_be = not is_win and not is_loss

                matches = []
                if d_obj == today_date:
                    matches.append("today")
                if d_obj == yesterday_date:
                    matches.append("yesterday")
                if week_start <= d_obj <= today_date:
                    matches.append("this_week")
                if month_start <= d_obj <= today_date:
                    matches.append("this_month")

                for m in matches:
                    bucket = periods[m]
                    bucket["total"] += 1
                    bucket["pnl"] += pnl
                    if is_win:
                        bucket["wins"] += 1
                    elif is_loss:
                        bucket["losses"] += 1
                    else:
                        bucket["be"] += 1

        for k, b in periods.items():
            tot = b["total"]
            w = b["wins"]
            l = b["losses"]
            b["win_pct"] = round((w / tot * 100.0), 1) if tot > 0 else 0.0
            b["loss_pct"] = round((l / tot * 100.0), 1) if tot > 0 else 0.0
            b["pnl"] = round(b["pnl"], 2)

    except Exception as e:
        logger.error(f"Error computing win rate stats: {e}")

    return periods
'''

target_sync_end = '    return added_count\n\n\ndef load_trade_excursions()'
if target_sync_end not in content:
    print("Could not find target_sync_end")
    sys.exit(1)

content = content.replace(target_sync_end, '    return added_count\n' + fn_code + '\n\ndef load_trade_excursions()')

# 2. Add caching fields to BotManager.__init__
init_target = '        self.has_initial_history_sync: bool = False'
init_replacement = '''        self.has_initial_history_sync: bool = False
        self._cached_win_rate_stats: Dict[str, Any] = {}
        self._last_win_rate_calc_time: float = 0.0
        self._last_csv_mtime: float = 0.0'''

if init_target not in content:
    print("Could not find init_target")
    sys.exit(1)

content = content.replace(init_target, init_replacement)

# 3. Add get_win_rate_stats method to BotManager
offset_target = '    def get_server_offset(self) -> float:'
method_code = '''    def get_win_rate_stats(self) -> Dict[str, Any]:
        """Returns institutional win rate metrics cached against closed_trades.csv mtime."""
        try:
            mtime = os.path.getmtime(CLOSED_TRADES_FILE) if os.path.exists(CLOSED_TRADES_FILE) else 0.0
        except Exception:
            mtime = 0.0
        if mtime != self._last_csv_mtime or (time.time() - self._last_win_rate_calc_time > 5.0) or not self._cached_win_rate_stats:
            self._cached_win_rate_stats = compute_win_rate_stats(CLOSED_TRADES_FILE, self.get_server_offset())
            self._last_csv_mtime = mtime
            self._last_win_rate_calc_time = time.time()
        return self._cached_win_rate_stats

    def get_server_offset(self) -> float:'''

if offset_target not in content:
    print("Could not find offset_target")
    sys.exit(1)

content = content.replace(offset_target, method_code)

# 4. Add win_rate_stats to snapshot()
snapshot_target = '            "history_period": self.history_period,\n            "events": list(self.events),'
snapshot_replacement = '            "history_period": self.history_period,\n            "win_rate_stats": self.get_win_rate_stats(),\n            "events": list(self.events),'

if snapshot_target not in content:
    print("Could not find snapshot_target")
    sys.exit(1)

content = content.replace(snapshot_target, snapshot_replacement)

# 5. Add /api/performance endpoint
perf_endpoint = '''
@app.get("/api/performance")
async def get_performance():
    return manager.get_win_rate_stats()
'''

if 'manager = BotManager()' in content:
    content = content.replace('manager = BotManager()', 'manager = BotManager()' + perf_endpoint)

with open("web_app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("web_app.py updated successfully!")

