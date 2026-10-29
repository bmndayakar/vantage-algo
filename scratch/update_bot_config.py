import json

with open("bot_config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

cfg.update({
    "max_spread": 0.50,
    "rollover_blackout": True,
    "rollover_start_ist": "02:15",
    "rollover_end_ist": "03:30",
    "spread_spike_mult": 2.0,
    "max_atr": 0.0,
    "atr_grid_scaling": True,
    "atr_grid_mult": 1.5,
})

with open("bot_config.json", "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2)

print("Updated bot_config.json with Lever 2 defaults!")

