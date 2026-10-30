import MetaTrader5 as mt5
import numpy as np
import datetime

def calculate_ema(values, span):
    alpha = 2.0 / (span + 1.0)
    ema = np.empty_like(values, dtype=float)
    ema[0] = values[0]
    for i in range(1, len(values)):
        ema[i] = ema[i - 1] * (1.0 - alpha) + values[i] * alpha
    return ema

def calculate_adx(highs, lows, closes, period=14):
    n = len(closes)
    if n < period * 2:
        return 0.0, 0.0, 0.0, False
        
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
            
    # Wilder's Smoothing
    tr_smooth = np.zeros(n)
    dm_plus_smooth = np.zeros(n)
    dm_minus_smooth = np.zeros(n)
    
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
                
    # ADX smoothing
    adx = np.zeros(n)
    start_idx = period * 2 - 1
    if start_idx < n:
        adx[start_idx] = np.mean(dx[period:start_idx + 1])
        for i in range(start_idx + 1, n):
            adx[i] = (adx[i - 1] * (period - 1) + dx[i]) / period
            
    adx_curr = float(adx[-1])
    adx_prev = float(adx[-2])
    di_plus_curr = float(di_plus[-1])
    di_minus_curr = float(di_minus[-1])
    is_rising = adx_curr > adx_prev
    return adx_curr, di_plus_curr, di_minus_curr, is_rising

def calculate_macd(closes, fast=12, slow=26, signal=9):
    if len(closes) < slow + signal + 5:
        return 0.0, 0.0, 0.0, False
    fast_ema = calculate_ema(closes, fast)
    slow_ema = calculate_ema(closes, slow)
    macd_line = fast_ema - slow_ema
    sig_line = calculate_ema(macd_line[slow - 1:], signal)
    
    # Pad signal line to match length
    full_sig = np.zeros_like(macd_line)
    full_sig[slow - 1:] = sig_line
    hist = macd_line - full_sig
    
    hist_curr = float(hist[-1])
    hist_prev = float(hist[-2])
    macd_curr = float(macd_line[-1])
    sig_curr = float(full_sig[-1])
    is_rising = hist_curr > hist_prev
    return macd_curr, sig_curr, hist_curr, is_rising

def calculate_structure(highs, lows, closes, lookback=20):
    # Swing Pivot detection (high higher than neighbors, low lower than neighbors)
    # Evaluated on closed bars
    n = len(closes)
    if n < lookback:
        return "INSUFFICIENT_DATA", []
        
    pivots = []
    # Identify local swing highs and lows
    for i in range(n - lookback, n - 1):
        if highs[i] > highs[i - 1] and highs[i] > highs[i + 1]:
            pivots.append(("H", highs[i], i))
        elif lows[i] < lows[i - 1] and lows[i] < lows[i + 1]:
            pivots.append(("L", lows[i], i))
            
    swing_highs = [p for p in pivots if p[0] == "H"]
    swing_lows = [p for p in pivots if p[0] == "L"]
    
    if len(swing_highs) >= 2 and len(swing_lows) >= 2:
        sh2, sh1 = swing_highs[-2][1], swing_highs[-1][1]
        sl2, sl1 = swing_lows[-2][1], swing_lows[-1][1]
        
        if sh1 > sh2 and sl1 > sl2:
            return "HH_HL_BULLISH", [sh2, sh1, sl2, sl1]
        elif sh1 < sh2 and sl1 < sl2:
            return "LH_LL_BEARISH", [sh2, sh1, sl2, sl1]
        else:
            return "MIXED_CHOPPY", [sh2, sh1, sl2, sl1]
            
    # Fallback to recent candle slope
    if closes[-1] > closes[-5] and lows[-1] > lows[-5]:
        return "RECENT_HIGHER", []
    elif closes[-1] < closes[-5] and highs[-1] < highs[-5]:
        return "RECENT_LOWER", []
    return "CONSOLIDATING", []

