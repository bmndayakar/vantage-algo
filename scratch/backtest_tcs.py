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

def evaluate_tcs_bar(idx, highs, lows, closes, ema_50, ema_200, adx, di_plus, di_minus, hist, lookback=20, require_adx_rising=True, min_adx=25.0):
    c = closes[idx]
    
    # Pillar 1: Trend Direction
    p1_bull = (ema_50[idx] > ema_200[idx]) and (c > ema_50[idx]) and (c > ema_200[idx])
    p1_bear = (ema_50[idx] < ema_200[idx]) and (c < ema_50[idx]) and (c < ema_200[idx])
    
    # Pillar 2: Trend Strength
    adx_val = adx[idx]
    adx_rising = adx[idx] > adx[idx - 1] if idx > 0 else False
    adx_ok = (adx_val >= min_adx) and (adx_rising if require_adx_rising else True)
    p2_bull = adx_ok and (di_plus[idx] > di_minus[idx])
    p2_bear = adx_ok and (di_minus[idx] > di_plus[idx])
    
    # Pillar 3: Price Structure (Higher Highs/Lows vs Lower Highs/Lows)
    start = max(1, idx - lookback)
    pivots = []
    for i in range(start, idx):
        if highs[i] > highs[i - 1] and highs[i] > highs[i + 1]:
            pivots.append(("H", highs[i]))
        elif lows[i] < lows[i - 1] and lows[i] < lows[i + 1]:
            pivots.append(("L", lows[i]))
            
    sh = [p[1] for p in pivots if p[0] == "H"]
    sl = [p[1] for p in pivots if p[0] == "L"]
    
    p3_bull = False
    p3_bear = False
    struct_tag = "CHOP"
    if len(sh) >= 2 and len(sl) >= 2:
        if sh[-1] > sh[-2] and sl[-1] > sl[-2]:
            p3_bull = True
            struct_tag = "HH_HL"
        elif sh[-1] < sh[-2] and sl[-1] < sl[-2]:
            p3_bear = True
            struct_tag = "LH_LL"
    else:
        # Fallback 5-bar momentum
        if closes[idx] > closes[idx - 4] and lows[idx] > lows[idx - 4]:
            p3_bull = True
            struct_tag = "MOM_UP"
        elif closes[idx] < closes[idx - 4] and highs[idx] < highs[idx - 4]:
            p3_bear = True
            struct_tag = "MOM_DN"
            
    # Pillar 4: Momentum Confirmation
    hist_val = hist[idx]
    hist_rising = hist[idx] > hist[idx - 1] if idx > 0 else False
    p4_bull = (hist_val > 0) and hist_rising
    p4_bear = (hist_val < 0) and (not hist_rising)
    
    bull_score = sum([p1_bull, p2_bull, p3_bull, p4_bull])
    bear_score = sum([p1_bear, p2_bear, p3_bear, p4_bear])
    
    direction = 0
    if bull_score >= 3 and bull_score > bear_score:
        direction = 1
    elif bear_score >= 3 and bear_score > bull_score:
        direction = -1
        
    return {
        "direction": direction,
        "bull_score": bull_score,
        "bear_score": bear_score,
        "p1_bull": p1_bull, "p1_bear": p1_bear,
        "p2_bull": p2_bull, "p2_bear": p2_bear,
        "p3_bull": p3_bull, "p3_bear": p3_bear,
        "p4_bull": p4_bull, "p4_bear": p4_bear,
        "ema_50": float(ema_50[idx]),
        "ema_200": float(ema_200[idx]),
        "adx": float(adx_val),
        "adx_rising": bool(adx_rising),
        "di_plus": float(di_plus[idx]),
        "di_minus": float(di_minus[idx]),
        "struct": struct_tag,
        "hist": float(hist_val),
        "hist_rising": bool(hist_rising),
    }

