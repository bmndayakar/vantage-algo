import os

file_path = "web_app.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update compute_entry_telemetry arguments
old_args = """    spread: float = 0.0,
    max_spread: float = 0.50,
    rollover_blackout: bool = True,
    rollover_start_ist: str = "02:15",
    rollover_end_ist: str = "03:30",
    tc: int = 0,
    server_offset: float = 2.0,
    atr: float = 0.0,
    max_atr: float = 0.0,
) -> Dict[str, Any]:"""

new_args = """    spread: float = 0.0,
    max_spread: float = 0.50,
    rollover_blackout: bool = True,
    rollover_start_ist: str = "02:15",
    rollover_end_ist: str = "03:30",
    tc: int = 0,
    server_offset: float = 2.0,
    atr: float = 0.0,
    max_atr: float = 0.0,
    htf_filter: bool = True,
    htf_tf: str = "M5",
    htf_dir: int = 0,
    htf_fast: float = 0.0,
    htf_slow: float = 0.0,
) -> Dict[str, Any]:"""

assert old_args in content, "old_args not found"
content = content.replace(old_args, new_args)

# 2. Update compute_entry_telemetry body for HTF alignment
old_telemetry_body = """    # Lever 2: Dynamic Gates & Rollover Blackout Overrides
    rollover_active = bool(rollover_blackout and bot_module.is_in_rollover_window(tc, server_offset, rollover_start_ist, rollover_end_ist))"""

new_telemetry_body = """    # Lever 3: Higher-Timeframe (HTF) Macro Alignment
    htf_status = "BULLISH" if htf_dir == 1 else ("BEARISH" if htf_dir == -1 else "NEUTRAL")
    if htf_filter and htf_dir != 0:
        if htf_dir == 1: # Bullish: BUY only
            sell_ready = False
            sell_desc = f"Blocked by {htf_tf} Bullish Momentum ({htf_fast:.2f} > {htf_slow:.2f})"
            if side == "both":
                action_side = f"BUY ONLY ({htf_tf} BULLISH)"
                target_entry_price = buy_price
                target_entry_desc = f"Dip to MA: {buy_desc} ({htf_tf} Bullish Aligned)"
        elif htf_dir == -1: # Bearish: SELL only
            buy_ready = False
            buy_desc = f"Blocked by {htf_tf} Bearish Momentum ({htf_fast:.2f} < {htf_slow:.2f})"
            if side == "both":
                action_side = f"SELL ONLY ({htf_tf} BEARISH)"
                target_entry_price = sell_price
                target_entry_desc = f"Rally to MA: {sell_desc} ({htf_tf} Bearish Aligned)"

    # Lever 2: Dynamic Gates & Rollover Blackout Overrides
    rollover_active = bool(rollover_blackout and bot_module.is_in_rollover_window(tc, server_offset, rollover_start_ist, rollover_end_ist))"""

assert old_telemetry_body in content, "old_telemetry_body not found"
content = content.replace(old_telemetry_body, new_telemetry_body)

# 3. Update compute_entry_telemetry return dict
old_ret = """        "atr": round(atr, 2),
        "max_atr": round(max_atr, 2),
        "volatility_climax": volatility_climax,
    }"""

new_ret = """        "atr": round(atr, 2),
        "max_atr": round(max_atr, 2),
        "volatility_climax": volatility_climax,
        "htf_filter": htf_filter,
        "htf_tf": htf_tf,
        "htf_dir": htf_dir,
        "htf_status": htf_status,
        "htf_fast": round(htf_fast, 2),
        "htf_slow": round(htf_slow, 2),
    }"""

assert old_ret in content, "old_ret not found"
content = content.replace(old_ret, new_ret)

# 4. Update BotManager.__init__ for live HTF state
old_mgr_init = """        self.live_ma: float = 0.0
        self.live_rsi: float = 50.0
        self.trade_excursions: Dict[str, Any] = load_trade_excursions()"""

new_mgr_init = """        self.live_ma: float = 0.0
        self.live_rsi: float = 50.0
        self.live_atr: float = 0.0
        self.live_htf_dir: int = 0
        self.live_htf_fast: float = 0.0
        self.live_htf_slow: float = 0.0
        self.trade_excursions: Dict[str, Any] = load_trade_excursions()"""

assert old_mgr_init in content, "old_mgr_init not found"
content = content.replace(old_mgr_init, new_mgr_init)

# 5. Update _poll_tick HTF calculation in BotManager
old_poll_sync = """            # Sync or calculate live MA and RSI
            if self.bot and getattr(self.bot, "ma", 0.0) > 0:
                self.live_ma = float(self.bot.ma)
                self.live_rsi = float(getattr(self.bot, "rsi", 50.0))
            else:"""

new_poll_sync = """            # Sync or calculate live MA, RSI and HTF trend
            if self.bot and getattr(self.bot, "ma", 0.0) > 0:
                self.live_ma = float(self.bot.ma)
                self.live_rsi = float(getattr(self.bot, "rsi", 50.0))
                self.live_atr = float(getattr(self.bot, "atr", 0.0))
                self.live_htf_dir = int(getattr(self.bot, "htf_dir", 0))
                self.live_htf_fast = float(getattr(self.bot, "htf_fast", 0.0))
                self.live_htf_slow = float(getattr(self.bot, "htf_slow", 0.0))
            else:"""

assert old_poll_sync in content, "old_poll_sync not found"
content = content.replace(old_poll_sync, new_poll_sync)

# 6. Update snapshot call to compute_entry_telemetry
old_snap_call = """            tc=tk_time,
            server_offset=server_offset,
            atr=atr_val,
            max_atr=getattr(self.cfg, "max_atr", 0.0),
        )"""

new_snap_call = """            tc=tk_time,
            server_offset=server_offset,
            atr=atr_val,
            max_atr=getattr(self.cfg, "max_atr", 0.0),
            htf_filter=getattr(self.cfg, "htf_filter", True),
            htf_tf=getattr(self.cfg, "htf_tf", "M5"),
            htf_dir=int(getattr(self.bot, "htf_dir", self.live_htf_dir)),
            htf_fast=float(getattr(self.bot, "htf_fast", self.live_htf_fast)),
            htf_slow=float(getattr(self.bot, "htf_slow", self.live_htf_slow)),
        )"""

assert old_snap_call in content, "old_snap_call not found"
content = content.replace(old_snap_call, new_snap_call)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Applied Lever 3 successfully to web_app.py")

