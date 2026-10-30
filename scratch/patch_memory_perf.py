with open("web_app.py", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Add throttle variables to BotManager.__init__
target1 = 'self.has_initial_history_sync: bool = False'
replace1 = '''self.has_initial_history_sync: bool = False
        self.last_history_sync_time: float = 0.0
        self.last_deals_count: int = -1'''
assert target1 in text, "target1 not found"
text = text.replace(target1, replace1, 1)

# 2. In get_mt5_account_and_market, throttle deals fetching and sync
target2 = '''            deals = mt5.history_deals_get(start_dt, end_dt) or ()
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
                )'''

replace2 = '''            now_t = time.time()
            cur_deals = getattr(self.bot, "deals", 0) if self.bot else 0
            deals_changed = (cur_deals != self.last_deals_count)
            time_since_sync = now_t - self.last_history_sync_time

            # Throttle history deal reconstruction: run every 10s or when a trade closes
            if not self.has_initial_history_sync or deals_changed or (time_since_sync >= 10.0):
                self.last_history_sync_time = now_t
                self.last_deals_count = cur_deals
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
                    )'''
assert target2 in text, "target2 not found"
text = text.replace(target2, replace2, 1)

# 3. In snapshot(), limit closed_positions to most recent 50
target3 = '"closed_positions": self.closed_positions_list,'
replace3 = '"closed_positions": self.closed_positions_list[:50],'
assert target3 in text, "target3 not found"
text = text.replace(target3, replace3, 1)

# 4. In websocket_endpoint, throttle loop from 0.2s to 0.8s
target4 = '''            # Send latest state to client 5 times per second
            state = manager.snapshot()
            await ws.send_text(json.dumps(state))
            await asyncio.sleep(0.2)'''

replace4 = '''            # Send latest state to client ~1.25 times per second (smooth, low-latency, zero-leak)
            state = manager.snapshot()
            await ws.send_text(json.dumps(state))
            await asyncio.sleep(0.8)'''
assert target4 in text, "target4 not found"
text = text.replace(target4, replace4, 1)

with open("web_app.py", "w", encoding="utf-8") as f:
    f.write(text)

print("web_app.py successfully patched for performance and memory stability!")

