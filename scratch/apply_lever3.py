import os

file_path = "up_down_tracker_win_bot_xauusd.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update Cfg dataclass
old_cfg = """    atr_grid_scaling: bool = True        # Dynamically widen grid step during elevated ATR volatility
    atr_grid_mult: float = 1.5           # Multiplier of ATR for grid step distance"""

new_cfg = """    atr_grid_scaling: bool = True        # Dynamically widen grid step during elevated ATR volatility
    atr_grid_mult: float = 1.5           # Multiplier of ATR for grid step distance
    htf_filter: bool = True              # Lever 3: Higher-timeframe macro trend filter (M5/M15)
    htf_tf: str = "M5"                   # Timeframe for macro alignment ("M5" or "M15")
    htf_ema_fast: int = 9                # Fast EMA period on HTF
    htf_ema_slow: int = 21               # Slow EMA period on HTF
    htf_neutral_band: float = 0.50       # Dollar band within which HTF is considered neutral
    grid_bounce_req: float = 0.40        # Lever 3B: Min price bounce/rejection ($) before adding grid leg"""

assert old_cfg in content, "old_cfg not found"
content = content.replace(old_cfg, new_cfg)

# 2. Update Bot.__init__
old_init = """        s.spread_history = deque(maxlen=30)
        s.atr = 0.0
        s.events = []"""

new_init = """        s.spread_history = deque(maxlen=30)
        s.atr = 0.0
        s.htf_dir = 0
        s.htf_fast = 0.0
        s.htf_slow = 0.0
        s.grid_trough = 0.0
        s.grid_crest = 0.0
        s.events = []"""

assert old_init in content, "old_init not found"
content = content.replace(old_init, new_init)

# 3. Update close_all
old_close = """        s.pullback_crest = 0.0
        s.pullback_trough = 0.0"""

new_close = """        s.pullback_crest = 0.0
        s.pullback_trough = 0.0
        s.grid_trough = 0.0
        s.grid_crest = 0.0"""

assert old_close in content, "old_close not found"
content = content.replace(old_close, new_close)

# 4. Update on_tick query indicators
old_ind = """        if hasattr(s.br, "rsi"):
            rv = s.br.rsi(c.rsi_period)
            if rv is not None: s.rsi = rv
        eq, mg = s.br.equity_margin(); s.exposure = (mg / eq * 100.0) if eq > 0 else 0.0"""

new_ind = """        if hasattr(s.br, "rsi"):
            rv = s.br.rsi(c.rsi_period)
            if rv is not None: s.rsi = rv
        if hasattr(s.br, "htf_trend"):
            td, hf, hs = s.br.htf_trend(c.htf_tf, c.htf_ema_fast, c.htf_ema_slow, c.htf_neutral_band)
            s.htf_dir = td; s.htf_fast = hf; s.htf_slow = hs
        eq, mg = s.br.equity_margin(); s.exposure = (mg / eq * 100.0) if eq > 0 else 0.0"""

assert old_ind in content, "old_ind not found"
content = content.replace(old_ind, new_ind)

# 5. Update grid-add with Lever 3B Grid Momentum Guard
old_grid_add = """                ok, rc = s.br.order(1 if has_buy else -1)
                side = "BUY" if has_buy else "SELL"
                if ok:
                    s.last_order_error = ""
                    s.margin_reject_count = 0
                    s.log("ENTRY", side, "grid-add", bid, total, 0.0)"""

new_grid_add = """                # Lever 3B: Anti-Averaging Grid Momentum Guard (Wait for price bounce/rejection before adding leg)
                if c.grid_bounce_req > 0:
                    if has_buy:
                        if s.grid_trough == 0.0 or bid < s.grid_trough:
                            s.grid_trough = bid
                        bounce = bid - s.grid_trough
                        if bounce < c.grid_bounce_req:
                            s.status = f"GRID x{s.nopen} WAIT BOUNCE (+${bounce:.2f} < ${c.grid_bounce_req:.2f})"
                            return
                    elif has_sell:
                        if s.grid_crest == 0.0 or ask > s.grid_crest:
                            s.grid_crest = ask
                        rejection = s.grid_crest - ask
                        if rejection < c.grid_bounce_req:
                            s.status = f"GRID x{s.nopen} WAIT REJECTION (-${rejection:.2f} < ${c.grid_bounce_req:.2f})"
                            return

                ok, rc = s.br.order(1 if has_buy else -1)
                side = "BUY" if has_buy else "SELL"
                if ok:
                    s.last_order_error = ""
                    s.margin_reject_count = 0
                    s.grid_trough = 0.0
                    s.grid_crest = 0.0
                    s.log("ENTRY", side, "grid-add", bid, total, 0.0)"""

