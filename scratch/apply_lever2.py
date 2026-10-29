with open("up_down_tracker_win_bot_xauusd.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Add is_in_rollover_window helper function before Cfg
target_before_cfg = '@dataclass\nclass Cfg:'
rollover_fn = '''def is_in_rollover_window(tc: int, server_offset: float = 2.0, start_ist: str = "02:15", end_ist: str = "03:30") -> bool:
    """
    Checks if current time falls within the high-spread broker rollover blackout window (IST).
    Converts broker tick epoch timestamp to Indian Standard Time (IST, UTC+5:30).
    """
    if tc > 0:
        dt_srv = dt.datetime.utcfromtimestamp(tc)
        dt_utc = dt_srv - dt.timedelta(hours=server_offset)
        dt_ist = dt_utc + dt.timedelta(hours=5, minutes=30)
    else:
        dt_ist = dt.datetime.now()

    try:
        s_parts = start_ist.strip().split(":")
        e_parts = end_ist.strip().split(":")
        s_min = int(s_parts[0]) * 60 + int(s_parts[1])
        e_min = int(e_parts[0]) * 60 + int(e_parts[1])
        c_min = dt_ist.hour * 60 + dt_ist.minute
        if s_min <= e_min:
            return s_min <= c_min < e_min
        else:
            return c_min >= s_min or c_min < e_min
    except Exception:
        return False


@dataclass
class Cfg:'''

code = code.replace(target_before_cfg, rollover_fn)

# 2. Add Lever 2 fields to Cfg
target_cfg_spread = '    max_spread: float = 0.0'
lever2_cfg = '''    max_spread: float = 0.50             # Absolute max spread ($) allowed for entry (0 = disabled)
    rollover_blackout: bool = True       # True: block new initial entries during broker rollover window
    rollover_start_ist: str = "02:15"    # Rollover start time in IST (HH:MM)
    rollover_end_ist: str = "03:30"      # Rollover end time in IST (HH:MM)
    spread_spike_mult: float = 2.0       # Spread spike multiplier vs rolling baseline (0 = disabled)
    max_atr: float = 0.0                 # Max ATR ($) allowed for new entry (0 = disabled)
    atr_grid_scaling: bool = True        # Dynamically widen grid step during elevated ATR volatility
    atr_grid_mult: float = 1.5           # Multiplier of ATR for grid step distance'''

code = code.replace(target_cfg_spread, lever2_cfg)

# 3. Add s.spread_history and s.atr in Bot.__init__
target_bot_init = '        s.pullback_crest = 0.0; s.pullback_trough = 0.0'
new_bot_init = '''        s.pullback_crest = 0.0; s.pullback_trough = 0.0
        s.spread_history = collections.deque(maxlen=30)
        s.atr = 0.0'''

code = code.replace(target_bot_init, new_bot_init)

# 4. In Bot.on_tick, add Rollover Blackout check when nopen == 0
target_break_time = '            if c.break_time: s.status = "☕ BREAK TIME (Tracking, no entries)"; s.flip = 0; return'
new_break_time = '''            if c.break_time: s.status = "☕ BREAK TIME (Tracking, no entries)"; s.flip = 0; return
            if c.rollover_blackout and is_in_rollover_window(tc, c.server_offset, c.rollover_start_ist, c.rollover_end_ist):
                s.status = f"🌙 ROLLOVER BLACKOUT ({c.rollover_start_ist}-{c.rollover_end_ist} IST)"
                s.flip = 0
                return'''

code = code.replace(target_break_time, new_break_time)

# 5. In Bot.on_tick, add Spread Gates and ATR Climax Gate
target_spread_check = '''                if c.max_spread > 0 and (ask - bid) > c.max_spread:
                    s.status = f"SPREAD WIDE {ask - bid:.2f}"; return'''

new_spread_check = '''                cur_spread = round(ask - bid, 2)
                s.spread_history.append(cur_spread)

                # Spread Expansion Gates (Lever 2)
                if c.max_spread > 0 and cur_spread > c.max_spread:
                    s.status = f"SPREAD WIDE ${cur_spread:.2f} > ${c.max_spread:.2f}"; return

                if c.spread_spike_mult > 0 and len(s.spread_history) >= 10:
                    baseline = sum(s.spread_history) / len(s.spread_history)
                    if cur_spread > baseline * c.spread_spike_mult and cur_spread > 0.40:
                        s.status = f"SPREAD SPIKE ${cur_spread:.2f} > ${baseline * c.spread_spike_mult:.2f}"; return

                # Volatility Climax Gate (Lever 2)
                atr_val = s.br.atr()
                if atr_val is not None and atr_val > 0:
                    s.atr = float(atr_val)
                    if c.max_atr > 0 and s.atr > c.max_atr:
                        s.status = f"VOLATILITY CLIMAX (ATR ${s.atr:.2f} > ${c.max_atr:.2f})"; return'''

code = code.replace(target_spread_check, new_spread_check)

# 6. In Bot.on_tick, add Dynamic ATR Grid step calculation
target_grid_step = '            if s.nopen < c.grid_max_legs and total <= -(s.nopen * c.eff_grid_step_loss):'
new_grid_step = '''            step = c.eff_grid_step_loss
            if c.atr_grid_scaling:
                tv, ts = s.br.tick_value_size()
                atr = s.br.atr()
                if ts > 0 and atr is not None and atr > 0:
                    s.atr = float(atr)
                    perUnit = (tv / ts) * c.lots
                    atr_step = s.atr * c.atr_grid_mult * perUnit
                    step = max(step, atr_step)

            if s.nopen < c.grid_max_legs and total <= -(s.nopen * step):'''

code = code.replace(target_grid_step, new_grid_step)

# 7. Add selftest checks for Lever 2
target_selftest_end = '    print(f"\\n{n_ok} checks passed")'

new_selftest_checks = '''    # Lever 2: Dynamic ATR Volatility, Spread Expansion Gates & Rollover Blackout
    # Rollover Blackout: blocks entry during rollover window (e.g. 02:40 IST = epoch 1793229000 at server_offset=2)
    cfg, b, bot = mk(rollover_blackout=True, rollover_start_ist="02:15", rollover_end_ist="03:30", server_offset=2.0)
    b.t = 1793229000; step(b, bot)
    check("rollover blackout blocks entry during window", not b.pos and "ROLLOVER BLACKOUT" in bot.status)

    # Rollover Blackout: allows entry outside window (e.g. 14:30 IST)
    cfg, b, bot = mk(rollover_blackout=True, rollover_start_ist="02:15", rollover_end_ist="03:30", server_offset=2.0)
    b.t = 1000000; step(b, bot)
    check("rollover blackout allows entry outside window", len(b.pos) == 1)

    # Spread Expansion Gate: absolute cap blocks entry
    cfg, b, bot = mk(max_spread=0.50, rollover_blackout=False)
    b.spread = 1.20; step(b, bot)
    check("max_spread 0.50 blocks entry on 1.20 spread", not b.pos and "SPREAD WIDE" in bot.status)

    # Spread Expansion Gate: relative spike multiplier blocks sudden widening
    cfg, b, bot = mk(max_spread=2.00, spread_spike_mult=2.0, rollover_blackout=False)
    for _ in range(12): b.spread = 0.25; step(b, bot)
    b.spread = 0.75; step(b, bot) # 0.75 > 0.25 * 2.0 (0.50)
    check("spread spike multiplier blocks entry on 3x spread expansion", not b.pos and "SPREAD SPIKE" in bot.status)

    # Volatility Climax Gate: max_atr blocks entry during economic release hurricane
    cfg, b, bot = mk(max_atr=5.00, rollover_blackout=False)
    b.atr_v = 8.50; step(b, bot)
    check("max_atr 5.0 blocks entry when ATR spikes to 8.5", not b.pos and "VOLATILITY CLIMAX" in bot.status)

    # Dynamic ATR Grid Scaling: widens grid spacing during elevated volatility
    cfg, b, bot = mk(atr_grid_scaling=True, atr_grid_mult=2.0, grid_step_loss=10.0, lots=0.10, rollover_blackout=False)
    step(b, bot) # 1 BUY @ 4000.3 (0.10 lot = $10/dollar move)
    b.atr_v = 10.0 # ATR $10.0 -> atr_step = 10 * 2.0 * $10 = $200 (widened from baseline $100)
    step(b, bot, 3988.0) # Gold drops $12.30 -> loss -$123.00 <= -$100 baseline. But scaled step is -$200!
    check("ATR grid scaling prevents premature leg 2 when step scaled to -$200", len(b.pos) == 1)
    step(b, bot, 3979.0) # Gold drops $21.30 -> loss -$213.00 <= -$200.
    check("ATR grid scaling triggers leg 2 only after full -$200 move", len(b.pos) == 2)

    print(f"\\n{n_ok} checks passed")'''

code = code.replace(target_selftest_end, new_selftest_checks)

with open("up_down_tracker_win_bot_xauusd.py", "w", encoding="utf-8") as f:
    f.write(code)

print("up_down_tracker_win_bot_xauusd.py successfully updated with Lever 2!")

