with open("web_app.py", "r", encoding="utf-8") as f:
    code = f.read()

target = '''            # One-time startup / account switch historical catchup (last 90 days)
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
                    logger.debug(f"Initial trade history sync: {ex}")'''

replacement = '''            # One-time startup / account switch historical catchup (last 90 days)
            if not self.has_initial_history_sync:
                self.has_initial_history_sync = True
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
                except Exception as ex:
                    logger.debug(f"Initial trade history sync: {ex}")'''

if target in code:
    code = code.replace(target, replacement, 1)
    with open("web_app.py", "w", encoding="utf-8") as f:
        f.write(code)
    print("Fixed has_initial_history_sync flag placement!")
else:
    print("Target not found in web_app.py")