assert old_grid_add in content, "old_grid_add not found"
content = content.replace(old_grid_add, new_grid_add)

# 6. Update pullback mode to align with HTF trend
old_pb = """                if c.entry_mode == "pullback":
                    # PULLBACK REJECTION ENGINE: Buys dips, sells rallies off MA
                    macro_dir = 1 if bid >= s.ma else -1"""

new_pb = """                if c.entry_mode == "pullback":
                    # PULLBACK REJECTION ENGINE: Buys dips, sells rallies off MA
                    if c.htf_filter and s.htf_dir != 0:
                        macro_dir = s.htf_dir
                    else:
                        macro_dir = 1 if bid >= s.ma else -1"""

assert old_pb in content, "old_pb not found"
content = content.replace(old_pb, new_pb)

# 7. Update HTF filter check before order placement
old_filter_check = """                # 2. RSI Overbought/Oversold Guard: do not buy overbought climax or sell oversold floor
                if c.rsi_filter:
                    if d > 0 and s.rsi >= c.rsi_ob:
                        s.status = f"RSI OVERBOUGHT ({s.rsi:.1f} >= {c.rsi_ob:.0f})"
                        return
                    if d < 0 and s.rsi <= c.rsi_os:
                        s.status = f"RSI OVERSOLD ({s.rsi:.1f} <= {c.rsi_os:.0f})"
                        return"""

new_filter_check = """                # 2. RSI Overbought/Oversold Guard: do not buy overbought climax or sell oversold floor
                if c.rsi_filter:
                    if d > 0 and s.rsi >= c.rsi_ob:
                        s.status = f"RSI OVERBOUGHT ({s.rsi:.1f} >= {c.rsi_ob:.0f})"
                        return
                    if d < 0 and s.rsi <= c.rsi_os:
                        s.status = f"RSI OVERSOLD ({s.rsi:.1f} <= {c.rsi_os:.0f})"
                        return

                # 3. Lever 3A: HTF Macro Trend Filter (M5 / M15)
                if c.htf_filter and s.htf_dir != 0:
                    if d > 0 and s.htf_dir < 0:
                        s.status = f"WAIT HTF BULLISH ({c.htf_tf} Bearish)"
                        return
                    if d < 0 and s.htf_dir > 0:
                        s.status = f"WAIT HTF BEARISH ({c.htf_tf} Bullish)"
                        return"""

assert old_filter_check in content, "old_filter_check not found"
content = content.replace(old_filter_check, new_filter_check)

# 8. Update MT5Broker with htf_trend
old_mt5_rsi = """        rs = avg_g / avg_l
        return float(100.0 - (100.0 / (1.0 + rs)))"""

new_mt5_rsi = """        rs = avg_g / avg_l
        return float(100.0 - (100.0 / (1.0 + rs)))

    def htf_trend(s, tf_str="M5", fast=9, slow=21, neutral_band=0.50):
        tf = s.mt5.TIMEFRAME_M5 if str(tf_str).upper() == "M5" else s.mt5.TIMEFRAME_M15
        n_bars = max(slow + 25, 45)
        r = s.mt5.copy_rates_from_pos(s.c.symbol, tf, 0, n_bars)
        if r is None or len(r) < slow + 5:
            return 0, 0.0, 0.0
        closes = r["close"]
        def calc_ema(arr, span):
            alpha = 2.0 / (span + 1.0)
            ema = arr[0]
            for val in arr[1:]:
                ema = ema * (1.0 - alpha) + val * alpha
            return float(ema)
        f_ema = calc_ema(closes, fast)
        s_ema = calc_ema(closes, slow)
        diff = f_ema - s_ema
        if abs(diff) < neutral_band:
            return 0, round(f_ema, 2), round(s_ema, 2)
        return (1 if diff > 0 else -1), round(f_ema, 2), round(s_ema, 2)"""

assert old_mt5_rsi in content, "old_mt5_rsi not found"
content = content.replace(old_mt5_rsi, new_mt5_rsi)

# 9. Update FakeBroker with htf_trend
old_fake = """        s.bid = 4000.0; s.spread = 0.3; s.t = 1_000_000; s.ma_v = 3990.0; s.pos = []; s.n = 0; s.fail = False; s.atr_v = 0.5; s.sleeps = 0; s.dp = 0.0; s.ma_ago_v = 3980.0; s.rsi_v = 50.0; s.margin_fail = False
    def tick(s): return Tick(s.bid, s.bid + s.spread, s.t, s.t * 1000)
    def ma(s): return s.ma_v
    def ma_ago(s, k): return s.ma_ago_v
    def atr(s): return s.atr_v
    def rsi(s, period=14): return s.rsi_v"""

