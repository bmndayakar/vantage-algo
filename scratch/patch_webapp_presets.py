with open("web_app.py", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Update update_config in BotManager to support noob mode preset application
target_upd = '''                for k, v in new_cfg.items():
                    if k == "symbol":
                        continue
                    if hasattr(self.cfg, k):
                        target_type = type(getattr(self.cfg, k))
                        if target_type is bool:
                            val = bool(v)
                        elif target_type is int:
                            val = int(v)
                        elif target_type is float:
                            val = float(v)
                        else:
                            val = str(v)
                        setattr(self.cfg, k, val)'''

replace_upd = '''                # If ui_mode is noob (or being updated to noob), apply noob preset
                req_ui_mode = str(new_cfg.get("ui_mode", getattr(self.cfg, "ui_mode", "noob"))).lower()
                req_noob_lvl = int(new_cfg.get("noob_level", getattr(self.cfg, "noob_level", 3)))

                if req_ui_mode == "noob":
                    bot_module.apply_noob_preset_to_cfg(self.cfg, req_noob_lvl)
                    self.cfg.ui_mode = "noob"

                for k, v in new_cfg.items():
                    if k == "symbol":
                        continue
                    # When in noob mode, do not let manual fields override noob presets except lots, side, etc.
                    if req_ui_mode == "noob" and k in ("tcs_min_pillars", "tcs_adx_min", "max_ma_dist", "pullback_zone", "grid_sl", "trail_arm", "trail_min_lock", "hard_cap_hours"):
                        continue
                    if hasattr(self.cfg, k):
                        target_type = type(getattr(self.cfg, k))
                        if target_type is bool:
                            val = bool(v)
                        elif target_type is int:
                            val = int(v)
                        elif target_type is float:
                            val = float(v)
                        else:
                            val = str(v)
                        setattr(self.cfg, k, val)'''

assert target_upd in text, "target_upd not found"
text = text.replace(target_upd, replace_upd, 1)

with open("web_app.py", "w", encoding="utf-8") as f:
    f.write(text)

print("web_app.py patched with noob preset handling successfully!")

