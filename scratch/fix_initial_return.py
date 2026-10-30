with open("web_app.py", "r", encoding="utf-8") as f:
    text = f.read()

target = '''            "rsi": round(rsi, 1),
            "rsi_status": rsi_status,
            "rsi_ob": round(rsi_ob, 1),
            "rsi_os": round(rsi_os, 1),
        }'''

replacement = '''            "rsi": round(rsi, 1),
            "rsi_status": rsi_status,
            "rsi_ob": round(rsi_ob, 1),
            "rsi_os": round(rsi_os, 1),
            "trend_system": trend_system,
            "tcs_dir": 0,
            "tcs_status": "CALCULATING...",
            "tcs_bull_score": 0,
            "tcs_bear_score": 0,
            "tcs_ema_fast": 0.0,
            "tcs_ema_slow": 0.0,
            "tcs_adx": 0.0,
            "tcs_adx_rising": False,
            "tcs_di_plus": 0.0,
            "tcs_di_minus": 0.0,
            "tcs_structure": "CALCULATING...",
            "tcs_macd": 0.0,
            "tcs_macd_sig": 0.0,
            "tcs_macd_hist": 0.0,
            "tcs_macd_rising": False,
            "tcs_p1_bull": False,
            "tcs_p1_bear": False,
            "tcs_p2_bull": False,
            "tcs_p2_bear": False,
            "tcs_p3_bull": False,
            "tcs_p3_bear": False,
            "tcs_p4_bull": False,
            "tcs_p4_bear": False,
            "tcs_bar_closed": True,
        }'''

if target in text:
    text = text.replace(target, replacement)
    with open("web_app.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("Updated initial return dict successfully!")
else:
    print("Target not found!")

