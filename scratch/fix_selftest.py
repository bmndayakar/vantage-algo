with open("up_down_tracker_win_bot_xauusd.py", "r", encoding="utf-8") as f:
    code = f.read()

target = '''    # Spread Expansion Gate: relative spike multiplier blocks sudden widening
    cfg, b, bot = mk(max_spread=2.00, spread_spike_mult=2.0, rollover_blackout=False)
    for _ in range(12): b.spread = 0.25; step(b, bot)
    b.spread = 0.75; step(b, bot) # 0.75 > 0.25 * 2.0 (0.50)
    check("spread spike multiplier blocks entry on 3x spread expansion", not b.pos and "SPREAD SPIKE" in bot.status)'''

replacement = '''    # Spread Expansion Gate: relative spike multiplier blocks sudden widening
    cfg, b, bot = mk(max_spread=2.00, spread_spike_mult=2.0, rollover_blackout=False, break_time=True)
    for _ in range(12): b.spread = 0.25; step(b, bot)
    cfg.break_time = False
    b.spread = 0.75; step(b, bot) # 0.75 > 0.25 * 2.0 (0.50)
    check("spread spike multiplier blocks entry on 3x spread expansion", not b.pos and "SPREAD SPIKE" in bot.status)'''

c_norm = code.replace("\r\n", "\n")
t_norm = target.replace("\r\n", "\n")
r_norm = replacement.replace("\r\n", "\n")

if t_norm in c_norm:
    c_norm = c_norm.replace(t_norm, r_norm)
    with open("up_down_tracker_win_bot_xauusd.py", "w", encoding="utf-8", newline="") as f:
        f.write(c_norm.replace("\n", "\r\n"))
    print("Fixed selftest successfully!")
else:
    print("Target not found")