new_fake = """        s.bid = 4000.0; s.spread = 0.3; s.t = 1_000_000; s.ma_v = 3990.0; s.pos = []; s.n = 0; s.fail = False; s.atr_v = 0.5; s.sleeps = 0; s.dp = 0.0; s.ma_ago_v = 3980.0; s.rsi_v = 50.0; s.margin_fail = False
        s.htf_trend_v = 0; s.htf_fast_v = 4000.0; s.htf_slow_v = 4000.0
    def tick(s): return Tick(s.bid, s.bid + s.spread, s.t, s.t * 1000)
    def ma(s): return s.ma_v
    def ma_ago(s, k): return s.ma_ago_v
    def atr(s): return s.atr_v
    def rsi(s, period=14): return s.rsi_v
    def htf_trend(s, tf_str="M5", fast=9, slow=21, neutral_band=0.50): return s.htf_trend_v, s.htf_fast_v, s.htf_slow_v"""

assert old_fake in content, "old_fake not found"
content = content.replace(old_fake, new_fake)

# 10. Add self-tests for Lever 3
old_test_end = """    step(b, bot, 3979.0) # Gold drops $21.30 -> loss -$213.00 <= -$200.
    check("ATR grid scaling triggers leg 2 only after full -$200 move", len(b.pos) == 2)

    print(f"\\n{n_ok} checks passed")"""

new_test_end = """    step(b, bot, 3979.0) # Gold drops $21.30 -> loss -$213.00 <= -$200.
    check("ATR grid scaling triggers leg 2 only after full -$200 move", len(b.pos) == 2)

    # 21. Lever 3: Higher-Timeframe (HTF) Macro Alignment & Grid Momentum Gate
    # Test 3A: HTF Bearish blocks counter-trend BUY
    cfg, b, bot = mk(htf_filter=True, htf_tf="M5", rollover_blackout=False)
    b.htf_trend_v = -1; step(b, bot)
    check("HTF Bearish blocks counter-trend BUY", not b.pos and "WAIT HTF BULLISH" in bot.status)

    # Test 3B: HTF Bullish blocks counter-trend SELL
    cfg, b, bot = mk(htf_filter=True, htf_tf="M5", rollover_blackout=False)
    b.ma_v = 4010.0; b.htf_trend_v = 1; step(b, bot)
    check("HTF Bullish blocks counter-trend SELL", not b.pos and "WAIT HTF BEARISH" in bot.status)

    # Test 3C: HTF Neutral allows normal entry
    cfg, b, bot = mk(htf_filter=True, htf_tf="M5", rollover_blackout=False)
    b.htf_trend_v = 0; step(b, bot)
    check("HTF Neutral allows normal BUY entry", len(b.pos) == 1 and b.pos[0]["dir"] == 1)

    # Test 3D: HTF Bullish guides pullback mode to buy dips
    cfg, b, bot = mk(htf_filter=True, entry_mode="pullback", pullback_zone=10.0, pullback_rejection_dist=0.5, rollover_blackout=False)
    b.htf_trend_v = 1; b.ma_v = 3995.0
    step(b, bot, 4000.0) # dip trough @ 4000.0
    check("HTF Bullish in pullback mode tracks dip trough", not b.pos and "Wait BUY Bounce" in bot.status)
    step(b, bot, 4000.6) # bounce +$0.60 >= $0.50 -> BUY
    check("HTF Bullish triggers BUY bounce entry on dip", len(b.pos) == 1 and b.pos[0]["dir"] == 1)

    # Test 3E: Anti-Averaging Grid Momentum Guard (grid_bounce_req)
    cfg, b, bot = mk(grid_bounce_req=0.50, rollover_blackout=False, atr_grid_scaling=False, htf_filter=False)
    step(b, bot) # BUY @ 4000.3
    step(b, bot, 3989.0) # price drops -$11.30 (loss -$11.30 <= -$10.0 step)
    check("grid_bounce_req holds leg 2 during active fall", len(b.pos) == 1 and "WAIT BOUNCE" in bot.status)
    step(b, bot, 3989.6) # price bounces +$0.60 from trough 3989.0 -> triggers leg 2
    check("grid_bounce_req fires leg 2 after confirmed bounce", len(b.pos) == 2)

    print(f"\\n{n_ok} checks passed")"""

assert old_test_end in content, "old_test_end not found"
content = content.replace(old_test_end, new_test_end)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Applied Lever 3 successfully to up_down_tracker_win_bot_xauusd.py")

