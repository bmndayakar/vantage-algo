with open("up_down_tracker_win_bot_xauusd.py", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Add ui_mode and noob_level fields to Cfg dataclass
target_cfg = '    tcs_min_pillars: int = 3             # Min confirming pillars required (3 or 4)'
replace_cfg = '''    tcs_min_pillars: int = 3             # Min confirming pillars required (3 or 4)
    ui_mode: str = "noob"                # noob | pro : UI Mode selector
    noob_level: int = 3                  # 1: Ultra-Safe | 2: Conservative | 3: Balanced | 4: Active Scalper | 5: Momentum Velocity'''
assert target_cfg in text, "target_cfg not found"
text = text.replace(target_cfg, replace_cfg, 1)

# 2. Add NOOB_PRESETS dictionary definition and apply_noob_preset method right before Bot class
target_class = '# ============================== BOT (line-for-line port of OnTick) =============================='
noob_presets_code = '''NOOB_PRESETS = {
    1: {
        "name": "Level 1: Ultra-Safe",
        "desc": "Ultra-filtered trend entries, tightest capital protection",
        "min_pillars": 4, "adx_min": 25.0, "max_ma_dist": 12.0, "pullback_zone": 8.0,
        "grid_sl": 3.50, "trail_arm": 2.00, "trail_min_lock": 0.50, "hard_cap_hours": 0.5
    },
    2: {
        "name": "Level 2: Conservative",
        "desc": "High conviction trends, low chop tolerance",
        "min_pillars": 3, "adx_min": 22.0, "max_ma_dist": 15.0, "pullback_zone": 10.0,
        "grid_sl": 4.00, "trail_arm": 1.60, "trail_min_lock": 0.40, "hard_cap_hours": 0.75
    },
    3: {
        "name": "Level 3: Balanced Scalp",
        "desc": "Optimal sweet spot: high win rate with balanced risk",
        "min_pillars": 3, "adx_min": 18.0, "max_ma_dist": 20.0, "pullback_zone": 12.0,
        "grid_sl": 4.50, "trail_arm": 1.40, "trail_min_lock": 0.40, "hard_cap_hours": 1.0
    },
    4: {
        "name": "Level 4: Active Scalper",
        "desc": "High trade frequency, shallower pullbacks allowed",
        "min_pillars": 2, "adx_min": 15.0, "max_ma_dist": 28.0, "pullback_zone": 16.0,
        "grid_sl": 5.00, "trail_arm": 1.20, "trail_min_lock": 0.30, "hard_cap_hours": 1.0
    },
    5: {
        "name": "Level 5: Momentum Velocity",
        "desc": "Full trend participation, never locked out of big market runs",
        "min_pillars": 2, "adx_min": 12.0, "max_ma_dist": 35.0, "pullback_zone": 20.0,
        "grid_sl": 5.50, "trail_arm": 1.00, "trail_min_lock": 0.30, "hard_cap_hours": 1.0
    }
}

def apply_noob_preset_to_cfg(cfg: Cfg, level: int):
    """Applies fool-proof backtested parameters to Cfg when in Noob mode."""
    lvl = max(1, min(5, int(level)))
    cfg.noob_level = lvl
    p = NOOB_PRESETS[lvl]
    cfg.tcs_min_pillars = p["min_pillars"]
    cfg.tcs_adx_min = p["adx_min"]
    cfg.max_ma_dist = p["max_ma_dist"]
    cfg.pullback_zone = p["pullback_zone"]
    cfg.grid_sl = p["grid_sl"]
    cfg.trail_arm = p["trail_arm"]
    cfg.trail_min_lock = p["trail_min_lock"]
    cfg.hard_cap_hours = p["hard_cap_hours"]
    cfg.trend_system = "hybrid"
    cfg.entry_mode = "pullback"


'''
assert target_class in text, "target_class not found"
text = text.replace(target_class, noob_presets_code + target_class, 1)

with open("up_down_tracker_win_bot_xauusd.py", "w", encoding="utf-8") as f:
    f.write(text)

print("up_down_tracker_win_bot_xauusd.py patched successfully!")
