"""
terminal_monitor.py - Real-Time Terminal Command Center for Vantage / MT5 Bot
Run in any terminal: python terminal_monitor.py
Auto-refreshes every 0.5 seconds with live ASCII telemetry, technicals, and safety guard status.
"""
import os
import sys
import time
import datetime as dt
import urllib.request
import json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import up_down_tracker_win_bot_xauusd as bot_module
import MetaTrader5 as mt5
import numpy as np


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def main():
    kw = bot_module.mt5_env()
    if not mt5.initialize(**kw):
        print(f"[!] Error: MT5 initialize failed: {mt5.last_error()}")
        sys.exit(1)

    print("[+] Connected to MT5. Launching Live Monitor...")
    time.sleep(1)

    sym = "XAUUSD"

    try:
        while True:
            acc = mt5.account_info()
            if not acc:
                print("Failed to fetch account info")
                time.sleep(0.5)
                continue

            tk = mt5.symbol_info_tick(sym)
            if not tk or tk.bid <= 0:
                print(f"Waiting for {sym} quote...")
                time.sleep(0.5)
                continue

            # Calculate M1 Indicators
            rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M1, 0, 250)
            ma = float(np.mean(rates["close"])) if rates is not None and len(rates) >= 250 else 0.0

            r = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M1, 1, 16)
            if r is not None and len(r) >= 15:
                diffs = np.diff(r["close"])
                gains = np.where(diffs > 0, diffs, 0.0)
                losses = np.where(diffs < 0, -diffs, 0.0)
                avg_g = float(np.mean(gains[-14:]))
                avg_l = float(np.mean(losses[-14:]))
                rsi = 100.0 - (100.0 / (1.0 + (avg_g / avg_l))) if avg_l > 0 else 50.0
                pc = r["close"][:-1]
                h, l = r["high"][1:], r["low"][1:]
                atr = float(np.mean(np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))))
            else:
                rsi, atr = 50.0, 1.0

            pos = mt5.positions_get(symbol=sym) or ()
            bot_pos = [p for p in pos if p.magic in {123790, 789998}]

            total_basket = sum(p.profit + p.swap for p in bot_pos)
            mode_badge = "DEMO (100% VIRTUAL)" if acc.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO else "LIVE REAL MONEY ⚠️"

            # Render ASCII Dashboard
            lines = []
            lines.append("=" * 72)
            lines.append(f"  VANTAGE ALGO — LIVE TERMINAL RADAR  [{dt.datetime.now().strftime('%H:%M:%S')}]")
            lines.append("=" * 72)
            lines.append("  [SECTION 1: ACCOUNT & ENVIRONMENT OVERVIEW]")
            lines.append(f"  Account: #{acc.login} ({acc.server})  |  MODE: {mode_badge}")
            lines.append(f"  Balance: ${acc.balance:,.2f}  |  Equity: ${acc.equity:,.2f}  |  Free Margin: ${acc.margin_free:,.2f}")
            lines.append("-" * 72)
            lines.append(f"  [SECTION 2: MARKET QUOTES & TECHNICAL SLATE — {sym}]")
            lines.append(f"  Bid: {tk.bid:<9.2f} Ask: {tk.ask:<9.2f} Spread: ${tk.ask - tk.bid:.2f}  ATR(14): ${atr:.2f}")
            trend_str = "BEARISH (Below MA)" if tk.bid < ma else "BULLISH (Above MA)"
            dist_ma = abs(tk.bid - ma)
            lines.append(f"  MA-250: {ma:<8.2f} Dist: ${dist_ma:.2f} ({trend_str})  |  RSI(14): {rsi:.1f}")
            lines.append("-" * 72)

            # Live Bot Status and Telemetry from Engine
            live_status = "SCANNING"
            radar_conditions = ""
            try:
                req = urllib.request.Request("http://127.0.0.1:8000/api/state", headers={"User-Agent": "terminal-monitor"})
                with urllib.request.urlopen(req, timeout=0.2) as resp:
                    st_data = json.loads(resp.read().decode("utf-8"))
                    live_status = st_data.get("bot", {}).get("status") or ("RUNNING" if st_data.get("is_running") else "BOT IDLE")
                    telem = st_data.get("telemetry", {})
                    if telem:
                        b_desc = telem.get("buy_target_desc", "")
                        s_desc = telem.get("sell_target_desc", "")
                        if b_desc and s_desc:
                            radar_conditions = f"BUY: {b_desc}  |  SELL: {s_desc}"
                        elif telem.get("target_entry_desc"):
                            radar_conditions = telem.get("target_entry_desc")
            except Exception:
                if bot_pos:
                    live_status = f"TRACKING POSITION ({len(bot_pos)} legs)"
                else:
                    live_status = f"WAIT PULLBACK TO MA (${dist_ma:.2f})" if dist_ma > 3.0 else "PULLBACK ZONE: Monitoring Rejection"

            # RSI state description: strictly oscillator boundaries
            if rsi >= 70.0:
                rsi_state = "OVERBOUGHT (Buy Blocked / Climax Risk)"
            elif rsi <= 30.0:
                rsi_state = "OVERSOLD (Sell Blocked / Floor Risk)"
            else:
                rsi_state = "NORMAL (Safe Entry Window)"

            lines.append("  [SECTION 3: REAL-TIME ENTRY TELEMETRY & MA RADAR]")
            lines.append(f"  Engine Status   : {live_status}")
            lines.append(f"  RSI-14 Status   : {rsi:.1f} — {rsi_state}")
            if radar_conditions:
                lines.append(f"  Entry Conditions: {radar_conditions}")
            else:
                lines.append(f"  MA Target Zone  : ${ma:.2f} ± $3.00 (Current Dist: ${dist_ma:.2f})")
            lines.append("-" * 72)

            # Positions Section
            lines.append("  [SECTION 4: ACTIVE BOT POSITIONS & BASKET P&L]")
            lines.append(f"  Open Legs: {len(bot_pos)}  |  Basket Floating P&L: ${total_basket:+.2f}")
            if bot_pos:
                lines.append(f"  {'Ticket':<12} {'Type':<6} {'Lots':<6} {'Open Price':<12} {'Cur Price':<12} {'Floating P&L':<14} {'Tag'}")
                for p in bot_pos:
                    p_type = "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL"
                    tag = "RECOVERY" if p.magic == 789998 else "GRID"
                    lines.append(f"  #{p.ticket:<11} {p_type:<6} {p.volume:<6.2f} {p.price_open:<12.2f} {p.price_current:<12.2f} ${p.profit:+.2f}{'':<8} [{tag}]")
            else:
                lines.append("  [No active trades — Engine scanning for high-probability setups...]")

            lines.append("-" * 72)
            lines.append("  [SECTION 5: ACTIVE SAFETY GUARDS & RISK CONTROLS]")
            lines.append("  • Max Grid Legs: 3 / 3             • Trend Invalidation Cut: $6.00 past MA")
            lines.append("  • Break-Even Bailout: +$0.05       • Max Basket SL: $20.00 (20% equity cap)")
            lines.append("  • Automated Loss Recycler: ON       • RSI Climax Guard: 70/30 Filter Active")
            lines.append("=" * 72)
            lines.append("  Press Ctrl+C to exit monitor (Bot continues trading in background)")

            clear_screen()
            print("\n".join(lines))
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n[+] Monitor stopped. MT5 connection closed.")
        mt5.shutdown()


if __name__ == "__main__":
    main()

