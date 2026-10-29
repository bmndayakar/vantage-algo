import os, sys
sys.path.insert(0, os.path.abspath("."))
import json
from up_down_tracker_win_bot_xauusd import Cfg
import dataclasses

with open("bot_config.json", "r", encoding="utf-8") as f:
    cfg_data = json.load(f)

# Update with Lever 2 & Lever 3 defaults
cfg = Cfg()
for f in dataclasses.fields(Cfg):
    if f.name not in cfg_data:
        cfg_data[f.name] = getattr(cfg, f.name)

# Ensure proper defaults for Gold
cfg_data["max_spread"] = 0.50
cfg_data["rollover_blackout"] = True
cfg_data["rollover_start_ist"] = "02:15"
cfg_data["rollover_end_ist"] = "03:30"
cfg_data["spread_spike_mult"] = 2.0
cfg_data["atr_grid_scaling"] = True
cfg_data["atr_grid_mult"] = 1.5
cfg_data["htf_filter"] = True
cfg_data["htf_tf"] = "M5"
cfg_data["htf_ema_fast"] = 9
cfg_data["htf_ema_slow"] = 21
cfg_data["htf_neutral_band"] = 0.50
cfg_data["grid_bounce_req"] = 0.40

with open("bot_config.json", "w", encoding="utf-8") as f:
    json.dump(cfg_data, f, indent=2)

print("Updated bot_config.json successfully:")
