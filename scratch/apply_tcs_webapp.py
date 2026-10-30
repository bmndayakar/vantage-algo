import sys

with open("web_app.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update BotManager.__init__ to include live_tcs_state and last_tcs_calc
init_target = '''        self.live_htf_dir: int = 0
        self.live_htf_fast: float = 0.0
        self.live_htf_slow: float = 0.0'''

init_replacement = '''        self.live_htf_dir: int = 0
        self.live_htf_fast: float = 0.0
        self.live_htf_slow: float = 0.0
        self.live_tcs_state: Dict[str, Any] = {}
        self.last_tcs_calc_time: float = 0.0'''

if init_target not in code:
    print("Could not find init_target in web_app.py")
    sys.exit(1)

code = code.replace(init_target, init_replacement)

# 2. In get_mt5_account_and_market, calculate live_tcs_state when bot is not running
htf_sync_target = '''            # Sync or calculate live MA, RSI and HTF trend
            if self.bot and getattr(self.bot, "ma", 0.0) > 0:
                self.live_ma = float(self.bot.ma)
                self.live_rsi = float(getattr(self.bot, "rsi", 50.0))
                self.live_atr = float(getattr(self.bot, "atr", 0.0))
                self.live_htf_dir = int(getattr(self.bot, "htf_dir", 0))
                self.live_htf_fast = float(getattr(self.bot, "htf_fast", 0.0))
                self.live_htf_slow = float(getattr(self.bot, "htf_slow", 0.0))'''

htf_sync_replacement = '''            # Sync or calculate live MA, RSI, HTF trend, and TCS state
            if self.bot and getattr(self.bot, "ma", 0.0) > 0:
                self.live_ma = float(self.bot.ma)
                self.live_rsi = float(getattr(self.bot, "rsi", 50.0))
                self.live_atr = float(getattr(self.bot, "atr", 0.0))
                self.live_htf_dir = int(getattr(self.bot, "htf_dir", 0))
                self.live_htf_fast = float(getattr(self.bot, "htf_fast", 0.0))
                self.live_htf_slow = float(getattr(self.bot, "htf_slow", 0.0))
                self.live_tcs_state = getattr(self.bot, "tcs_state", {}) or {}
            else:
                if time.time() - self.last_tcs_calc_time > 1.0:
                    self.last_tcs_calc_time = time.time()
                    try:
                        br = MT5Broker(self.cfg)
                        self.live_tcs_state = br.tcs_eval(
                            tf_str=getattr(self.cfg, "tcs_tf", "M1"),
                            ema_fast=getattr(self.cfg, "tcs_ema_fast", 50),
                            ema_slow=getattr(self.cfg, "tcs_ema_slow", 200),
                            adx_period=getattr(self.cfg, "tcs_adx_period", 14),
                            adx_min=getattr(self.cfg, "tcs_adx_min", 25.0),
                            require_rising=getattr(self.cfg, "tcs_adx_require_rising", False),
                            lookback=getattr(self.cfg, "tcs_structure_bars", 20),
                            min_pillars=getattr(self.cfg, "tcs_min_pillars", 3),
                        )
                    except Exception:
                        pass'''

if htf_sync_target not in code:
    print("Could not find htf_sync_target in web_app.py")
    sys.exit(1)

code = code.replace(htf_sync_target, htf_sync_replacement)

# 3. Update compute_entry_telemetry to include TCS parameters and logic
param_target = '''    htf_fast: float = 0.0,
    htf_slow: float = 0.0,
) -> Dict[str, Any]:'''

param_replacement = '''    htf_fast: float = 0.0,
    htf_slow: float = 0.0,
    trend_system: str = "hybrid",
    tcs_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:'''

if param_target not in code:
    print("Could not find param_target in web_app.py")
    sys.exit(1)

code = code.replace(param_target, param_replacement)

# 4. In compute_entry_telemetry, evaluate TCS directional override
override_target = '''    # Lever 3: Higher-Timeframe (HTF) Macro Alignment
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
                target_entry_desc = f"Rally to MA: {sell_desc} ({htf_tf} Bearish Aligned)"'''

override_replacement = '''    # Directional Overrides: TCS (4-Pillar System) if active, else Lever 3 HTF
    tcs = tcs_state or {}
    tcs_dir = int(tcs.get("direction", 0))
    tcs_status = str(tcs.get("status", "NEUTRAL"))
    b_score = int(tcs.get("bull_score", 0))
    s_score = int(tcs.get("bear_score", 0))

    htf_status = "BULLISH" if htf_dir == 1 else ("BEARISH" if htf_dir == -1 else "NEUTRAL")

    if trend_system in ("tcs", "hybrid") and tcs:
        if tcs_dir == 1:
            sell_ready = False
            sell_desc = f"Blocked by TCS Bullish Confirmation ({b_score}/4 Pillars)"
            action_side = f"BUY ONLY (TCS BULLISH {b_score}/4)"
            target_entry_price = buy_price
            target_entry_desc = f"TCS Bullish ({b_score}/4): {buy_desc}"
        elif tcs_dir == -1:
            buy_ready = False
            buy_desc = f"Blocked by TCS Bearish Confirmation ({s_score}/4 Pillars)"
            action_side = f"SELL ONLY (TCS BEARISH {s_score}/4)"
            target_entry_price = sell_price
            target_entry_desc = f"TCS Bearish ({s_score}/4): {sell_desc}"
        else:
            buy_ready = False
            sell_ready = False
            in_entry_zone = False
            action_side = f"NO TRADE (TCS CHOP FILTERED {b_score}B/{s_score}S)"
            target_entry_desc = f"⚠️ Chop Filter Active ({b_score}B/{s_score}S < Min Pillars) - Orders Blocked"
            buy_desc = f"Blocked: TCS Choppy ({b_score}B/{s_score}S)"
            sell_desc = f"Blocked: TCS Choppy ({b_score}B/{s_score}S)"
    elif htf_filter and htf_dir != 0:
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
                target_entry_desc = f"Rally to MA: {sell_desc} ({htf_tf} Bearish Aligned)"'''

if override_target not in code:
    print("Could not find override_target in web_app.py")
    sys.exit(1)

code = code.replace(override_target, override_replacement)

# 5. In compute_entry_telemetry return dict, include TCS fields
telemetry_ret_target = '''        "htf_fast": round(htf_fast, 2),
        "htf_slow": round(htf_slow, 2),
    }'''

telemetry_ret_replacement = '''        "htf_fast": round(htf_fast, 2),
        "htf_slow": round(htf_slow, 2),
        "trend_system": trend_system,
        "tcs_dir": tcs_dir,
        "tcs_status": tcs_status,
        "tcs_bull_score": b_score,
        "tcs_bear_score": s_score,
        "tcs_ema_fast": tcs.get("ema_fast", 0.0),
        "tcs_ema_slow": tcs.get("ema_slow", 0.0),
        "tcs_adx": tcs.get("adx", 0.0),
        "tcs_adx_rising": tcs.get("adx_rising", False),
        "tcs_di_plus": tcs.get("di_plus", 0.0),
        "tcs_di_minus": tcs.get("di_minus", 0.0),
        "tcs_structure": tcs.get("structure", "CHOPPY"),
        "tcs_macd": tcs.get("macd", 0.0),
        "tcs_macd_sig": tcs.get("macd_sig", 0.0),
        "tcs_macd_hist": tcs.get("macd_hist", 0.0),
        "tcs_macd_rising": tcs.get("macd_rising", False),
        "tcs_p1_bull": tcs.get("p1_bull", False),
        "tcs_p1_bear": tcs.get("p1_bear", False),
        "tcs_p2_bull": tcs.get("p2_bull", False),
        "tcs_p2_bear": tcs.get("p2_bear", False),
        "tcs_p3_bull": tcs.get("p3_bull", False),
        "tcs_p3_bear": tcs.get("p3_bear", False),
        "tcs_p4_bull": tcs.get("p4_bull", False),
        "tcs_p4_bear": tcs.get("p4_bear", False),
        "tcs_bar_closed": tcs.get("bar_closed", True),
    }'''

if telemetry_ret_target not in code:
    print("Could not find telemetry_ret_target in web_app.py")
    sys.exit(1)

code = code.replace(telemetry_ret_target, telemetry_ret_replacement)

# 6. In snapshot(), pass trend_system and tcs_state to compute_entry_telemetry
snapshot_call_target = '''            htf_dir=int(getattr(self.bot, "htf_dir", self.live_htf_dir)),
            htf_fast=float(getattr(self.bot, "htf_fast", self.live_htf_fast)),
            htf_slow=float(getattr(self.bot, "htf_slow", self.live_htf_slow)),
        )'''

snapshot_call_replacement = '''            htf_dir=int(getattr(self.bot, "htf_dir", self.live_htf_dir)),
            htf_fast=float(getattr(self.bot, "htf_fast", self.live_htf_fast)),
            htf_slow=float(getattr(self.bot, "htf_slow", self.live_htf_slow)),
            trend_system=getattr(self.cfg, "trend_system", "hybrid"),
            tcs_state=getattr(self.bot, "tcs_state", self.live_tcs_state) or {},
        )'''

if snapshot_call_target not in code:
    print("Could not find snapshot_call_target in web_app.py")
    sys.exit(1)

code = code.replace(snapshot_call_target, snapshot_call_replacement)

with open("web_app.py", "w", encoding="utf-8") as f:
    f.write(code)

print("web_app.py successfully updated with TCS telemetry!")
