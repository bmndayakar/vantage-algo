import datetime as dt
import collections

# Prototype Lever 2 logic
def is_in_rollover_window(tc: int, server_offset: float = 2.0, start_ist: str = "02:15", end_ist: str = "03:30") -> bool:
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

# 1. Test rollover at 02:40 AM IST (21:10 UTC, 23:10 broker EET):
dt_srv = dt.datetime(2026, 10, 28, 23, 10, 0)
tc_rollover = int(dt_srv.replace(tzinfo=dt.timezone.utc).timestamp())
assert is_in_rollover_window(tc_rollover, 2.0, "02:15", "03:30") == True, "Failed 02:40 IST check"

# 2. Test outside rollover at 14:30 IST (09:00 UTC, 11:00 broker EET):
dt_srv_day = dt.datetime(2026, 10, 28, 11, 0, 0)
tc_day = int(dt_srv_day.replace(tzinfo=dt.timezone.utc).timestamp())
assert is_in_rollover_window(tc_day, 2.0, "02:15", "03:30") == False, "Failed 14:30 IST check"

# 3. Test spread expansion:
spread_history = collections.deque(maxlen=30)
for _ in range(20): spread_history.append(0.28) # normal 28 cent spread
baseline = sum(spread_history) / len(spread_history)

spike_spread = 1.25 # spike to $1.25
mult = 2.0
is_spike = (spike_spread > baseline * mult and spike_spread > 0.40)
assert is_spike == True, "Failed spread spike check"

# 4. Test ATR grid scaling:
eff_grid_step_loss = 100.0 # $100 for 0.10 lot
perUnit = 10.0 # $10 per $1 move for 0.10 lot
atr_mult = 1.5

# Case A: Calm ATR = $1.50 -> atr_step = 1.5 * 1.5 * 10 = $22.50 -> uses max($100, $22.50) = $100
step_calm = max(eff_grid_step_loss, 1.50 * atr_mult * perUnit)
assert step_calm == 100.0, f"Expected 100.0, got {step_calm}"

# Case B: High Volatility ATR = $8.00 -> atr_step = 8.0 * 1.5 * 10 = $120.00 -> uses max($100, $120) = $120
step_wild = max(eff_grid_step_loss, 8.00 * atr_mult * perUnit)
assert step_wild == 120.0, f"Expected 120.0, got {step_wild}"

print("All Lever 2 prototype assertions PASSED!")

