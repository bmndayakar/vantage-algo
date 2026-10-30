import sys
sys.path.insert(0, ".")
import MetaTrader5 as mt5
from up_down_tracker_win_bot_xauusd import MT5Broker, Cfg
from datetime import datetime
import numpy as np

if not mt5.initialize():
    print("mt5 init failed")
    quit()

cfg = Cfg()
cfg.symbol = "XAUUSD"
broker = MT5Broker(cfg)

# Fetch last 450 M1 bars
rates = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M1, 0, 450)
closes = np.array([r[4] for r in rates], dtype=float)
highs = np.array([r[2] for r in rates], dtype=float)
lows = np.array([r[3] for r in rates], dtype=float)
times = [datetime.fromtimestamp(r[0]) for r in rates]

tcs_chop_count = 0
tcs_confirmed_count = 0
overextended_count = 0
ready_count = 0

reasons = {
    "tcs_chop": 0,
    "overextended": 0,
    "wait_pullback": 0,
    "signal_ready": 0
}

# Inspect from bar 250 to 450 (last ~200 minutes, ~3.3 hours)
for i in range(250, len(rates)):
    bar_t = times[i].strftime("%H:%M")
    c_price = closes[i]
    ma = np.mean(closes[i-250:i])
    dist = abs(c_price - ma)
    
    # Run TCS logic on historical slice
    # Helper EMA
    def _ema(arr, span):
        alpha = 2.0 / (span + 1.0)
        res = np.empty_like(arr)
        res[0] = arr[0]
        for idx in range(1, len(arr)):
            res[idx] = res[idx - 1] * (1.0 - alpha) + arr[idx] * alpha
        return res

    sub_c = closes[:i]
    sub_h = highs[:i]
    sub_l = lows[:i]
    n = len(sub_c)
    last_c = sub_c[-1]
    
    # P1
    ef = _ema(sub_c, 50)[-1]
    es = _ema(sub_c, 200)[-1]
    p1_bull = (ef > es) and (last_c > ef) and (last_c > es)
    p1_bear = (ef < es) and (last_c < ef) and (last_c < es)
    
    # P2 (ADX)
    tr = np.zeros(n)
    dm_p = np.zeros(n)
    dm_m = np.zeros(n)
    for k in range(1, n):
        hd = sub_h[k] - sub_h[k-1]
        ld = sub_l[k-1] - sub_l[k]
        tr[k] = max(sub_h[k] - sub_l[k], abs(sub_h[k] - sub_c[k-1]), abs(sub_l[k] - sub_c[k-1]))
        if hd > ld and hd > 0: dm_p[k] = hd
        if ld > hd and ld > 0: dm_m[k] = ld
    p_adx = 14
    tr_sm, dp_sm, dm_sm = np.zeros(n), np.zeros(n), np.zeros(n)
    if n > p_adx:
        tr_sm[p_adx] = np.sum(tr[1:p_adx+1])
        dp_sm[p_adx] = np.sum(dm_p[1:p_adx+1])
        dm_sm[p_adx] = np.sum(dm_m[1:p_adx+1])
        for k in range(p_adx + 1, n):
            tr_sm[k] = tr_sm[k-1] - (tr_sm[k-1]/p_adx) + tr[k]
            dp_sm[k] = dp_sm[k-1] - (dp_sm[k-1]/p_adx) + dm_p[k]
            dm_sm[k] = dm_sm[k-1] - (dm_sm[k-1]/p_adx) + dm_m[k]
    di_p, di_m, dx = np.zeros(n), np.zeros(n), np.zeros(n)
    for k in range(p_adx, n):
        if tr_sm[k] > 0:
            di_p[k] = 100.0 * (dp_sm[k] / tr_sm[k])
            di_m[k] = 100.0 * (dm_sm[k] / tr_sm[k])
            denom = di_p[k] + di_m[k]
            if denom > 0: dx[k] = 100.0 * abs(di_p[k] - di_m[k]) / denom
    adx_series = np.zeros(n)
    s_idx = p_adx * 2 - 1
    if s_idx < n:
        adx_series[s_idx] = np.mean(dx[p_adx:s_idx+1])
        for k in range(s_idx + 1, n):
            adx_series[k] = (adx_series[k-1] * (p_adx - 1) + dx[k]) / p_adx
    adx_val = float(adx_series[-1])
    p2_bull = (adx_val >= 25.0) and (di_p[-1] > di_m[-1])
    p2_bear = (adx_val >= 25.0) and (di_m[-1] > di_p[-1])
    
    # P3 Structure
    pivots = []
    st_bar = max(1, n - 20)
    for k in range(st_bar, n - 1):
        if sub_h[k] > sub_h[k-1] and sub_h[k] > sub_h[k+1]: pivots.append(('H', sub_h[k]))
        elif sub_l[k] < sub_l[k-1] and sub_l[k] < sub_l[k+1]: pivots.append(('L', sub_l[k]))
    sh = [p[1] for p in pivots if p[0] == 'H']
    sl = [p[1] for p in pivots if p[0] == 'L']
    p3_bull, p3_bear = False, False
    if len(sh) >= 2 and len(sl) >= 2:
        if sh[-1] > sh[-2] and sl[-1] > sl[-2]: p3_bull = True
        elif sh[-1] < sh[-2] and sl[-1] < sl[-2]: p3_bear = True
    else:
        if sub_c[-1] > sub_c[-5] and sub_l[-1] > sub_l[-5]: p3_bull = True
        elif sub_c[-1] < sub_c[-5] and sub_h[-1] < sub_h[-5]: p3_bear = True
        
    # P4 MACD
    f_m = _ema(sub_c, 12)
    s_m = _ema(sub_c, 26)
    m_l = f_m - s_m
    sig_l = np.zeros_like(m_l)
    if len(m_l) >= 35: sig_l[25:] = _ema(m_l[25:], 9)
    hist_l = m_l - sig_l
    h_val = float(hist_l[-1])
    h_prev = float(hist_l[-2])
    p4_bull = (h_val > 0) and (h_val > h_prev)
    p4_bear = (h_val < 0) and (h_val < h_prev)
    
    b_score = int(sum([p1_bull, p2_bull, p3_bull, p4_bull]))
    s_score = int(sum([p1_bear, p2_bear, p3_bear, p4_bear]))
    
    tcs_dir = 0
    if b_score >= 3 and b_score > s_score: tcs_dir = 1
    elif s_score >= 3 and s_score > b_score: tcs_dir = -1
    
    if tcs_dir == 0:
        reasons["tcs_chop"] += 1
    elif dist > 12.0:
        reasons["overextended"] += 1
    elif dist > 10.0: # pullback zone is 10.0
        reasons["wait_pullback"] += 1
    else:
        reasons["signal_ready"] += 1

total = len(rates) - 250
print(f"Total bars analyzed: {total} ({times[250].strftime('%H:%M')} to {times[-1].strftime('%H:%M')})")
for k, v in reasons.items():
    print(f"  {k}: {v} bars ({v/total*100:.1f}%)")

mt5.shutdown()
