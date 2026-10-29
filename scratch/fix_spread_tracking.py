with open("up_down_tracker_win_bot_xauusd.py", "r", encoding="utf-8") as f:
    code = f.read()

target_top = '''        if bid <= 0 or ask <= 0:
            s.status = "MARKET CLOSED / NO QUOTE"
            return'''

replacement_top = '''        if bid <= 0 or ask <= 0:
            s.status = "MARKET CLOSED / NO QUOTE"
            return
        cur_spread = round(ask - bid, 2)
        s.spread_history.append(cur_spread)'''

code = code.replace(target_top, replacement_top)

# Remove the redundant s.spread_history.append from line 440
target_dup = '''                cur_spread = round(ask - bid, 2)
                s.spread_history.append(cur_spread)

                # Spread Expansion Gates (Lever 2)'''

replacement_dup = '''                # Spread Expansion Gates (Lever 2)'''

code = code.replace(target_dup, replacement_dup)

with open("up_down_tracker_win_bot_xauusd.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Updated spread tracking to top of on_tick()")

