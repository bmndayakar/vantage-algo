import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from up_down_tracker_win_bot_xauusd import Cfg, FakeBroker, Bot

def mk(**kw):
    cfg = Cfg(enable_log=False, **kw); b = FakeBroker(cfg); return cfg, b, Bot(cfg, b)
def step(b, bot, price=None, dt_s=1):
    if price is not None: b.bid = price
    b.t += dt_s; bot.on_tick()

cfg, b, bot = mk(max_spread=2.00, spread_spike_mult=2.0, rollover_blackout=False, break_time=True)
for _ in range(12):
    b.spread = 0.25
    step(b, bot)

cfg.break_time = False
b.spread = 0.75
step(b, bot)
print("bot.status:", bot.status)
print("positions:", len(b.pos))
assert not b.pos and "SPREAD SPIKE" in bot.status
print("Spread spike test passed!")