def run_backtest():
    print("=== BACKTESTING TCS OVER HISTORICAL XAUUSD DATA ===")
    if not mt5.initialize():
        print("MT5 initialization failed!")
        return
        
    # Fetch 3000 M1 bars (~2.5 days of trading)
    rates = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M1, 1, 3000)
    mt5.shutdown()
    
    if rates is None or len(rates) < 500:
        print("Insufficient rates fetched.")
        return
        
    closes = rates["close"]
    highs = rates["high"]
    lows = rates["low"]
    times = rates["time"]
    n = len(closes)
    print(f"Total bars fetched: {n} from {datetime.datetime.fromtimestamp(times[0])} to {datetime.datetime.fromtimestamp(times[-1])}")
    
    # Pre-calculate series
    ema_50 = calculate_ema(closes, 50)
    ema_200 = calculate_ema(closes, 200)
    adx, di_plus, di_minus = calculate_adx_series(highs, lows, closes, 14)
    macd, sig, hist = calculate_macd_series(closes, 12, 26, 9)
    
    # Simulate Scalping Strategy:
    # Compare:
    # 1. Unfiltered (Classic: buy above 250 MA, sell below 250 MA)
    # 2. TCS Filtered (Only buy when TCS confirms Bullish, only sell when TCS confirms Bearish)
    
    sma_250 = np.zeros(n)
    for i in range(250, n):
        sma_250[i] = np.mean(closes[i - 250 + 1:i + 1])
        
    def simulate(use_tcs=False, min_pillars=3, require_rising=True):
        trades = []
        pos = None # {"dir": 1/-1, "entry_p": float, "entry_bar": int}
        
        for i in range(300, n - 1):
            c_now = closes[i]
            tcs_res = evaluate_tcs_bar(i, highs, lows, closes, ema_50, ema_200, adx, di_plus, di_minus, hist,
                                       require_adx_rising=require_rising, min_adx=25.0)
            
            # Check exit if in position
            if pos is not None:
                pnl_pts = (c_now - pos["entry_p"]) if pos["dir"] == 1 else (pos["entry_p"] - c_now)
                # Simple scalp exit: +$1.00 TP or -$3.00 SL or max 30 bars
                dur = i - pos["entry_bar"]
                if pnl_pts >= 1.0 or pnl_pts <= -3.0 or dur >= 30:
                    trades.append({"pnl": pnl_pts, "dur": dur})
                    pos = None
                    continue
                    
            # Check entry if flat
            if pos is None:
                if use_tcs:
                    score = tcs_res["bull_score"] if tcs_res["direction"] == 1 else (tcs_res["bear_score"] if tcs_res["direction"] == -1 else 0)
                    if tcs_res["direction"] == 1 and score >= min_pillars:
                        pos = {"dir": 1, "entry_p": c_now, "entry_bar": i}
                    elif tcs_res["direction"] == -1 and score >= min_pillars:
                        pos = {"dir": -1, "entry_p": c_now, "entry_bar": i}
                else:
                    # Legacy 250 SMA
                    if c_now > sma_250[i]:
                        pos = {"dir": 1, "entry_p": c_now, "entry_bar": i}
                    elif c_now < sma_250[i]:
                        pos = {"dir": -1, "entry_p": c_now, "entry_bar": i}
                        
        wins = [t for t in trades if t["pnl"] > 0]
        losses = [t for t in trades if t["pnl"] < 0]
        tot = len(trades)
        win_rate = (len(wins) / tot * 100.0) if tot > 0 else 0.0
        tot_pts = sum(t["pnl"] for t in trades)
        return {
            "total_trades": tot,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": win_rate,
            "net_pts": tot_pts,
            "profit_factor": (sum(t["pnl"] for t in wins) / abs(sum(t["pnl"] for t in losses))) if losses and sum(t["pnl"] for t in losses) != 0 else 0.0
        }
        
    res_legacy = simulate(use_tcs=False)
    res_tcs_3 = simulate(use_tcs=True, min_pillars=3, require_rising=False)
    res_tcs_3_rising = simulate(use_tcs=True, min_pillars=3, require_rising=True)
    res_tcs_4 = simulate(use_tcs=True, min_pillars=4, require_rising=False)
    
    print("\n=== COMPARATIVE BACKTEST RESULTS (3000 M1 Bars) ===")
    print(f"1. Legacy 250-SMA (No TCS Filter):")
    print(f"   Trades: {res_legacy['total_trades']} | Win Rate: {res_legacy['win_rate']:.1f}% | Net Points: {res_legacy['net_pts']:+.1f} | PF: {res_legacy['profit_factor']:.2f}")
    
    print(f"\n2. TCS Filter (3/4 Pillars, ADX >= 25):")
    print(f"   Trades: {res_tcs_3['total_trades']} | Win Rate: {res_tcs_3['win_rate']:.1f}% | Net Points: {res_tcs_3['net_pts']:+.1f} | PF: {res_tcs_3['profit_factor']:.2f}")
    
    print(f"\n3. TCS Filter (3/4 Pillars + Rising ADX Required):")
    print(f"   Trades: {res_tcs_3_rising['total_trades']} | Win Rate: {res_tcs_3_rising['win_rate']:.1f}% | Net Points: {res_tcs_3_rising['net_pts']:+.1f} | PF: {res_tcs_3_rising['profit_factor']:.2f}")

    print(f"\n4. TCS Strict (4/4 Pillars All Confirm):")
    print(f"   Trades: {res_tcs_4['total_trades']} | Win Rate: {res_tcs_4['win_rate']:.1f}% | Net Points: {res_tcs_4['net_pts']:+.1f} | PF: {res_tcs_4['profit_factor']:.2f}")

if __name__ == "__main__":
    run_backtest()

