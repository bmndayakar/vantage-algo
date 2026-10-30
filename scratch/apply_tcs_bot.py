import sys

with open("up_down_tracker_win_bot_xauusd.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Add TCS fields to Cfg
target_cfg = '    grid_bounce_req: float = 0.0        # Lever 3B: Min price bounce/rejection ($) before adding grid leg\n'
new_cfg = '''    grid_bounce_req: float = 0.0        # Lever 3B: Min price bounce/rejection ($) before adding grid leg
    trend_system: str = "legacy"         # legacy | tcs | hybrid : 4-Pillar Trend Confirmation System switch
    tcs_tf: str = "M1"                   # TCS evaluation timeframe ("M1" or "M5")
    tcs_ema_fast: int = 50               # Pillar 1 fast EMA
    tcs_ema_slow: int = 200              # Pillar 1 slow EMA
    tcs_adx_period: int = 14             # Pillar 2 ADX period
    tcs_adx_min: float = 25.0            # Pillar 2 min ADX threshold
    tcs_adx_require_rising: bool = False # Pillar 2 require ADX slope > 0
    tcs_structure_bars: int = 20         # Pillar 3 swing lookback bars
    tcs_min_pillars: int = 3             # Min confirming pillars required (3 or 4)
'''

if target_cfg not in code:
    print("Could not find target_cfg")
    sys.exit(1)

code = code.replace(target_cfg, new_cfg)

# 2. Add tcs_state and tcs_dir to Bot.__init__
target_bot_init = '        s.htf_dir = 0\n        s.htf_fast = 0.0\n        s.htf_slow = 0.0\n'
new_bot_init = '''        s.htf_dir = 0
        s.htf_fast = 0.0
        s.htf_slow = 0.0
        s.tcs_dir = 0
        s.tcs_state = {}
'''
if target_bot_init not in code:
    print("Could not find target_bot_init")
    sys.exit(1)

code = code.replace(target_bot_init, new_bot_init)

# 3. Add tcs_eval call in on_tick
target_on_tick = '        if hasattr(s.br, "htf_trend"):\n            td, hf, hs = s.br.htf_trend(c.htf_tf, c.htf_ema_fast, c.htf_ema_slow, c.htf_neutral_band)\n            s.htf_dir = td; s.htf_fast = hf; s.htf_slow = hs\n'
new_on_tick = '''        if hasattr(s.br, "htf_trend"):\n            td, hf, hs = s.br.htf_trend(c.htf_tf, c.htf_ema_fast, c.htf_ema_slow, c.htf_neutral_band)\n            s.htf_dir = td; s.htf_fast = hf; s.htf_slow = hs
        if hasattr(s.br, "tcs_eval"):
            s.tcs_state = s.br.tcs_eval(
                tf_str=c.tcs_tf,
                ema_fast=c.tcs_ema_fast,
                ema_slow=c.tcs_ema_slow,
                adx_period=c.tcs_adx_period,
                adx_min=c.tcs_adx_min,
                require_rising=c.tcs_adx_require_rising,
                lookback=c.tcs_structure_bars,
                min_pillars=c.tcs_min_pillars,
            )
            s.tcs_dir = s.tcs_state.get("direction", 0)
'''
if target_on_tick not in code:
    print("Could not find target_on_tick")
    sys.exit(1)

code = code.replace(target_on_tick, new_on_tick)

# 4. Integrate TCS into entry logic in Bot.on_tick
target_pullback_macro = '''                    if c.htf_filter and s.htf_dir != 0:
                        macro_dir = s.htf_dir
                    else:
                        macro_dir = 1 if bid >= s.ma else -1'''

new_pullback_macro = '''                    if c.trend_system in ("tcs", "hybrid"):
                        if s.tcs_dir == 0:
                            b_sc = s.tcs_state.get("bull_score", 0)
                            s_sc = s.tcs_state.get("bear_score", 0)
                            s.status = f"TCS CHOP / NO TREND ({b_sc}B/{s_sc}S < {c.tcs_min_pillars})"
                            return
                        macro_dir = s.tcs_dir
                    elif c.htf_filter and s.htf_dir != 0:
                        macro_dir = s.htf_dir
                    else:
                        macro_dir = 1 if bid >= s.ma else -1'''

if target_pullback_macro not in code:
    print("Could not find target_pullback_macro")
    sys.exit(1)

code = code.replace(target_pullback_macro, new_pullback_macro)

# 5. Handle strict TCS mode when entry_mode != "pullback"
target_classic_entry = '''                else:
                    # CLASSIC (Direct MA cross/level)
                    s.status = "SIGNAL READY"
                    if bid > s.ma: d = 1
                    elif bid < s.ma: d = -1
                    else: return'''

new_classic_entry = '''                else:
                    # CLASSIC / TCS (Direct trend signal)
                    if c.trend_system in ("tcs", "hybrid"):
                        if s.tcs_dir == 0:
                            b_sc = s.tcs_state.get("bull_score", 0)
                            s_sc = s.tcs_state.get("bear_score", 0)
                            s.status = f"TCS CHOP / NO TREND ({b_sc}B/{s_sc}S < {c.tcs_min_pillars})"
                            return
                        d = s.tcs_dir
                        s.status = f"TCS CONFIRMED ({'BUY' if d > 0 else 'SELL'} {s.tcs_state.get('bull_score' if d > 0 else 'bear_score', 0)}/4)"
                    else:
                        s.status = "SIGNAL READY"
                        if bid > s.ma: d = 1
                        elif bid < s.ma: d = -1
                        else: return'''

if target_classic_entry not in code:
    print("Could not find target_classic_entry")
    sys.exit(1)

code = code.replace(target_classic_entry, new_classic_entry)

# 6. Add tcs_eval calculation functions to MT5Broker and helper math
tcs_calc_methods = '''
    def tcs_eval(s, tf_str="M1", ema_fast=50, ema_slow=200, adx_period=14, adx_min=25.0, require_rising=False, lookback=20, min_pillars=3):
        """
        4-Pillar Trend Confirmation System (TCS):
        Pillar 1: 50 EMA vs 200 EMA + Close price vs both (Direction)
        Pillar 2: ADX(14) >= 25, +DI/-DI confirmation, optionally rising (Strength)
        Pillar 3: Swing Pivot Structure HH/HL vs LH/LL (Structure)
        Pillar 4: MACD(12,26,9) Histogram sign and slope (Momentum)
        Strictly evaluates closed candle (shift 1).
        """
        tf = s.mt5.TIMEFRAME_M1 if str(tf_str).upper() == "M1" else s.mt5.TIMEFRAME_M5
        n_needed = max(ema_slow + 50, 260)
        # Shift 1: closed candle discipline
        r = s.mt5.copy_rates_from_pos(s.c.symbol, tf, 1, n_needed)
        if r is None or len(r) < ema_slow + 10:
            return {"direction": 0, "bull_score": 0, "bear_score": 0, "status": "INSUFFICIENT_DATA"}

        closes = s.np.asarray(r["close"], dtype=float)
        highs = s.np.asarray(r["high"], dtype=float)
        lows = s.np.asarray(r["low"], dtype=float)
        last_c = float(closes[-1])
        n = len(closes)

        # Helper EMA
        def _ema(arr, span):
            alpha = 2.0 / (span + 1.0)
            res = s.np.empty_like(arr)
            res[0] = arr[0]
            for idx in range(1, len(arr)):
                res[idx] = res[idx - 1] * (1.0 - alpha) + arr[idx] * alpha
            return res

        # Pillar 1: Trend Direction
        ema_f_series = _ema(closes, ema_fast)
        ema_s_series = _ema(closes, ema_slow)
        ef = float(ema_f_series[-1])
        es = float(ema_s_series[-1])

        p1_bull = (ef > es) and (last_c > ef) and (last_c > es)
        p1_bear = (ef < es) and (last_c < ef) and (last_c < es)

        # Pillar 2: Trend Strength (ADX & DI)
        tr = s.np.zeros(n)
        dm_p = s.np.zeros(n)
        dm_m = s.np.zeros(n)
        for i in range(1, n):
            hd = highs[i] - highs[i - 1]
            ld = lows[i - 1] - lows[i]
            tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
            if hd > ld and hd > 0: dm_p[i] = hd
            if ld > hd and ld > 0: dm_m[i] = ld

        tr_sm = s.np.zeros(n)
        dp_sm = s.np.zeros(n)
        dm_sm = s.np.zeros(n)
        p_adx = adx_period
        if n > p_adx:
            tr_sm[p_adx] = s.np.sum(tr[1:p_adx + 1])
            dp_sm[p_adx] = s.np.sum(dm_p[1:p_adx + 1])
            dm_sm[p_adx] = s.np.sum(dm_m[1:p_adx + 1])
            for i in range(p_adx + 1, n):
                tr_sm[i] = tr_sm[i - 1] - (tr_sm[i - 1] / p_adx) + tr[i]
                dp_sm[i] = dp_sm[i - 1] - (dp_sm[i - 1] / p_adx) + dm_p[i]
                dm_sm[i] = dm_sm[i - 1] - (dm_sm[i - 1] / p_adx) + dm_m[i]

        di_p = s.np.zeros(n)
        di_m = s.np.zeros(n)
        dx = s.np.zeros(n)
        for i in range(p_adx, n):
            if tr_sm[i] > 0:
                di_p[i] = 100.0 * (dp_sm[i] / tr_sm[i])
                di_m[i] = 100.0 * (dm_sm[i] / tr_sm[i])
                denom = di_p[i] + di_m[i]
                if denom > 0:
                    dx[i] = 100.0 * abs(di_p[i] - di_m[i]) / denom

        adx_series = s.np.zeros(n)
        s_idx = p_adx * 2 - 1
        if s_idx < n:
            adx_series[s_idx] = s.np.mean(dx[p_adx:s_idx + 1])
            for i in range(s_idx + 1, n):
                adx_series[i] = (adx_series[i - 1] * (p_adx - 1) + dx[i]) / p_adx

        adx_val = float(adx_series[-1])
        adx_prev = float(adx_series[-2]) if n >= 2 else adx_val
        adx_rising = adx_val > adx_prev
        adx_ok = (adx_val >= adx_min) and (adx_rising if require_rising else True)
        di_plus_val = float(di_p[-1])
        di_minus_val = float(di_m[-1])

        p2_bull = adx_ok and (di_plus_val > di_minus_val)
        p2_bear = adx_ok and (di_minus_val > di_plus_val)

        # Pillar 3: Price Structure (Higher Highs/Lows vs Lower Highs/Lows)
        pivots = []
        st_bar = max(1, n - lookback)
        for i in range(st_bar, n - 1):
            if highs[i] > highs[i - 1] and highs[i] > highs[i + 1]:
                pivots.append(("H", highs[i]))
            elif lows[i] < lows[i - 1] and lows[i] < lows[i + 1]:
                pivots.append(("L", lows[i]))

        sh = [p[1] for p in pivots if p[0] == "H"]
        sl = [p[1] for p in pivots if p[0] == "L"]
        p3_bull = False
        p3_bear = False
        struct_tag = "CHOPPY"
        if len(sh) >= 2 and len(sl) >= 2:
            if sh[-1] > sh[-2] and sl[-1] > sl[-2]:
                p3_bull = True
                struct_tag = "HH_HL_BULLISH"
            elif sh[-1] < sh[-2] and sl[-1] < sl[-2]:
                p3_bear = True
                struct_tag = "LH_LL_BEARISH"
        else:
            if closes[-1] > closes[-5] and lows[-1] > lows[-5]:
                p3_bull = True
                struct_tag = "MOM_UP"
            elif closes[-1] < closes[-5] and highs[-1] < highs[-5]:
                p3_bear = True
                struct_tag = "MOM_DN"

        # Pillar 4: MACD Histogram (12, 26, 9)
        f_macd = _ema(closes, 12)
        s_macd = _ema(closes, 26)
        macd_l = f_macd - s_macd
        sig_l = s.np.zeros_like(macd_l)
        if len(macd_l) >= 35:
            sig_sub = _ema(macd_l[25:], 9)
            sig_l[25:] = sig_sub
        hist_l = macd_l - sig_l
        hist_val = float(hist_l[-1])
        hist_prev = float(hist_l[-2]) if n >= 2 else hist_val
        hist_rising = hist_val > hist_prev

        p4_bull = (hist_val > 0) and hist_rising
        p4_bear = (hist_val < 0) and (not hist_rising)

        bull_score = int(sum([p1_bull, p2_bull, p3_bull, p4_bull]))
        bear_score = int(sum([p1_bear, p2_bear, p3_bear, p4_bear]))

        direction = 0
        if bull_score >= min_pillars and bull_score > bear_score:
            direction = 1
        elif bear_score >= min_pillars and bear_score > bull_score:
            direction = -1

        status_str = "NEUTRAL"
        if bull_score == 4: status_str = "CONFIRMED BULLISH (4/4)"
        elif bear_score == 4: status_str = "CONFIRMED BEARISH (4/4)"
        elif direction == 1: status_str = f"PROBABLE BULLISH ({bull_score}/4)"
        elif direction == -1: status_str = f"PROBABLE BEARISH ({bear_score}/4)"
        else: status_str = f"CHOPPY / FILTERED ({bull_score}B/{bear_score}S)"

        return {
            "direction": direction,
            "bull_score": bull_score,
            "bear_score": bear_score,
            "status": status_str,
            "ema_fast": round(ef, 2),
            "ema_slow": round(es, 2),
            "p1_bull": bool(p1_bull),
            "p1_bear": bool(p1_bear),
            "adx": round(adx_val, 1),
            "adx_rising": bool(adx_rising),
            "di_plus": round(di_plus_val, 1),
            "di_minus": round(di_minus_val, 1),
            "p2_bull": bool(p2_bull),
            "p2_bear": bool(p2_bear),
            "structure": struct_tag,
            "p3_bull": bool(p3_bull),
            "p3_bear": bool(p3_bear),
            "macd": round(float(macd_l[-1]), 2),
            "macd_sig": round(float(sig_l[-1]), 2),
            "macd_hist": round(hist_val, 2),
            "macd_rising": bool(hist_rising),
            "p4_bull": bool(p4_bull),
            "p4_bear": bool(p4_bear),
            "last_close": round(last_c, 2),
            "bar_closed": True,
        }
'''

target_broker_end = '    def equity_margin(s):\n        a = s.mt5.account_info()\n        if a is None: return 0.0, 0.0\n        return a.equity, a.margin\n'
if target_broker_end not in code:
    print("Could not find target_broker_end")
    sys.exit(1)

code = code.replace(target_broker_end, target_broker_end + tcs_calc_methods)

# 7. Add tcs_eval to FakeBroker for testing
target_fake_broker = '    def htf_trend(s, tf_str="M5", fast=9, slow=21, neutral_band=0.50): return s.htf_trend_v, s.htf_fast_v, s.htf_slow_v'

new_fake_broker = '''    def htf_trend(s, tf_str="M5", fast=9, slow=21, neutral_band=0.50): return s.htf_trend_v, s.htf_fast_v, s.htf_slow_v
    def tcs_eval(s, **kwargs):
        if hasattr(s, "tcs_v") and s.tcs_v is not None:
            return s.tcs_v
        return {"direction": 0, "bull_score": 0, "bear_score": 0, "status": "NEUTRAL", "ema_fast": 4000.0, "ema_slow": 4000.0, "adx": 20.0, "di_plus": 20.0, "di_minus": 20.0, "structure": "CHOPPY", "macd_hist": 0.0, "bar_closed": True}'''

if target_fake_broker not in code:
    print("Could not find target_fake_broker")
    sys.exit(1)

code = code.replace(target_fake_broker, new_fake_broker)

with open("up_down_tracker_win_bot_xauusd.py", "w", encoding="utf-8") as f:
    f.write(code)

print("up_down_tracker_win_bot_xauusd.py updated with TCS engine!")
