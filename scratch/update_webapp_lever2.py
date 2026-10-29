with open("web_app.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update compute_entry_telemetry signature and logic
target_telem_sig = '''def compute_entry_telemetry(
    bid: float,
    ma: float,
    max_dist: float = 0.0,
    side: str = "both",
    entry_mode: str = "classic",
    pullback_zone: float = 3.0,
    pullback_rejection_dist: float = 0.6,
    rsi: float = 50.0,
    rsi_filter: bool = True,
    rsi_ob: float = 70.0,
    rsi_os: float = 30.0,
) -> Dict[str, Any]:'''

new_telem_sig = '''def compute_entry_telemetry(
    bid: float,
    ma: float,
    max_dist: float = 0.0,
    side: str = "both",
    entry_mode: str = "classic",
    pullback_zone: float = 3.0,
    pullback_rejection_dist: float = 0.6,
    rsi: float = 50.0,
    rsi_filter: bool = True,
    rsi_ob: float = 70.0,
    rsi_os: float = 30.0,
    spread: float = 0.0,
    max_spread: float = 0.50,
    rollover_blackout: bool = True,
    rollover_start_ist: str = "02:15",
    rollover_end_ist: str = "03:30",
    tc: int = 0,
    server_offset: float = 2.0,
    atr: float = 0.0,
    max_atr: float = 0.0,
) -> Dict[str, Any]:'''

code = code.replace(target_telem_sig, new_telem_sig)

# 2. Add Lever 2 override logic before returning from compute_entry_telemetry
target_ret_block = '''        target_entry_desc = f"BUY: {buy_desc}  |  SELL: {sell_desc}"

    return {'''

new_ret_block = '''        target_entry_desc = f"BUY: {buy_desc}  |  SELL: {sell_desc}"

    # Lever 2: Dynamic Gates & Rollover Blackout Overrides
    rollover_active = bool(rollover_blackout and bot_module.is_in_rollover_window(tc, server_offset, rollover_start_ist, rollover_end_ist))
    spread_wide = bool(max_spread > 0 and spread > max_spread)
    volatility_climax = bool(max_atr > 0 and atr > max_atr)

    if rollover_active:
        action_side = "SLEEP (ROLLOVER BLACKOUT)"
        target_entry_desc = f"Rollover Blackout Active ({rollover_start_ist}-{rollover_end_ist} IST) - High Spread Protection"
        buy_ready = False
        sell_ready = False
        in_entry_zone = False
    elif spread_wide:
        action_side = f"BLOCKED (SPREAD WIDE ${spread:.2f})"
        target_entry_desc = f"Spread ${spread:.2f} exceeds Max Limit ${max_spread:.2f}"
        buy_ready = False
        sell_ready = False
        in_entry_zone = False
    elif volatility_climax:
        action_side = f"BLOCKED (VOLATILITY CLIMAX ATR ${atr:.2f})"
        target_entry_desc = f"ATR ${atr:.2f} exceeds Volatility Ceiling ${max_atr:.2f}"
        buy_ready = False
        sell_ready = False
        in_entry_zone = False

    return {'''

code = code.replace(target_ret_block, new_ret_block)

# 3. Add new fields to the returned telemetry dictionary
target_ret_dict = '''        "rsi": round(rsi, 1),
        "rsi_status": rsi_status,
        "rsi_ob": round(rsi_ob, 1),
        "rsi_os": round(rsi_os, 1),
    }'''

new_ret_dict = '''        "rsi": round(rsi, 1),
        "rsi_status": rsi_status,
        "rsi_ob": round(rsi_ob, 1),
        "rsi_os": round(rsi_os, 1),
        "rollover_active": rollover_active,
        "rollover_window": f"{rollover_start_ist} - {rollover_end_ist} IST",
        "spread": round(spread, 2),
        "max_spread": round(max_spread, 2),
        "spread_wide": spread_wide,
        "atr": round(atr, 2),
        "max_atr": round(max_atr, 2),
        "volatility_climax": volatility_climax,
    }'''

code = code.replace(target_ret_dict, new_ret_dict)

# 4. In snapshot(), pass all Lever 2 fields to compute_entry_telemetry
target_snapshot_call = '''        telemetry = compute_entry_telemetry(
            bid=bid_val,
            ma=ma_val,
            max_dist=self.cfg.max_ma_dist,
            side=self.cfg.side,
            entry_mode=getattr(self.cfg, "entry_mode", "classic"),
            pullback_zone=getattr(self.cfg, "pullback_zone", 3.0),
            pullback_rejection_dist=getattr(self.cfg, "pullback_rejection_dist", 0.6),
            rsi=rsi_val,
            rsi_filter=getattr(self.cfg, "rsi_filter", True),
            rsi_ob=getattr(self.cfg, "rsi_ob", 70.0),
            rsi_os=getattr(self.cfg, "rsi_os", 30.0),
        )'''

new_snapshot_call = '''        server_offset = self.get_server_offset()
        ask_val = float(self.last_tick.get("ask", 0.0)) if self.last_tick else 0.0
        cur_spread = round(ask_val - bid_val, 2) if (ask_val > 0 and bid_val > 0) else 0.0
        atr_val = float(getattr(self.bot, "atr", 0.0)) if self.bot else float(getattr(self, "live_atr", 0.0))
        tk_time = int(self.last_tick.get("time", 0)) if self.last_tick else int(time.time())

        telemetry = compute_entry_telemetry(
            bid=bid_val,
            ma=ma_val,
            max_dist=self.cfg.max_ma_dist,
            side=self.cfg.side,
            entry_mode=getattr(self.cfg, "entry_mode", "classic"),
            pullback_zone=getattr(self.cfg, "pullback_zone", 3.0),
            pullback_rejection_dist=getattr(self.cfg, "pullback_rejection_dist", 0.6),
            rsi=rsi_val,
            rsi_filter=getattr(self.cfg, "rsi_filter", True),
            rsi_ob=getattr(self.cfg, "rsi_ob", 70.0),
            rsi_os=getattr(self.cfg, "rsi_os", 30.0),
            spread=cur_spread,
            max_spread=getattr(self.cfg, "max_spread", 0.50),
            rollover_blackout=getattr(self.cfg, "rollover_blackout", True),
            rollover_start_ist=getattr(self.cfg, "rollover_start_ist", "02:15"),
            rollover_end_ist=getattr(self.cfg, "rollover_end_ist", "03:30"),
            tc=tk_time,
            server_offset=server_offset,
            atr=atr_val,
            max_atr=getattr(self.cfg, "max_atr", 0.0),
        )'''

code = code.replace(target_snapshot_call, new_snapshot_call)

with open("web_app.py", "w", encoding="utf-8") as f:
    f.write(code)

print("web_app.py updated with Lever 2 telemetry!")

