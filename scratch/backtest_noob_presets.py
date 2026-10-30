import MetaTrader5 as mt5
import numpy as np
import datetime

def calculate_ema(arr, span):
    alpha = 2.0 / (span + 1.0)
    ema = np.empty_like(arr, dtype=float)
    ema[0] = arr[0]
    for i in range(1, len(arr)):
        ema[i] = ema[i - 1] * (1.0 - alpha) + arr[i] * alpha
    return ema

def calculate_adx_series(highs, lows, closes, period=14):
    n = len(closes)
    tr = np.zeros(n)
    dm_plus = np.zeros(n)
    dm_minus = np.zeros(n)
    
    for i in range(1, n):
        h_diff = highs[i] - highs[i - 1]
        l_diff = lows[i - 1] - lows[i]
        tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        if h_diff > l_diff and h_diff > 0:
            dm_plus[i] = h_diff
        if l_diff > h_diff and l_diff > 0:
            dm_minus[i] = l_diff

    tr_smooth = np.zeros(n)
    dm_plus_smooth = np.zeros(n)
    dm_minus_smooth = np.zeros(n)
    
    if n > period:
        tr_smooth[period] = np.sum(tr[1:period + 1])
        dm_plus_smooth[period] = np.sum(dm_plus[1:period + 1])
        dm_minus_smooth[period] = np.sum(dm_minus[1:period + 1])
        
        for i in range(period + 1, n):
            tr_smooth[i] = tr_smooth[i - 1] - (tr_smooth[i - 1] / period) + tr[i]
            dm_plus_smooth[i] = dm_plus_smooth[i - 1] - (dm_plus_smooth[i - 1] / period) + dm_plus[i]
            dm_minus_smooth[i] = dm_minus_smooth[i - 1] - (dm_minus_smooth[i - 1] / period) + dm_minus[i]

    di_plus = np.zeros(n)
    di_minus = np.zeros(n)
    dx = np.zeros(n)
    
    for i in range(period, n):
        if tr_smooth[i] > 0:
            di_plus[i] = 100.0 * (dm_plus_smooth[i] / tr_smooth[i])
            di_minus[i] = 100.0 * (dm_minus_smooth[i] / tr_smooth[i])
            denom = di_plus[i] + di_minus[i]
            if denom > 0:
                dx[i] = 100.0 * abs(di_plus[i] - di_minus[i]) / denom
                
    adx = np.zeros(n)
    start_idx = period * 2 - 1
    if start_idx < n:
        adx[start_idx] = np.mean(dx[period:start_idx + 1])
        for i in range(start_idx + 1, n):
            adx[i] = (adx[i - 1] * (period - 1) + dx[i]) / period

    return adx, di_plus, di_minus

def calculate_macd_series(closes, fast=12, slow=26, signal=9):
    fast_ema = calculate_ema(closes, fast)
    slow_ema = calculate_ema(closes, slow)
    macd_line = fast_ema - slow_ema
    sig_line = np.zeros_like(macd_line)
    if len(macd_line) >= slow + signal:
        sig_sub = calculate_ema(macd_line[slow - 1:], signal)
        sig_line[slow - 1:] = sig_sub
    hist = macd_line - sig_line
    return macd_line, sig_line, hist

# Noob Presets Configuration
NOOB_PRESETS = {
    1: {
        "name": "Level 1: Ultra-Safe",
        "min_pillars": 4,
        "adx_min": 25.0,
        "max_ma_dist": 12.0,
        "pullback_zone": 8.0,
        "sl": 3.5,
        "tp": 2.5,
        "trail_arm": 2.0,
    },
    2: {
        "name": "Level 2: Conservative",
        "min_pillars": 3,
        "adx_min": 22.0,
        "max_ma_dist": 15.0,
        "pullback_zone": 10.0,
        "sl": 4.0,
        "tp": 2.2,
        "trail_arm": 1.8,
    },
    3: {
        "name": "Level 3: Balanced",
        "min_pillars": 3,
        "adx_min": 18.0,
        "max_ma_dist": 20.0,
        "pullback_zone": 12.0,
        "sl": 4.5,
        "tp": 2.0,
        "trail_arm": 1.5,
    },
    4: {
        "name": "Level 4: Active Scalper",
        "min_pillars": 2,
        "adx_min": 15.0,
        "max_ma_dist": 28.0,
        "pullback_zone": 15.0,
        "sl": 5.0,
        "tp": 1.8,
        "trail_arm": 1.2,
    },
    5: {
        "name": "Level 5: Aggressive Momentum",
        "min_pillars": 2,
        "adx_min": 12.0,
        "max_ma_dist": 40.0,
        "pullback_zone": 20.0,
        "sl": 6.0,
        "tp": 1.5,
        "trail_arm": 1.0,
    }
}

