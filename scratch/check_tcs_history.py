import sys
sys.path.insert(0, ".")
import MetaTrader5 as mt5
from up_down_tracker_win_bot_xauusd import MT5Broker, Cfg
from datetime import datetime

if not mt5.initialize():
    print("mt5 init failed")
    quit()

cfg = Cfg()
broker = MT5Broker(cfg)

# Let's inspect last bars
rates = mt5.copy_rates_from_pos('XAUUSD', mt5.TIMEFRAME_M1, 0, 350)
closes = [r[4] for r in rates]
highs = [r[2] for r in rates]
lows = [r[3] for r in rates]
times = [datetime.fromtimestamp(r[0]) for r in rates]

total_tested = 0
adx_vals = []

for end_idx in range(250, len(rates) + 1):
    sub_closes = closes[:end_idx]
    sub_highs = highs[:end_idx]
    sub_lows = lows[:end_idx]
    
    tr_list, dm_plus_list, dm_minus_list = [], [], []
    for k in range(1, len(sub_closes) - 1):
        h, l, prev_c = sub_highs[k], sub_lows[k], sub_closes[k-1]
        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        up = sub_highs[k] - sub_highs[k-1]
        down = sub_lows[k-1] - sub_lows[k]
        dm_p = up if (up > down and up > 0) else 0.0
        dm_m = down if (down > up and down > 0) else 0.0
        tr_list.append(tr)
        dm_plus_list.append(dm_p)
        dm_minus_list.append(dm_m)
        
    p = 14
    atr_smooth = sum(tr_list[:p])
    dmp_smooth = sum(dm_plus_list[:p])
    dmm_smooth = sum(dm_minus_list[:p])
    dx_list = []
    for k in range(p, len(tr_list)):
        atr_smooth = atr_smooth - (atr_smooth / p) + tr_list[k]
        dmp_smooth = dmp_smooth - (dmp_smooth / p) + dm_plus_list[k]
        dmm_smooth = dmm_smooth - (dmm_smooth / p) + dm_minus_list[k]
        di_p = 100.0 * (dmp_smooth / atr_smooth) if atr_smooth > 0 else 0.0
        di_m = 100.0 * (dmm_smooth / atr_smooth) if atr_smooth > 0 else 0.0
        diff = abs(di_p - di_m)
        sm = di_p + di_m
        dx = 100.0 * (diff / sm) if sm > 0 else 0.0
        dx_list.append(dx)
        
    adx = sum(dx_list[:p]) / p
    for dx in dx_list[p:]:
        adx = (adx * (p - 1) + dx) / p
        
    adx_vals.append(adx)
    total_tested += 1

print(f"Tested last {total_tested} bars ({times[250]} to {times[-1]}):")
print(f"ADX min: {min(adx_vals):.1f}, max: {max(adx_vals):.1f}, avg: {sum(adx_vals)/len(adx_vals):.1f}")
print(f"Bars with ADX >= 25: {sum(1 for a in adx_vals if a >= 25)} / {total_tested}")
print(f"Bars with ADX < 25: {sum(1 for a in adx_vals if a < 25)} / {total_tested}")

mt5.shutdown()
