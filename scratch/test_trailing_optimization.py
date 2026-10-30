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
        if h_diff > l_diff and h_diff > 0: dm_plus[i] = h_diff
        if l_diff > h_diff and l_diff > 0: dm_minus[i] = l_diff

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
            if denom > 0: dx[i] = 100.0 * abs(di_plus[i] - di_minus[i]) / denom
                
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

def test_trailing():
    if not mt5.initialize():
        return
    rates = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M1, 1, 4000)
    mt5.shutdown()
    closes = rates["close"]
    highs = rates["high"]
    lows = rates["low"]
    n = len(closes)

    ema_50 = calculate_ema(closes, 50)
    ema_200 = calculate_ema(closes, 200)
    adx, di_plus, di_minus = calculate_adx_series(highs, lows, closes, 14)
    macd, sig, hist = calculate_macd_series(closes, 12, 26, 9)

    sma_250 = np.zeros(n)
    for i in range(250, n):
        sma_250[i] = np.mean(closes[i - 250 + 1:i + 1])

    # Let's test combinations of:
    # trail_arm: 1.0, 1.5, 2.0
    # trail_give: 20%
    # min_lock: 0.3, 0.5, 1.0
    # sl: 3.0, 4.0, 5.0, 6.0
    # entry: pullback bounce off MA vs direct

    print(f"=== TESTING TRAILING ENGINE ACROSS {n} BARS ===")

    for sl in [3.0, 4.0, 5.0]:
        for arm in [1.2, 1.5, 2.0]:
            for min_lock in [0.4, 0.8]:
                trades = []
                pos = None
                for i in range(300, n - 1):
                    c = closes[i]
                    h = highs[i]
                    l = lows[i]
                    c_prev = closes[i-1]
                    ma = sma_250[i]
                    dist = abs(c - ma)

                    if pos is not None:
                        # Excursion
                        d = pos["dir"]
                        # High water mark
                        max_p = (h - pos["entry_p"]) if d == 1 else (pos["entry_p"] - l)
                        curr_p = (c - pos["entry_p"]) if d == 1 else (pos["entry_p"] - c)
                        if max_p > pos["peak"]:
                            pos["peak"] = max_p
                        
                        # Check SL
                        if curr_p <= -sl:
                            trades.append(-sl)
                            pos = None
                            continue
                        
                        # Trailing check
                        if pos["peak"] >= arm:
                            give = pos["peak"] * 0.25
                            t_stop = max(pos["peak"] - give, min_lock)
                            if curr_p <= t_stop:
                                trades.append(t_stop)
                                pos = None
                                continue

                        if (i - pos["entry_bar"]) >= 40:
                            trades.append(curr_p)
                            pos = None
                            continue

                    if pos is None:
                        if dist > 20.0:
                            continue
                        # TCS 3/4
                        p1_bull = (ema_50[i] > ema_200[i]) and (c_prev > ema_50[i]) and (c_prev > ema_200[i])
                        p1_bear = (ema_50[i] < ema_200[i]) and (c_prev < ema_50[i]) and (c_prev < ema_200[i])
                        p2_bull = (adx[i] >= 20.0) and (di_plus[i] > di_minus[i])
                        p2_bear = (adx[i] >= 20.0) and (di_minus[i] > di_plus[i])
                        p3_bull = closes[i-1] > closes[i-6] and lows[i-1] > lows[i-6]
                        p3_bear = closes[i-1] < closes[i-6] and highs[i-1] < highs[i-6]
                        p4_bull = (hist[i] > 0) and (hist[i] > hist[i-1])
                        p4_bear = (hist[i] < 0) and (hist[i] < hist[i-1])

                        b_sc = sum([p1_bull, p2_bull, p3_bull, p4_bull])
                        s_sc = sum([p1_bear, p2_bear, p3_bear, p4_bear])

                        sig_dir = 0
                        if b_sc >= 3 and b_sc > s_sc: sig_dir = 1
                        elif s_sc >= 3 and s_sc > b_sc: sig_dir = -1

                        if sig_dir != 0:
                            # Pullback condition: price must be within 10 pts of MA
                            if dist <= 12.0:
                                pos = {"dir": sig_dir, "entry_p": c, "entry_bar": i, "peak": 0.0}

                wins = [t for t in trades if t > 0]
                losses = [t for t in trades if t < 0]
                tot = len(trades)
                wr = len(wins) / tot * 100.0 if tot else 0.0
                net = sum(trades)
                pf = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else 0.0
                if net > 0:
                    print(f"SL: ${sl:.1f} | Arm: ${arm:.1f} | Lock: ${min_lock:.1f} -> Trades: {tot} | WinRate: {wr:.1f}% | Net: {net:+.1f} pts | PF: {pf:.2f} (WINNER!)")

if __name__ == "__main__":
    test_trailing()