def backtest_all_presets():
    if not mt5.initialize():
        print("MT5 initialization failed!")
        return

    # Fetch 4000 M1 bars of Gold (XAUUSD)
    rates = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M1, 1, 4000)
    mt5.shutdown()

    if rates is None or len(rates) < 1000:
        print("Insufficient rates fetched.")
        return

    closes = rates["close"]
    highs = rates["high"]
    lows = rates["low"]
    times = rates["time"]
    n = len(closes)
    t_start = datetime.datetime.fromtimestamp(times[0])
    t_end = datetime.datetime.fromtimestamp(times[-1])
    print(f"=== TESTING ALL 5 NOOB PRESETS ACROSS {n} REAL M1 BARS OF XAUUSD ===")
    print(f"Period: {t_start} to {t_end} (Price range: {min(lows):.2f} - {max(highs):.2f})")
    print(f"Includes the massive -$96 gold crash and prior rallies.\n")

    ema_50 = calculate_ema(closes, 50)
    ema_200 = calculate_ema(closes, 200)
    adx, di_plus, di_minus = calculate_adx_series(highs, lows, closes, 14)
    macd, sig, hist = calculate_macd_series(closes, 12, 26, 9)

    sma_250 = np.zeros(n)
    for i in range(250, n):
        sma_250[i] = np.mean(closes[i - 250 + 1:i + 1])

    results = {}

    for lvl in range(1, 6):
        p = NOOB_PRESETS[lvl]
        min_pillars = p["min_pillars"]
        adx_min = p["adx_min"]
        max_dist = p["max_ma_dist"]
        pullback_z = p["pullback_zone"]
        sl = p["sl"]
        tp = p["tp"]
        
        trades = []
        pos = None
        
        for i in range(300, n - 1):
            c_now = closes[i]
            c_prev = closes[i-1]
            ma_val = sma_250[i]
            dist = abs(c_now - ma_val)
            
            # Check exit if in position
            if pos is not None:
                pnl_pts = (c_now - pos["entry_p"]) if pos["dir"] == 1 else (pos["entry_p"] - c_now)
                dur = i - pos["entry_bar"]
                
                # Check stop loss hit
                if pnl_pts <= -sl:
                    trades.append({"pnl": -sl, "dur": dur, "reason": "SL"})
                    pos = None
                    continue
                # Check take profit hit
                elif pnl_pts >= tp:
                    trades.append({"pnl": tp, "dur": dur, "reason": "TP"})
                    pos = None
                    continue
                elif dur >= 45: # soft time cap
                    trades.append({"pnl": pnl_pts, "dur": dur, "reason": "TIME"})
                    pos = None
                    continue
            
            # Check entry if flat
            if pos is None:
                if dist > max_dist:
                    continue
                    
                # Evaluate Pillars
                # P1: EMA 50 vs 200 + Close
                p1_bull = (ema_50[i] > ema_200[i]) and (c_prev > ema_50[i]) and (c_prev > ema_200[i])
                p1_bear = (ema_50[i] < ema_200[i]) and (c_prev < ema_50[i]) and (c_prev < ema_200[i])
                
                # P2: ADX
                p2_bull = (adx[i] >= adx_min) and (di_plus[i] > di_minus[i])
                p2_bear = (adx[i] >= adx_min) and (di_minus[i] > di_plus[i])
                
                # P3: Structure (5-bar momentum proxy)
                p3_bull = closes[i-1] > closes[i-6] and lows[i-1] > lows[i-6]
                p3_bear = closes[i-1] < closes[i-6] and highs[i-1] < highs[i-6]
                
                # P4: MACD
                p4_bull = (hist[i] > 0) and (hist[i] > hist[i-1])
                p4_bear = (hist[i] < 0) and (hist[i] < hist[i-1])
                
                b_score = sum([p1_bull, p2_bull, p3_bull, p4_bull])
                s_score = sum([p1_bear, p2_bear, p3_bear, p4_bear])
                
                # Entry direction
                d = 0
                if b_score >= min_pillars and b_score > s_score:
                    d = 1
                elif s_score >= min_pillars and s_score > b_score:
                    d = -1
                    
                if d != 0:
                    pos = {"dir": d, "entry_p": c_now, "entry_bar": i}
                    
        wins = [t for t in trades if t["pnl"] > 0]
        losses = [t for t in trades if t["pnl"] < 0]
        tot = len(trades)
        win_rate = (len(wins) / tot * 100.0) if tot > 0 else 0.0
        tot_pts = sum(t["pnl"] for t in trades)
        profit_factor = (sum(t["pnl"] for t in wins) / abs(sum(t["pnl"] for t in losses))) if losses and sum(t["pnl"] for t in losses) != 0 else 0.0
        max_drawdown = 0.0
        cum = 0.0
        peak = 0.0
        for t in trades:
            cum += t["pnl"]
            if cum > peak: peak = cum
            dd = peak - cum
            if dd > max_drawdown: max_drawdown = dd
            
        results[lvl] = {
            "name": p["name"],
            "trades": tot,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": win_rate,
            "net_pts": tot_pts,
            "net_usd_001": tot_pts * 1.0, # 1 pt in Gold per 0.01 lot is $1.00
            "pf": profit_factor,
            "max_dd_pts": max_drawdown
        }

    print(f"{'Level':<30} | {'Trades':<8} | {'Win Rate':<10} | {'Net Pts':<12} | {'Net ($ 0.01)':<14} | {'PF':<6} | {'Max DD'}")
    print("-" * 105)
    for lvl in range(1, 6):
        r = results[lvl]
        print(f"{r['name']:<30} | {r['trades']:<8} | {r['win_rate']:>6.1f}%   | {r['net_pts']:>+8.2f} pts | ${r['net_usd_001']:>+10.2f}   | {r['pf']:>4.2f} | -{r['max_dd_pts']:.1f} pts")

if __name__ == "__main__":
    backtest_all_presets()