print("=== TESTING TREND CONFIRMATION SYSTEM ON MT5 LIVE RATES ===")
if mt5.initialize():
    for tf_name, tf_const in [("M1", mt5.TIMEFRAME_M1), ("M5", mt5.TIMEFRAME_M5)]:
        print(f"\n--- TIMEFRAME {tf_name} ---")
        # Fetch 300 bars of closed data (shift 1 to 300)
        rates = mt5.copy_rates_from_pos("XAUUSD", tf_const, 1, 300)
        if rates is not None and len(rates) >= 250:
            closes = rates["close"]
            highs = rates["high"]
            lows = rates["low"]
            last_close = float(closes[-1])
            last_time = datetime.datetime.fromtimestamp(rates["time"][-1])
            
            # 1. 50 EMA & 200 EMA
            ema_50 = calculate_ema(closes, 50)[-1]
            ema_200 = calculate_ema(closes, 200)[-1]
            
            p1_bull = (ema_50 > ema_200) and (last_close > ema_50) and (last_close > ema_200)
            p1_bear = (ema_50 < ema_200) and (last_close < ema_50) and (last_close < ema_200)
            p1_status = "BULLISH" if p1_bull else ("BEARISH" if p1_bear else "NEUTRAL")
            
            # 2. ADX(14)
            adx_val, di_plus, di_minus, adx_rising = calculate_adx(highs, lows, closes, 14)
            p2_bull = (adx_val >= 25.0) and (di_plus > di_minus)
            p2_bear = (adx_val >= 25.0) and (di_minus > di_plus)
            p2_status = "BULLISH" if p2_bull else ("BEARISH" if p2_bear else "WEAK_CHOPOFF")
            
            # 3. Structure
            struct_status, pts = calculate_structure(highs, lows, closes, lookback=25)
            p3_bull = "BULLISH" in struct_status or "HIGHER" in struct_status
            p3_bear = "BEARISH" in struct_status or "LOWER" in struct_status
            
            # 4. MACD
            macd_val, sig_val, hist_val, hist_rising = calculate_macd(closes, 12, 26, 9)
            p4_bull = (hist_val > 0) and hist_rising
            p4_bear = (hist_val < 0) and not hist_rising
            p4_status = "BULLISH" if p4_bull else ("BEARISH" if p4_bear else "NEUTRAL")
            
            print(f"Closed Bar Time: {last_time} | Close: {last_close:.2f}")
            print(f"Pillar 1 (Trend Dir): 50 EMA={ema_50:.2f}, 200 EMA={ema_200:.2f} -> {p1_status}")
            print(f"Pillar 2 (Strength): ADX(14)={adx_val:.1f} (Rising: {adx_rising}), +DI={di_plus:.1f}, -DI={di_minus:.1f} -> {p2_status}")
            print(f"Pillar 3 (Structure): {struct_status}")
            print(f"Pillar 4 (Momentum): MACD Hist={hist_val:.2f} (Rising: {hist_rising}) -> {p4_status}")
            
            # Total score
            bull_score = sum([p1_bull, p2_bull, p3_bull, p4_bull])
            bear_score = sum([p1_bear, p2_bear, p3_bear, p4_bear])
            
            final_signal = "NEUTRAL"
            if bull_score == 4:
                final_signal = "CONFIRMED BULLISH (4/4)"
            elif bear_score == 4:
                final_signal = "CONFIRMED BEARISH (4/4)"
            elif bull_score >= 3:
                final_signal = f"PROBABLE BULLISH ({bull_score}/4)"
            elif bear_score >= 3:
                final_signal = f"PROBABLE BEARISH ({bear_score}/4)"
            else:
                final_signal = f"CHOPPY / FILTERED (Bull: {bull_score}/4, Bear: {bear_score}/4)"
                
            print(f"Final Signal: {final_signal}")
    mt5.shutdown()

