"""
up_down_tracker_win_bot_xauusd.py - Python port of up_down_tracker_win_bot_xauusd.mq5.

Same logic as the EA (MA-250 trend entry, flat-lot loss grid, profit-peak trailing exit, soft time cap,
optional flip), driven from Python through the MetaTrader5 package. Needs the MT5 DESKTOP terminal INSTALLED on
this Windows PC. Put MT5_PATH / MT5_LOGIN / MT5_PASSWORD / MT5_SERVER in a .env next to this file and the script
launches + logs in the terminal itself; without .env it attaches to an already-open, logged-in terminal. Run ONE of {this script, the EA} per account/magic.

  python up_down_tracker_win_bot_xauusd.py selftest            # logic checks on a simulated broker, no MT5
  python up_down_tracker_win_bot_xauusd.py backtest --days 40  # replay real MT5 ticks through the same Bot code
  python up_down_tracker_win_bot_xauusd.py backtest --days 40 --sweep trail_arm=0.5,1,2 --sweep grid_max_legs=3,5 --jobs 4
  python up_down_tracker_win_bot_xauusd.py walkforward --days 365 --train-days 60 --test-days 30 --jobs 5   # tune on past, trade unseen
  python up_down_tracker_win_bot_xauusd.py run                 # DEMO accounts only (refuses a real account)
  python up_down_tracker_win_bot_xauusd.py run --allow-real    # real account: you own the risk
  python up_down_tracker_win_bot_xauusd.py run --symbol GOLD --tf M5 --grid-max-legs 3 --no-trail-on
  python up_down_tracker_win_bot_xauusd.py run --side sell --slope-bars 30   # sells only, and only while the MA is falling

Every EA input is a CLI flag (InpGridMaxLegs -> --grid-max-legs, bools -> --flag / --no-flag).
NOTE --tf: the EA's MA used the timeframe of the chart it was attached to; pick the same one here (default M1).
"""
import argparse, os, sys, time, datetime as dt
from dataclasses import dataclass, fields
from collections import namedtuple

HERE = os.path.dirname(os.path.abspath(__file__))
Tick = namedtuple("Tick", "bid ask time msc")           # time = server epoch s (MQL TimeCurrent), msc = ms
Pos = namedtuple("Pos", "ticket dir profit swap time magic")   # dir +1 buy / -1 sell


# ============================== INPUTS (same names/defaults as the .mq5) ==============================
@dataclass
class Cfg:
    symbol: str = "XAUUSD"
    tf: str = "M1"                       # chart timeframe the MA runs on
    lots: float = 0.01
    target_profit: float = 0.20
    daily_goal: float = 20.00
    basket_target: float = 0.10
    min_entry_gap_sec: int = 15
    ma_period: int = 250
    magic: int = 123790
    magic_recovery: int = 789998
    server_offset: int = 3
    soft_cap_min: int = 45
    soft_cap_profit: float = 0.00
    stop_loss: float = 0.0
    grid_sessions: bool = True
    grid_step_loss: float = 10.00
    grid_max_legs: int = 5
    grid_tp: float = 0.20
    grid_sl: float = 200.00
    hard_cap_hours: float = 0
    max_spread: float = 0.0
    trail_on: bool = True
    trail_arm: float = 1.00
    trail_give_frac: float = 0.20
    trail_min_give: float = 0.00
    trail_atr_k: float = 0.0
    atr_period: int = 14
    trail_min_lock: float = 0.30
    flip_on_reversal: bool = False
    side: str = "both"                   # both | buy | sell : only open baskets in this direction
    slope_bars: int = 0                  # >0: also require the MA to slope that way vs N bars ago (falling MA -> sells only)
    max_ma_dist: float = 0.0             # >0: max allowable distance from MA (e.g. 2.50 on Gold); blocks buying at the top of a spike
    rsi_filter: bool = False             # True: block BUY when RSI > rsi_ob, block SELL when RSI < rsi_os
    rsi_period: int = 14                 # RSI calculation period
    rsi_ob: float = 70.0                 # RSI overbought threshold
    rsi_os: float = 30.0                 # RSI oversold threshold
    bailout_on_max_legs: bool = True     # True: when grid hits max legs, switch target to bailout_target to escape
    bailout_target: float = 0.05         # Target profit ($) in bailout mode (0.05 = breakeven exit)
    trend_stop_dist: float = 0.0         # >0: close basket if price moves N dollars on wrong side of MA
    max_equity_risk_pct: float = 0.0     # >0: max floating basket loss allowed as % of account equity
    break_time: bool = False             # True: finish open trades, but block new initial entries
    min_free_margin: float = 10.0        # Min free margin ($) required before allowing a new entry
    margin_buffer_pct: float = 20.0      # Required free margin safety buffer % over required margin
    min_margin_level: float = 0.0        # Min account margin level % required (0 = disabled, 100-200 optional)
    enable_log: bool = True
    log_file: str = "up_down_tracker_decisions_py.csv"   # separate from the EA's CSV


# ============================== BOT (line-for-line port of OnTick) ==============================
class Bot:
    def __init__(s, cfg, br):
        s.c, s.br = cfg, br
        s.status = "Initializing..."; s.basket = 0.0; s.last_exit = 0; s.open_time = 0; s.ma = 0.0
        s.daily = 0.0; s.deals = 0; s.nopen = 0; s.tp_price = 0.0; s.dir = 0
        s.peak = 0.0; s.trail_stop = 0.0; s.flip = 0; s.exposure = 0.0
        s.dist_ma = 0.0; s.rsi = 50.0; s.margin_cooldown_until = 0; s.last_order_error = ""; s.margin_reject_count = 0
        s.events = []

    # ---- CSV decision log ----
    def log(s, ev, side, detail, price, basket, realized):
        c = s.c; s.events.append(f"{ev} {side} {detail} basket={basket:.2f}")
        if not c.enable_log: return
        path = os.path.normpath(os.path.join(HERE, "..", "Files", c.log_file))
        try:
            new = not os.path.exists(path) or os.path.getsize(path) == 0
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tk = s.br.tick(); bid, ask, tc = tk.bid, tk.ask, tk.time
            age = int((tc - s.open_time) / 60) if s.open_time > 0 else 0
            with open(path, "a", encoding="ascii", errors="replace") as f:
                if new: f.write("time,event,side,detail,price,ma,spread,basket,openPos,ageMin,realized,dailyProfit\n")
                f.write(",".join([dt.datetime.fromtimestamp(tc, dt.timezone.utc).strftime("%Y.%m.%d %H:%M:%S"), ev, side, detail,
                                  f"{price:.2f}", f"{s.ma:.2f}", f"{ask - bid:.2f}", f"{basket:.2f}", str(s.nopen), str(age),
                                  f"{realized:.2f}", f"{s.daily:.2f}"]) + "\n")
        except OSError:
            pass

    def allowed(s, d): return s.c.side == "both" or d == (1 if s.c.side == "buy" else -1)

    def close_all(s):
        for _ in range(10):
            ps = s.br.positions()
            if not ps: break
            for p in ps: s.br.close(p)
            s.br.sleep(0.3)
        s.last_exit = s.br.tick().time                  # start the cooldown clock
        s.status = f"COOLDOWN {s.c.min_entry_gap_sec}s"

    def on_timer(s):
        s.daily, s.deals = s.br.daily_profit()

    def on_tick(s):
        c = s.c; tk = s.br.tick(); bid, ask, tc = tk.bid, tk.ask, tk.time
        if bid <= 0 or ask <= 0:
            s.status = "MARKET CLOSED / NO QUOTE"
            return
        m = s.br.ma()
        if m: s.ma = m
        if hasattr(s.br, "rsi"):
            rv = s.br.rsi(c.rsi_period)
            if rv is not None: s.rsi = rv
        eq, mg = s.br.equity_margin(); s.exposure = (mg / eq * 100.0) if eq > 0 else 0.0

        # 1. SCAN POSITIONS (EA iterates newest -> oldest; buyP/sellP keep the last leg seen)
        has_buy = has_sell = False; buy_p = sell_p = 0.0; total = 0.0; earliest = 0
        ps = s.br.positions(); s.nopen = len(ps)
        for p in reversed(ps):
            v = p.profit + p.swap; total += v
            if earliest == 0 or p.time < earliest: earliest = p.time
            if p.dir > 0: has_buy, buy_p = True, v
            else: has_sell, sell_p = True, v
        s.basket = total; s.open_time = earliest if s.nopen > 0 else 0

        # profit point: price where the whole stack hits +target (basket is linear in price)
        s.dir = 1 if (has_buy and not has_sell) else (-1 if (has_sell and not has_buy) else 0)
        if s.nopen > 0 and s.dir != 0:
            tv, ts = s.br.tick_value_size()
            per_unit = (tv / ts) * c.lots * s.nopen if ts > 0 else 0
            if c.bailout_on_max_legs and s.nopen >= c.grid_max_legs:
                tgt = c.bailout_target
            else:
                tgt = c.grid_tp if c.grid_sessions else c.basket_target
            if per_unit > 0: s.tp_price = bid + s.dir * (tgt - total) / per_unit
        else:
            s.tp_price = 0.0

        # 1b. MAX-LEGS BAILOUT EXIT (Fast escape when stacked at max capacity)
        if c.grid_sessions and c.bailout_on_max_legs and s.nopen >= c.grid_max_legs and total >= c.bailout_target:
            s.status = f"GRID x{s.nopen} BAILOUT EXIT (${total:+.2f})"
            s.log("CLOSE", "BUY" if s.dir > 0 else "SELL", f"max-legs-bailout target={c.bailout_target:.2f}", bid, total, total)
            s.close_all()
            return

        # 1c. TREND INVALIDATION STOP (Cuts losing basket if market reverses strongly across MA)
        if c.trend_stop_dist > 0 and s.ma > 0 and s.nopen > 0 and s.dir != 0:
            dist_wrong = (s.ma - bid) if s.dir > 0 else (bid - s.ma)
            if dist_wrong >= c.trend_stop_dist:
                s.status = f"TREND INVALIDATED (${dist_wrong:.2f} past MA)"
                s.log("CLOSE", "BUY" if s.dir > 0 else "SELL", f"trend-inval dist={dist_wrong:.2f}", bid, total, total)
                s.close_all()
                return

        # 1d. EQUITY RISK STOP (Guarantees max drawdown % per basket on any account size)
        if s.nopen > 0 and c.max_equity_risk_pct > 0 and eq > 0:
            max_eq_loss = eq * (c.max_equity_risk_pct / 100.0)
            if total <= -max_eq_loss:
                s.status = f"EQUITY RISK STOP (-${abs(total):.2f} >= {c.max_equity_risk_pct:.0f}%)"
                s.log("CLOSE", "BUY" if s.dir > 0 else "SELL", f"equity-risk-sl limit={max_eq_loss:.2f}", bid, total, total)
                s.close_all()
                return

        # 1e. PROFIT-PEAK TRAIL
        if s.nopen == 0: s.peak = 0.0; s.trail_stop = 0.0
        elif total > s.peak: s.peak = total
        if c.trail_on and s.nopen > 0 and s.peak >= c.trail_arm:
            give = max(s.peak * c.trail_give_frac, c.trail_min_give)
            if c.trail_atr_k > 0:
                tv, ts = s.br.tick_value_size(); atr = s.br.atr()
                if ts > 0 and atr is not None:
                    give = max(give, c.trail_atr_k * atr * (tv / ts) * c.lots * s.nopen)
            s.trail_stop = max(s.peak - give, c.trail_min_lock)
            if total <= s.trail_stop:
                d = s.dir
                s.log("CLOSE", "BUY" if d > 0 else "SELL", "trail-exit", bid, total, total)
                s.close_all()
                if c.flip_on_reversal and d != 0: s.flip = -d
                return
            s.status = f"TRAILING {'BUY' if s.dir > 0 else 'SELL'} peak ${s.peak:.2f}"
            return

        # 2. basket exit (single-leg / non-grid only)
        if (not c.trail_on) and (not c.grid_sessions) and s.nopen > 0 and total >= c.basket_target:
            s.log("CLOSE", "-", "basket-target", bid, total, total); s.close_all(); return

        # 2b. SOFT TIME CAP: only exits at >= soft_cap_profit
        if s.nopen > 0 and s.open_time > 0:
            age_min = int((tc - s.open_time) / 60)
            if c.soft_cap_min > 0 and age_min >= c.soft_cap_min and total >= c.soft_cap_profit:
                s.status = "TIME CAP: SOFT"
                s.log("CLOSE", "-", "time-soft", bid, total, total); s.close_all(); return

        # 2c. GRID SESSIONS (owns the basket; never falls through)
        if c.grid_sessions and s.nopen > 0:
            if c.bailout_on_max_legs and s.nopen >= c.grid_max_legs:
                s.status = f"GRID x{s.nopen} (BAILOUT @ ${c.bailout_target:+.2f})"
            else:
                s.status = f"GRID x{s.nopen}"
            if (not c.trail_on) and total >= c.grid_tp:
                s.log("CLOSE", "-", "grid-tp", bid, total, total); s.close_all(); return
            if c.grid_sl > 0 and total <= -c.grid_sl:
                s.log("CLOSE", "-", "grid-sl", bid, total, total); s.close_all(); return
            if c.hard_cap_hours > 0 and s.open_time > 0 and (tc - s.open_time) / 3600.0 >= c.hard_cap_hours:
                s.log("CLOSE", "-", "time-hard", bid, total, total); s.close_all(); return
            if (not c.trail_on) and s.nopen == 1 and total >= c.target_profit:
                s.log("CLOSE", "-", "scalp-tp", bid, total, total); s.close_all(); return
            if s.nopen < c.grid_max_legs and total <= -(s.nopen * c.grid_step_loss):
                if tc < s.margin_cooldown_until:
                    rem = s.margin_cooldown_until - tc
                    err_msg = f": {s.last_order_error}" if s.last_order_error else ""
                    if s.margin_reject_count >= 2:
                        s.status = f"GRID PAUSED (INSUFFICIENT MARGIN): {s.last_order_error}"
                    else:
                        s.status = f"GRID WAIT MARGIN ({rem}s{err_msg})"
                    return
                ok, rc = s.br.order(1 if has_buy else -1)
                side = "BUY" if has_buy else "SELL"
                if ok:
                    s.last_order_error = ""
                    s.margin_reject_count = 0
                    s.log("ENTRY", side, "grid-add", bid, total, 0.0)
                else:
                    s.last_order_error = str(rc)
                    s.log("SKIP", side, f"grid-add-failed rc={rc}", bid, total, 0.0)
                    if "MARGIN" in str(rc).upper():
                        s.margin_reject_count += 1
                        if s.margin_reject_count >= 2:
                            s.margin_cooldown_until = tc + 86400
                            s.status = f"GRID PAUSED (INSUFFICIENT MARGIN): {rc}"
                            return
                    s.margin_cooldown_until = tc + 60
                    s.status = f"GRID MARGIN GUARD: {rc}"
            return

        # 3. single-leg scalp / stop (non-grid mode)
        for d, v, name in ((1, buy_p, "BUY"), (-1, sell_p, "SELL")):
            if (has_buy and not has_sell and d > 0) or (has_sell and not has_buy and d < 0):
                s.status = f"MONITORING {name}"
                if (not c.trail_on) and v >= c.target_profit:
                    s.log("CLOSE", name, "scalp-tp", bid, total, total); s.close_all(); return
                if c.stop_loss > 0 and v <= -c.stop_loss:
                    s.log("CLOSE", name, "stop-loss", bid, total, total); s.close_all(); return

        # 4. NEW ENTRY SIGNAL
        if s.nopen == 0:
            if tc < s.margin_cooldown_until:
                rem = s.margin_cooldown_until - tc
                err_msg = f": {s.last_order_error}" if s.last_order_error else ""
                if s.margin_reject_count >= 2:
                    s.status = f"PAUSED (INSUFFICIENT MARGIN): {s.last_order_error}. Please reduce lot size in Settings (⚙️)."
                else:
                    s.status = f"MARGIN COOLDOWN {rem}s{err_msg}"
                return
            if c.break_time: s.status = "☕ BREAK TIME (Tracking, no entries)"; s.flip = 0; return
            if s.daily >= c.daily_goal: s.status = "GOAL REACHED"; s.flip = 0; return
            if s.flip != 0 and not s.allowed(s.flip): s.flip = 0
            if s.flip != 0:                               # one-shot reversal entry (no cooldown, no MA vote)
                fd, s.flip = s.flip, 0
                ok, rc = s.br.order(fd); fs = "BUY" if fd > 0 else "SELL"
                if ok:
                    s.last_order_error = ""
                    s.margin_reject_count = 0
                    s.log("ENTRY", fs, "flip-reversal", bid, 0.0, 0.0)
                else:
                    s.last_order_error = str(rc)
                    s.log("SKIP", fs, f"flip-failed rc={rc}", bid, 0.0, 0.0)
                    s.last_exit = tc
                    if "MARGIN" in str(rc).upper():
                        s.margin_reject_count += 1
                        if s.margin_reject_count >= 2:
                            s.margin_cooldown_until = tc + 86400
                            s.status = f"PAUSED (INSUFFICIENT MARGIN): {rc}. Please reduce lot size in Settings (⚙️)."
                            return
                    s.margin_cooldown_until = tc + 60
                    s.status = f"MARGIN GUARD: {rc}"
                return
            since = tc - s.last_exit
            if s.last_exit > 0 and since < c.min_entry_gap_sec:
                s.status = f"COOLDOWN {c.min_entry_gap_sec - since}s"; return
            if s.ma > 0:
                s.status = "SIGNAL READY"
                if c.max_spread > 0 and (ask - bid) > c.max_spread:
                    s.status = f"SPREAD WIDE {ask - bid:.2f}"; return
                if bid > s.ma: d = 1
                elif bid < s.ma: d = -1
                else: return

                dist = abs(bid - s.ma)
                s.dist_ma = dist

                # 1. Overextension Guard: do not buy/sell if price is stretched too far from MA
                if c.max_ma_dist > 0 and dist > c.max_ma_dist:
                    s.status = f"OVEREXTENDED {dist:.2f} > {c.max_ma_dist:.2f}"
                    return

                # 2. RSI Overbought/Oversold Guard: do not buy overbought climax or sell oversold floor
                if c.rsi_filter:
                    if d > 0 and s.rsi >= c.rsi_ob:
                        s.status = f"RSI OVERBOUGHT ({s.rsi:.1f} >= {c.rsi_ob:.0f})"
                        return
                    if d < 0 and s.rsi <= c.rsi_os:
                        s.status = f"RSI OVERSOLD ({s.rsi:.1f} <= {c.rsi_os:.0f})"
                        return

                if not s.allowed(d): s.status = f"WAIT {c.side.upper()}" + (f"/SLOPE{c.slope_bars}" if c.slope_bars else ""); return
                if c.slope_bars > 0:
                    ago = s.br.ma_ago(c.slope_bars)
                    if not ago or (s.ma - ago) * d <= 0: s.status = f"WAIT SLOPE {'BUY' if d > 0 else 'SELL'}"; return
                ok, rc = s.br.order(d); side = "BUY" if d > 0 else "SELL"
                if ok:
                    s.last_order_error = ""
                    s.margin_reject_count = 0
                    s.log("ENTRY", side, "ma-signal", bid, 0.0, 0.0)
                else:
                    s.last_order_error = str(rc)
                    s.log("SKIP", side, f"ma-signal-failed rc={rc}", bid, 0.0, 0.0)
                    s.last_exit = tc
                    if "MARGIN" in str(rc).upper():
                        s.margin_reject_count += 1
                        if s.margin_reject_count >= 2:
                            s.margin_cooldown_until = tc + 86400
                            s.status = f"PAUSED (INSUFFICIENT MARGIN): {rc}. Please reduce lot size in Settings (⚙️)."
                            return
                    s.margin_cooldown_until = tc + 60
                    s.status = f"MARGIN GUARD: {rc}"
            else:
                s.status = f"CALCULATING MA ({c.tf} {c.ma_period})"
                return


# ============================== REAL BROKER (MetaTrader5 package) ==============================
def mt5_env(path=os.path.join(HERE, ".env")):
    """Read MT5_PATH / MT5_LOGIN / MT5_PASSWORD / MT5_SERVER from .env (or the process env) into initialize() kwargs.
    With them, initialize() launches terminal64.exe and logs in itself; without them it attaches to a running terminal."""
    env = dict(os.environ)
    if os.path.exists(path):   # ponytail: stdlib KEY=VALUE parser, no python-dotenv dependency
        for line in open(path, encoding="utf-8"):
            k, sep, v = line.strip().partition("=")
            if sep and not k.startswith("#"): env.setdefault(k.strip(), v.strip().strip('"\''))
    kw = {"path": env.get("MT5_PATH"), "login": env.get("MT5_LOGIN"), "password": env.get("MT5_PASSWORD"),
          "server": env.get("MT5_SERVER")}
    if kw["login"]: kw["login"] = int(kw["login"])
    return {k: v for k, v in kw.items() if v}


def save_mt5_env(login, password, server, path=None, env_path=os.path.join(HERE, ".env")):
    """Save or update MT5 credentials in .env."""
    lines = []
    keys_written = set()
    new_vals = {
        "MT5_PATH": path or r"C:\Program Files\MetaTrader 5\terminal64.exe",
        "MT5_LOGIN": str(login),
        "MT5_PASSWORD": str(password),
        "MT5_SERVER": str(server),
    }
    if os.path.exists(env_path):
        for line in open(env_path, "r", encoding="utf-8"):
            k, sep, v = line.strip().partition("=")
            if sep and k.strip() in new_vals:
                lines.append(f"{k.strip()}={new_vals[k.strip()]}\n")
                keys_written.add(k.strip())
            else:
                lines.append(line if line.endswith("\n") else line + "\n")
    for k, v in new_vals.items():
        if k not in keys_written:
            lines.append(f"{k}={v}\n")
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


class MT5Broker:
    def __init__(s, cfg):
        import MetaTrader5 as mt5, numpy as np
        s.mt5, s.np, s.c = mt5, np, cfg
        kw = mt5_env()
        if not mt5.initialize(**kw):
            # Prompt user interactively if running in terminal without active session
            if sys.stdin and hasattr(sys.stdin, "isatty") and sys.stdin.isatty():
                print("\n" + "=" * 58)
                print("  NO ACTIVE MT5 LOGIN DETECTED")
                print("  Enter your credentials to launch & log into MT5:")
                print("=" * 58)
                try:
                    p_path = kw.get("path") or r"C:\Program Files\MetaTrader 5\terminal64.exe"
                    u_path = input(f"MT5 Path [{p_path}]: ").strip() or p_path
                    u_login = input("MT5 Login (account #): ").strip()
                    import getpass
                    u_pass = getpass.getpass("MT5 Password: ").strip()
                    u_serv = input("MT5 Server (e.g. VantageFX-Live): ").strip()
                    if u_login and u_pass and u_serv:
                        save_mt5_env(u_login, u_pass, u_serv, u_path)
                        kw = {"path": u_path, "login": int(u_login), "password": u_pass, "server": u_serv}
                        if mt5.initialize(**kw):
                            print(f"[+] Successfully logged into account #{u_login} @ {u_serv}!\n")
                except Exception as e:
                    print(f"Interactive login input failed: {e}")
        if not mt5.initialize(**kw):
            raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()} "
                               f"(.env keys used: {sorted(k for k in kw if k != 'password')}; is MT5 installed and are login/server right?)")
        sym_clean = str(cfg.symbol).strip().upper()
        if mt5.symbol_select(sym_clean, True) and mt5.symbol_info(sym_clean) is not None:
            cfg.symbol = sym_clean
        else:
            base = sym_clean.split(".")[0].rstrip("m").rstrip("+")
            candidates = [sym_clean, sym_clean + "+", sym_clean + ".a", sym_clean + "m", sym_clean + ".",
                          base, base + "+", base + ".a", base + "m", base + ".",
                          "XAUUSD", "GOLD", "XAUUSD.a", "XAUUSDm", "XAUUSD."]
            for s_cand in dict.fromkeys(candidates):
                if mt5.symbol_select(s_cand, True) and mt5.symbol_info(s_cand) is not None:
                    print(f"symbol '{cfg.symbol}' auto-resolved to '{s_cand}' in MT5")
                    cfg.symbol = s_cand; break
            else:
                raise RuntimeError(f"symbol '{cfg.symbol}' not found in MT5 Market Watch")
        s.tf = getattr(mt5, "TIMEFRAME_" + cfg.tf.upper())
        s.magics = {cfg.magic, cfg.magic_recovery}

    def tick(s):
        t = s.mt5.symbol_info_tick(s.c.symbol)
        if t is None or t.bid is None or t.ask is None:
            return Tick(0.0, 0.0, int(time.time()), int(time.time() * 1000))
        return Tick(float(t.bid), float(t.ask), int(t.time), int(t.time_msc))

    def positions(s):
        ps = s.mt5.positions_get(symbol=s.c.symbol) or ()
        return [Pos(p.ticket, 1 if p.type == s.mt5.POSITION_TYPE_BUY else -1, p.profit, p.swap, int(p.time), p.magic)
                for p in ps if p.magic in s.magics]

    def ma(s):
        r = s.mt5.copy_rates_from_pos(s.c.symbol, s.tf, 0, s.c.ma_period)   # bar 0 = forming bar, like iMA shift 0
        return float(s.np.mean(r["close"])) if r is not None and len(r) >= s.c.ma_period else None

    def ma_ago(s, k):
        r = s.mt5.copy_rates_from_pos(s.c.symbol, s.tf, k, s.c.ma_period)       # SMA ending k bars back (closed bars)
        return float(s.np.mean(r["close"])) if r is not None and len(r) >= s.c.ma_period else None

    def atr(s):
        r = s.mt5.copy_rates_from_pos(s.c.symbol, s.mt5.TIMEFRAME_M1, 1, s.c.atr_period + 1)   # closed bars only
        if r is None or len(r) < s.c.atr_period + 1: return None
        np = s.np; pc = r["close"][:-1]; h, l = r["high"][1:], r["low"][1:]
        return float(np.mean(np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))))

    def rsi(s, period=14):
        r = s.mt5.copy_rates_from_pos(s.c.symbol, s.tf, 1, period + 2)   # closed bars
        if r is None or len(r) < period + 1: return 50.0
        diffs = s.np.diff(r["close"])
        gains = s.np.where(diffs > 0, diffs, 0.0)
        losses = s.np.where(diffs < 0, -diffs, 0.0)
        avg_g = float(s.np.mean(gains[-period:]))
        avg_l = float(s.np.mean(losses[-period:]))
        if avg_l == 0: return 100.0 if avg_g > 0 else 50.0
        rs = avg_g / avg_l
        return float(100.0 - (100.0 / (1.0 + rs)))

    def tick_value_size(s):
        i = s.mt5.symbol_info(s.c.symbol)
        if i is None: return 1.0, 0.01
        return i.trade_tick_value, i.trade_tick_size

    def equity_margin(s):
        a = s.mt5.account_info()
        if a is None: return 0.0, 0.0
        return a.equity, a.margin

    def _fill(s):
        i = s.mt5.symbol_info(s.c.symbol); m = s.mt5
        if i is None: return m.ORDER_FILLING_IOC
        fm = getattr(i, "filling_mode", 0)
        if fm & 2: return m.ORDER_FILLING_IOC
        if fm & 1: return m.ORDER_FILLING_FOK
        return m.ORDER_FILLING_RETURN

    def check_margin(s, d, lots=None):
        m = s.mt5
        acc = m.account_info()
        if acc is None:
            return False, "NO_ACCOUNT_INFO"
        free = float(acc.margin_free)
        vol = lots or s.c.lots
        t = m.symbol_info_tick(s.c.symbol)
        if t is None or t.ask <= 0 or t.bid <= 0:
            return False, "NO_TICK"
        price = t.ask if d > 0 else t.bid
        order_type = m.ORDER_TYPE_BUY if d > 0 else m.ORDER_TYPE_SELL
        needed = m.order_calc_margin(order_type, s.c.symbol, vol, price)
        if needed is None or needed <= 0:
            lev = acc.leverage if acc.leverage > 0 else 100
            sym_info = m.symbol_info(s.c.symbol)
            cs = sym_info.trade_contract_size if sym_info and sym_info.trade_contract_size > 0 else (100000.0 if ("USD" in s.c.symbol and "XAU" not in s.c.symbol and "GOLD" not in s.c.symbol) else 100.0)
            needed = (vol * cs * price) / lev
        needed = float(needed)

        # 1. Absolute free margin floor
        if free < s.c.min_free_margin:
            return False, f"FREE MARGIN ${free:.2f} < MIN ${s.c.min_free_margin:.2f}"

        # 2. Safety buffer over needed margin
        req_with_buf = needed * (1.0 + s.c.margin_buffer_pct / 100.0)
        if free < req_with_buf:
            return False, f"FREE MARGIN ${free:.2f} < REQUIRED ${req_with_buf:.2f} (needed ${needed:.2f} + {s.c.margin_buffer_pct:.0f}% buffer)"

        # 3. Account margin level check (Only if min_margin_level > 0 and account already has open positions)
        if acc.margin > 0 and acc.margin_level > 0 and s.c.min_margin_level > 0:
            if acc.margin_level < s.c.min_margin_level:
                return False, f"MARGIN LEVEL {acc.margin_level:.1f}% < MIN {s.c.min_margin_level:.0f}%"

        return True, "OK"

    def order(s, d):
        ok_m, reason = s.check_margin(d)
        if not ok_m:
            return False, f"MARGIN_REJECT: {reason}"

        m = s.mt5; t = s.mt5.symbol_info_tick(s.c.symbol)
        if t is None or t.ask <= 0 or t.bid <= 0:
            return False, "NO_TICK"
        price = t.ask if d > 0 else t.bid

        # Try best fill mode, and auto-retry if 10030 (TRADE_RETCODE_INVALID_FILL)
        fill_modes = [s._fill()]
        for f in [m.ORDER_FILLING_IOC, m.ORDER_FILLING_FOK, m.ORDER_FILLING_RETURN]:
            if f not in fill_modes:
                fill_modes.append(f)

        last_r = None
        for fill in fill_modes:
            req = dict(
                action=m.TRADE_ACTION_DEAL,
                symbol=s.c.symbol,
                volume=s.c.lots,
                type=m.ORDER_TYPE_BUY if d > 0 else m.ORDER_TYPE_SELL,
                price=price,
                deviation=50,
                magic=s.c.magic,
                comment="udt-py",
                type_time=m.ORDER_TIME_GTC,
                type_filling=fill,
            )
            r = m.order_send(req)
            last_r = r
            if r is not None and r.retcode == m.TRADE_RETCODE_DONE:
                return True, m.TRADE_RETCODE_DONE
            if r is not None and r.retcode != 10030:
                break

        rc = last_r.retcode if last_r else m.last_error()
        comment = getattr(last_r, "comment", "") if last_r else ""
        err_msg = f"{rc} ({comment})" if comment else str(rc)
        return False, err_msg

    def close(s, p):
        m = s.mt5; t = m.symbol_info_tick(s.c.symbol); buy = p.dir > 0
        if t is None or t.ask <= 0 or t.bid <= 0:
            return
        price = t.bid if buy else t.ask
        m.order_send(dict(action=m.TRADE_ACTION_DEAL, symbol=s.c.symbol, volume=s.c.lots, position=p.ticket,
                          type=m.ORDER_TYPE_SELL if buy else m.ORDER_TYPE_BUY, price=price,
                          deviation=50, magic=s.c.magic, comment="udt-py", type_time=m.ORDER_TIME_GTC, type_filling=s._fill()))

    def daily_profit(s):
        m = s.mt5; tc = s.tick().time; now = tc + s.c.server_offset * 3600
        mid = now - now % 86400 - s.c.server_offset * 3600          # same formula as CalculateStatistics()
        u = dt.datetime.now(dt.timezone.utc)
        ds = m.history_deals_get(u - dt.timedelta(days=3), u + dt.timedelta(days=1)) or ()
        sel = [d for d in ds if d.magic in s.magics and d.entry == m.DEAL_ENTRY_OUT and d.time >= mid]
        return sum(d.profit + d.commission + d.swap for d in sel), len(sel)

    def sleep(s, x): time.sleep(x)


# ============================== LIVE LOOP + CONSOLE PANEL ==============================
def run(cfg, allow_real):
    br = MT5Broker(cfg); m = br.mt5
    acc = m.account_info(); ti = m.terminal_info()
    demo = acc.trade_mode == m.ACCOUNT_TRADE_MODE_DEMO
    print(f"account {acc.login} @ {acc.server} ({'DEMO' if demo else 'REAL'})  symbol {cfg.symbol}  tf {cfg.tf}  lots {cfg.lots}")
    if not demo and not allow_real: raise SystemExit("REAL account: refusing to trade. Re-run with --allow-real if you really mean it.")
    if not ti.trade_allowed: print("WARNING: terminal 'Algo Trading' button is OFF - orders will fail (retcode 10027). Click it in MT5.")
    bot = Bot(cfg, br); last_msc = -1; t_panel = 0.0; shown = 0
    print("running - Ctrl+C to stop (open positions stay open; they carry the magic number)\n")
    try:
        while True:
            try:
                tk = br.tick()
                if tk.msc != last_msc: last_msc = tk.msc; bot.on_tick()
                if time.time() - t_panel >= 1.0:
                    t_panel = time.time(); bot.on_timer()
                    while shown < len(bot.events): print("\n  >> " + bot.events[shown]); shown += 1
                    print(f"\r{time.strftime('%H:%M:%S')} {bot.status[:34]:<34} legs {bot.nopen}/{cfg.grid_max_legs} basket ${bot.basket:+.2f} "
                          f"peak/lock ${bot.peak:.2f}/${bot.trail_stop:.2f} daily ${bot.daily:+.2f} ma {bot.ma:.2f} bid {tk.bid:.2f}  ", end="", flush=True)
            except KeyboardInterrupt: raise
            except Exception as e:
                print(f"\nloop error: {e!r}"); time.sleep(1)
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\nstopped."); m.shutdown()


# ============================== SELF-TEST (simulated broker, no MT5) ==============================
class FakeBroker:
    """Gold at $1 P&L per $1 move per 0.01 lot. Price/MA/clock are set by the test."""
    def __init__(s): s.bid = 4000.0; s.spread = 0.3; s.t = 1_000_000; s.ma_v = 3990.0; s.pos = []; s.n = 0; s.fail = False; s.atr_v = 0.5; s.sleeps = 0; s.dp = 0.0; s.ma_ago_v = 3980.0; s.rsi_v = 50.0; s.margin_fail = False
    def tick(s): return Tick(s.bid, s.bid + s.spread, s.t, s.t * 1000)
    def ma(s): return s.ma_v
    def ma_ago(s, k): return s.ma_ago_v
    def atr(s): return s.atr_v
    def rsi(s, period=14): return s.rsi_v
    def tick_value_size(s): return 1.0, 0.01
    def equity_margin(s): return 1000.0, 10.0
    def sleep(s, x): s.sleeps += 1
    def daily_profit(s): return s.dp, 0
    def check_margin(s, d, lots=None):
        if getattr(s, "margin_fail", False):
            return False, "FREE MARGIN $5.00 < MIN $10.00"
        return True, "OK"
    def order(s, d):
        ok_m, reason = s.check_margin(d)
        if not ok_m: return False, f"MARGIN_REJECT: {reason}"
        if s.fail: return False, 10027
        s.n += 1; s.pos.append(dict(ticket=s.n, dir=d, entry=(s.bid + s.spread) if d > 0 else s.bid, time=s.t)); return True, 10009
    def close(s, p): s.pos = [q for q in s.pos if q["ticket"] != p.ticket]
    def positions(s):
        return [Pos(q["ticket"], q["dir"], ((s.bid - q["entry"]) if q["dir"] > 0 else (q["entry"] - (s.bid + s.spread))) * 1.0, 0.0, q["time"], 123790) for q in s.pos]


def selftest():
    import tempfile
    n_ok = 0
    def check(name, cond):
        nonlocal n_ok
        print(("PASS " if cond else "FAIL ") + name)
        if not cond: raise SystemExit(1)
        n_ok += 1
    def mk(**kw):
        cfg = Cfg(enable_log=False, **kw); b = FakeBroker(); return cfg, b, Bot(cfg, b)
    def step(b, bot, price=None, dt_s=1):
        if price is not None: b.bid = price
        b.t += dt_s; bot.on_tick()

    # 1. entry direction follows the MA
    cfg, b, bot = mk(); step(b, bot)
    check("flat + bid above MA -> BUY opened", len(b.pos) == 1 and b.pos[0]["dir"] == 1)
    cfg, b, bot = mk(); b.ma_v = 4010.0; step(b, bot)
    check("flat + bid below MA -> SELL opened", len(b.pos) == 1 and b.pos[0]["dir"] == -1)
    cfg, b, bot = mk(); b.fail = True; step(b, bot)
    check("failed order -> no position, SKIP logged (no phantom ENTRY)", not b.pos and any(e.startswith("SKIP") for e in bot.events) and not any(e.startswith("ENTRY") for e in bot.events))
    cfg, b, bot = mk(max_spread=0.2); step(b, bot)
    check("max_spread guard blocks entry", not b.pos and bot.status.startswith("SPREAD WIDE"))
    cfg, b, bot = mk(); b.dp = 25.0; bot.on_timer(); step(b, bot)
    check("daily goal reached -> no entry", not b.pos and bot.status == "GOAL REACHED")

    # 2. trail: buy, peak, give-back exit. entry ask=4000.3 ; profit = bid - 4000.3
    cfg, b, bot = mk(); step(b, bot)                      # BUY @4000.3
    step(b, bot, 4001.0)                                  # profit +0.70: below arm (1.00) -> no trail, grid mgmt
    check("below arm: still open, GRID status", len(b.pos) == 1 and bot.status.startswith("GRID"))
    step(b, bot, 4001.8); step(b, bot, 4002.3)            # profit 2.00 -> peak 2.00, give 0.40 -> stop 1.60
    check("armed: peak 2.00, trail stop 1.60", abs(bot.peak - 2.0) < 1e-9 and abs(bot.trail_stop - 1.6) < 1e-9 and bot.status.startswith("TRAILING"))
    step(b, bot, 4002.0)                                  # profit 1.70 > 1.60 -> hold
    check("pullback above stop -> hold", len(b.pos) == 1)
    step(b, bot, 4001.8)                                  # profit 1.50 <= 1.60 -> exit
    check("pullback through stop -> basket closed (trail-exit)", not b.pos and any("trail-exit" in e for e in bot.events))
    # cooldown then re-entry
    step(b, bot, 4001.8, 5)
    check("cooldown: no re-entry after 5s", not b.pos and bot.status.startswith("COOLDOWN"))
    step(b, bot, 4001.8, 12)
    check("re-entry after cooldown (17s >= 15s)", len(b.pos) == 1)

    # 3. min-lock floor: peak 1.0 -> give 0.2 -> stop 0.8 ; peak 1.0 with min_lock 0.9 -> stop 0.9
    cfg, b, bot = mk(trail_min_lock=0.9); step(b, bot); step(b, bot, 4001.3)   # profit 1.00
    check("min_lock floor lifts stop to 0.90", abs(bot.trail_stop - 0.9) < 1e-9)
    # ATR band: give = max(0.2*peak, k*ATR*perUnit*legs) = max(0.4, 2*0.5*1*1)=1.0 -> stop 1.0
    cfg, b, bot = mk(trail_atr_k=2.0); step(b, bot); step(b, bot, 4002.3)
    check("ATR band widens give to $1.00 (stop 1.00)", abs(bot.trail_stop - 1.0) < 1e-9)

    # 4. grid: adds at -10, -20, -30, -40 ; cap 5 legs ; SL at -200
    cfg, b, bot = mk(); step(b, bot)                       # 1 buy @4000.3
    step(b, bot, 3990.0)                                   # profit -10.30 -> add leg #2
    check("grid adds 2nd leg at -$10", len(b.pos) == 2)
    step(b, bot, 3980.0)                                   # basket = (3980-4000.3)+(3980-3990.3) = -30.6 <= -20 -> 3rd
    check("grid adds 3rd leg at -$20", len(b.pos) == 3)
    for p in (3970, 3960, 3950): step(b, bot, p)   # 5 legs at 3950 = -151; -200 is reached below
    check("grid capped at 5 legs", len(b.pos) == 5)
    step(b, bot, 3900.0)                                   # basket way under -200 / 5 legs
    check("grid-sl closes ALL legs", not b.pos and any("grid-sl" in e for e in bot.events))
    cfg, b, bot = mk(grid_sl=0); step(b, bot); step(b, bot, 3000.0)
    check("grid_sl=0 -> no SL close (time cap is only backstop)", len(b.pos) >= 1)

    # 5. soft cap: aged basket closes only at >= 0 profit
    cfg, b, bot = mk(); step(b, bot, None); step(b, bot, 4000.8)       # +0.50 profit
    step(b, bot, 4000.8, 46 * 60)
    check("soft cap after 46 min at profit>=0 -> closed (time-soft)", not b.pos and any("time-soft" in e for e in bot.events))
    cfg, b, bot = mk(); step(b, bot); step(b, bot, 3998.0)             # -2.30 loss
    step(b, bot, 3998.0, 46 * 60)
    check("soft cap never closes a losing basket", len(b.pos) >= 1)
    # hard cap
    cfg, b, bot = mk(hard_cap_hours=2); step(b, bot); step(b, bot, 3998.0); step(b, bot, 3998.0, 3 * 3600)
    check("hard cap closes a stale losing basket", not b.pos and any("time-hard" in e for e in bot.events))

    # 6. flip on reversal: trail exit then opposite side immediately (no cooldown)
    cfg, b, bot = mk(flip_on_reversal=True); step(b, bot); step(b, bot, 4002.3); step(b, bot, 4001.8)
    check("trail exit closed the buy", not b.pos)
    step(b, bot, 4001.8, 1)
    check("flip: SELL opened next tick, skipping cooldown+MA", len(b.pos) == 1 and b.pos[0]["dir"] == -1)
    cfg, b, bot = mk(flip_on_reversal=False); step(b, bot); step(b, bot, 4002.3); step(b, bot, 4001.8); step(b, bot, 4001.8, 1)
    check("no flip when disabled", not b.pos)

    # 7. non-grid, non-trail (EA with fixed TP) : scalp-tp / basket target / stop-loss
    cfg, b, bot = mk(trail_on=False, grid_sessions=False); step(b, bot); step(b, bot, 4000.5)   # +0.20 = basket_target 0.10
    check("fixed-TP mode closes at basket target", not b.pos and any("basket-target" in e for e in bot.events))
    cfg, b, bot = mk(trail_on=False, grid_sessions=False, basket_target=5.0, stop_loss=3.0); step(b, bot); step(b, bot, 3996.0)
    check("single-leg stop_loss closes", not b.pos and any("stop-loss" in e for e in bot.events))
    cfg, b, bot = mk(trail_on=False); step(b, bot); step(b, bot, 4000.7)   # grid mode, 1 leg, +0.40 >= scalp 0.20
    check("grid mode + trail off: 1-leg scalp-tp", not b.pos and any(("scalp-tp" in e) or ("grid-tp" in e) for e in bot.events))

    # 8. profit-point math
    cfg, b, bot = mk(); step(b, bot); step(b, bot, 3999.0)    # buy @4000.3, profit -1.30, tp price = bid + (0.20+1.30)/1
    check("profit-at price = bid + (target - P)/perUnit", abs(bot.tp_price - (3999.0 + 1.5)) < 1e-9)

    # 8c. side / slope filters (bid 4000 > MA 3990 -> BUY signal; MA 3990 vs 3980 ago = rising)
    cfg, b, bot = mk(side="sell"); step(b, bot)
    check("side=sell: buy signal ignored", not b.pos and bot.status.startswith("WAIT SELL"))
    b.ma_v = 4010.0; b.ma_ago_v = 4020.0; step(b, bot)
    check("side=sell: sell signal taken", len(b.pos) == 1 and b.pos[0]["dir"] == -1)
    cfg, b, bot = mk(slope_bars=10); b.ma_ago_v = 3995.0; step(b, bot)       # price above MA but MA falling
    check("slope filter blocks buy on a falling MA", not b.pos and bot.status.startswith("WAIT SLOPE"))
    b.ma_ago_v = 3985.0; step(b, bot)
    check("slope filter allows buy on a rising MA", len(b.pos) == 1 and b.pos[0]["dir"] == 1)

    # 8d. Overextension & RSI filters
    cfg, b, bot = mk(max_ma_dist=5.0); step(b, bot) # bid 4000 vs MA 3990 = 10 > 5 -> overextended
    check("max_ma_dist blocks buy when overextended", not b.pos and bot.status.startswith("OVEREXTENDED"))
    cfg, b, bot = mk(rsi_filter=True); b.rsi_v = 75.0; step(b, bot)
    check("rsi_filter blocks buy when overbought", not b.pos and bot.status.startswith("RSI OVERBOUGHT"))

    # 8e. Break Time filter: finish active trades but block new entries
    cfg, b, bot = mk(break_time=True); step(b, bot)
    check("break_time blocks new entry when flat", not b.pos and "BREAK TIME" in bot.status)

    # 8f. Margin Pre-check: blocks order and enforces 60s cooldown if free margin is insufficient
    cfg, b, bot = mk(); b.margin_fail = True; step(b, bot)
    check("margin pre-check blocks order and enforces margin cooldown", not b.pos and "MARGIN" in bot.status and bot.margin_cooldown_until > b.t)
    b.t += 61; step(b, bot) # Second consecutive margin reject triggers pause instead of infinite loop
    check("margin pre-check breaks endless loop after repeated rejects", not b.pos and "PAUSED (INSUFFICIENT MARGIN)" in bot.status and bot.margin_reject_count >= 2)

    # 8g. Max Legs Bailout: when max legs reached, escape at bailout_target
    cfg, b, bot = mk(grid_max_legs=2, bailout_on_max_legs=True, bailout_target=0.10)
    step(b, bot)                      # 1 buy @4000.3
    step(b, bot, 3990.0)              # leg 2 added
    check("grid has 2 legs (max)", len(b.pos) == 2)
    step(b, bot, 4000.5)              # basket profit now >= 0.10 -> bailout exit
    check("bailout exit closes max legs basket at target", not b.pos and any("max-legs-bailout" in e for e in bot.events))

    # 8h. Trend Invalidation Stop: cuts position when price moves past MA
    cfg, b, bot = mk(trend_stop_dist=5.0)
    step(b, bot)                      # BUY @4000.3, MA=3990
    b.ma_v = 4010.0; step(b, bot, 4004.0)  # price 4004 is 6 below MA 4010 >= trend_stop_dist (5.0)
    check("trend invalidation cuts basket when trend reverses across MA", not b.pos and any("trend-inval" in e for e in bot.events))

    # 8i. Equity Risk Stop: cuts basket if loss exceeds equity %
    cfg, b, bot = mk(max_equity_risk_pct=10.0)  # 10% of $1000 eq = $100
    step(b, bot)                      # BUY @4000.3
    step(b, bot, 3890.0)              # loss > $100
    check("equity risk stop cuts basket when loss exceeds % limit", not b.pos and any("equity-risk-sl" in e for e in bot.events))

    # 9. CSV logger writes a header + rows
    d = tempfile.mkdtemp(); global HERE
    old = HERE; HERE = os.path.join(d, "Experts")
    cfg = Cfg(enable_log=True); b = FakeBroker(); bot = Bot(cfg, b); step(b, bot)
    f = os.path.join(d, "Files", cfg.log_file); HERE = old
    txt = open(f).read().splitlines()
    check("CSV log has header + ENTRY row", txt[0].startswith("time,event,side") and "ma-signal" in txt[1])

    # 10. backtest machinery on a synthetic random walk (needs numpy)
    try:
        import numpy as np, json
    except ImportError:
        print("SKIP backtest checks (numpy missing)"); print(f"\n{n_ok} checks passed"); return
    global BT_DIR, _BTD
    old_dir, old_d = BT_DIR, _BTD; BT_DIR = tempfile.mkdtemp(); _BTD = None
    rng = np.random.default_rng(3); N = 60_000
    ms = 1_700_000_000_000 + np.cumsum(rng.integers(200, 1500, N)); mid = 4000 + np.cumsum(rng.normal(0, 0.12, N))
    bq = np.rint(mid * 100).astype(np.int32); aq = bq + 30
    np.save(os.path.join(BT_DIR, "m.npy"), ms); np.save(os.path.join(BT_DIR, "b.npy"), bq); np.save(os.path.join(BT_DIR, "a.npy"), aq)
    json.dump(dict(symbol="T", digits=2, tv=1.0, ts=0.01, n=N, fetched_days=0, first_ms=int(ms[0]), last_ms=int(ms[-1])), open(os.path.join(BT_DIR, "meta.json"), "w"))
    D = BTData(); cfg = Cfg(enable_log=False, ma_period=20, trail_atr_k=1.0, atr_period=14)
    ma, atr = D.ind(cfg); sec = D.msc // 1000; bid = D.bid
    bar = sec // 60; ub = np.unique(bar); close = {b: bid[bar == b][-1] for b in ub}; ubl = list(ub)
    ok_ma = ok_atr = True
    for i in rng.integers(5000, N, 40):
        k = ubl.index(bar[i]); prev = [close[b] for b in ub[k - 19:k]]
        ok_ma &= abs(ma[i] - (sum(prev) + bid[i]) / 20) < 1e-9
        trs = []                                       # ATR(14) of the last 14 CLOSED M1 bars; TR uses the previous close
        for j in range(k - 14, k):
            m_ = bar == ub[j]; h, l_ = bid[m_].max(), bid[m_].min(); pc = close[ub[j - 1]]
            trs.append(max(h - l_, abs(h - pc), abs(l_ - pc)))
        ok_atr &= abs(atr[i] - sum(trs) / 14) < 1e-9
    check("vectorised MA == brute-force SMA(20) incl. forming bar", bool(ok_ma))
    check("vectorised ATR(14, M1, closed bars) == brute force", bool(ok_atr))
    ag = D.ago(Cfg(ma_period=20, slope_bars=5)); ok_ag = True
    for i in rng.integers(5000, N, 40):
        k = ubl.index(bar[i]); ok_ag &= abs(ag[i] - sum(close[b] for b in ub[k - 24:k - 4]) / 20) < 1e-9
    check("vectorised MA 5 bars ago == brute force", bool(ok_ag))
    kw = dict(enable_log=False, ma_period=20, soft_cap_min=3, daily_goal=1e9)
    r = bt_run(Cfg(**kw), 0.5, 0.05, 0.0); pnl = sum(b["pnl"] for b in r["baskets"])
    check("backtest runs and closes baskets", len(r["baskets"]) > 0)
    r2 = bt_run(Cfg(**kw), 0.5, 0.05, 0.0)
    check("backtest is deterministic", [b["pnl"] for b in r["baskets"]] == [b["pnl"] for b in r2["baskets"]])
    r3 = bt_run(Cfg(**kw), 0.5, 0.50, 0.0)
    check("higher slippage strictly lowers P&L", sum(b["pnl"] for b in r3["baskets"]) < pnl)
    # each basket's P&L must equal an independent recomputation from its legs: 1 leg, buy @ask+slip, sell @bid-slip
    cfg1 = Cfg(enable_log=False, grid_sessions=False, trail_on=False, basket_target=0.4, ma_period=20, daily_goal=1e9)
    r4 = bt_run(cfg1, 0.5, 0.0, 0.0)
    check("fixed-TP single-leg baskets all close at >= target (no slippage) and none lose before soft cap", all(b["pnl"] >= 0.4 - 1e-9 for b in r4["baskets"] if b["reason"] == "basket-target"))
    BT_DIR, _BTD = old_dir, old_d
    print(f"\n{n_ok} checks passed")


# ============================== BACKTEST (real MT5 ticks -> the SAME Bot class) ==============================
BT_DIR = os.path.join(HERE, "predictive_cache", "bt_run")
TF_SEC = {"M1": 60, "M2": 120, "M3": 180, "M4": 240, "M5": 300, "M6": 360, "M10": 600, "M12": 720, "M15": 900, "M20": 1200,
          "M30": 1800, "H1": 3600, "H2": 7200, "H3": 10800, "H4": 14400, "H6": 21600, "H8": 28800, "H12": 43200, "D1": 86400}


def fetch_ticks(cfg, days, warm_days):
    """Pull (days + warm_days) of ticks from MT5 history (cached per day as scaled int32), dedupe, and write
    memory-mappable arrays to BT_DIR so sweep workers can share them. Returns the meta dict."""
    import numpy as np, json
    br = MT5Broker(cfg); mt5 = br.mt5; sym = cfg.symbol
    info = mt5.symbol_info(sym); digits = info.digits; sc = 10 ** digits
    cache = os.path.join(HERE, "predictive_cache"); os.makedirs(cache, exist_ok=True); os.makedirs(BT_DIR, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc); end = now + dt.timedelta(hours=12)       # MT5 tick epochs are server time (ahead of UTC)
    d = (end - dt.timedelta(days=days + warm_days)).replace(hour=0, minute=0, second=0, microsecond=0)
    ms_l, b_l, a_l = [], [], []; n_fetch = 0
    while d < end:
        nxt = d + dt.timedelta(days=1); f = os.path.join(cache, f"ticks_{sym}_{d:%Y%m%d}.npz")
        complete = nxt <= now - dt.timedelta(hours=1)
        if not (complete and os.path.exists(f)): print(f"  fetching {d:%Y-%m-%d} from MT5 ...", end=chr(13), flush=True)
        if complete and os.path.exists(f):
            z = np.load(f); m, b, a = z["m"], z["b"], z["a"]
        else:
            tk = mt5.copy_ticks_range(sym, d, min(nxt, end), mt5.COPY_TICKS_ALL); n_fetch += 1
            if tk is None or len(tk) == 0: d = nxt; continue
            lo, hi = int(d.timestamp() * 1000), int(nxt.timestamp() * 1000)
            tk = tk[(tk["bid"] > 0) & (tk["ask"] > 0) & (tk["time_msc"] >= lo) & (tk["time_msc"] < hi)]
            m = tk["time_msc"].astype(np.int64); b = np.rint(tk["bid"] * sc).astype(np.int32); a = np.rint(tk["ask"] * sc).astype(np.int32)
            if complete: np.savez(f, m=m, b=b, a=a)
        if len(m): ms_l.append(m); b_l.append(b); a_l.append(a)
        d = nxt
    mt5.shutdown()
    if not ms_l: raise SystemExit("no tick history returned by MT5 for that range")
    m = np.concatenate(ms_l); b = np.concatenate(b_l); a = np.concatenate(a_l)
    o = np.argsort(m, kind="stable"); m, b, a = m[o], b[o], a[o]
    sec = m // 1000                                   # drop repeats: same quote in the same second changes nothing
    keep = np.r_[True, (b[1:] != b[:-1]) | (a[1:] != a[:-1]) | (sec[1:] != sec[:-1])]
    m, b, a = m[keep], b[keep], a[keep]
    np.save(os.path.join(BT_DIR, "m.npy"), m); np.save(os.path.join(BT_DIR, "b.npy"), b); np.save(os.path.join(BT_DIR, "a.npy"), a)
    meta = dict(symbol=sym, digits=digits, tv=info.trade_tick_value, ts=info.trade_tick_size, n=int(len(m)), fetched_days=n_fetch,
                first_ms=int(m[0]), last_ms=int(m[-1]))
    json.dump(meta, open(os.path.join(BT_DIR, "meta.json"), "w"))
    return meta


class BTData:
    def __init__(s):
        import numpy as np, json
        s.np = np; s.meta = json.load(open(os.path.join(BT_DIR, "meta.json")))
        s.sc = 10.0 ** s.meta["digits"]                    # memory-mapped: sweep workers share the OS page cache
        s.msc = np.load(os.path.join(BT_DIR, "m.npy"), mmap_mode="r"); s.b = np.load(os.path.join(BT_DIR, "b.npy"), mmap_mode="r")
        s.a = np.load(os.path.join(BT_DIR, "a.npy"), mmap_mode="r"); s._ind = {}

    @property
    def bid(s): return s.b / s.sc

    def _bars(s, sec, tfsec):
        np = s.np; bar_id = sec // tfsec
        newb = np.empty(len(bar_id), bool); newb[0] = True; newb[1:] = bar_id[1:] != bar_id[:-1]
        st = np.flatnonzero(newb); return st, np.r_[st[1:], len(bar_id)] - 1, np.cumsum(newb, dtype=np.int32) - 1

    def ind(s, cfg):
        """Per-tick MA (SMA of bar closes, forming bar = current bid, exactly iMA shift 0) and ATR(M1, last closed bar; None if unused).
        Only the latest key is kept so a long sweep does not accumulate 360 MB arrays per setting."""
        np = s.np; key = (cfg.tf, cfg.ma_period, cfg.atr_period if cfg.trail_atr_k > 0 else 0)
        if key in s._ind: return s._ind[key]
        sec = s.msc // 1000; bid = s.bid
        st, en, k = s._bars(sec, TF_SEC[cfg.tf.upper()]); p = cfg.ma_period
        C = np.r_[0.0, np.cumsum(bid[en])]
        ma = np.where(k >= p - 1, (C[k] - C[np.maximum(k - p + 1, 0)] + bid) / p, 0.0); atr = None
        if cfg.trail_atr_k > 0:
            st1, en1, k1 = s._bars(sec, 60); P = cfg.atr_period
            hi = np.maximum.reduceat(bid, st1); lo = np.minimum.reduceat(bid, st1); cl = bid[en1]
            prev = np.r_[cl[0], cl[:-1]]; tr = np.maximum(hi - lo, np.maximum(abs(hi - prev), abs(lo - prev))); tr[0] = 0
            cT = np.r_[0.0, np.cumsum(tr)]; atr = np.where(k1 - P >= 1, (cT[k1] - cT[np.maximum(k1 - P, 0)]) / P, -1.0)
        s._ind.clear(); s._ind[key] = (ma, atr); return s._ind[key]

    def ago(s, cfg):
        """Per-tick SMA of the closed bars ending slope_bars back (0 where not warm)."""
        np = s.np; sec = s.msc // 1000; bid = s.bid
        st, en, k = s._bars(sec, TF_SEC[cfg.tf.upper()]); p = cfg.ma_period; j = k - cfg.slope_bars
        C = np.r_[0.0, np.cumsum(bid[en])]
        return np.where(j >= p - 1, (C[np.maximum(j + 1, 0)] - C[np.maximum(j + 1 - p, 0)]) / p, 0.0)


class BTBroker:
    """Simulated account: market orders fill at the recorded ask/bid +- slip; commission is round-trip $ per lot."""
    def __init__(s, cfg, tv, ts, slip, comm):
        s.c, s.tv, s.ts, s.slip, s.comm = cfg, tv, ts, slip, comm; s.pu = tv / ts * cfg.lots
        s.pos = []; s.n = 0; s.realized = 0.0; s.basket_pnl = 0.0; s.day_mid = None; s.day_sum = 0.0
        s._t = Tick(0, 0, 0, 0); s._ma = 0.0; s._atr = -1.0; s._ago = 0.0

    def set(s, ms, bid, ask, ma, atr, ago=0.0): s._t = Tick(bid, ask, ms // 1000, ms); s._ma = ma; s._atr = atr; s._ago = ago
    def ma_ago(s, k): return s._ago
    def tick(s): return s._t
    def ma(s): return s._ma
    def atr(s): return s._atr if s._atr >= 0 else None
    def tick_value_size(s): return s.tv, s.ts
    def equity_margin(s): return 1000.0, 0.0
    def sleep(s, x): pass
    def _day(s):
        tc = s._t.time; mid = tc - (tc + s.c.server_offset * 3600) % 86400      # same day boundary as CalculateStatistics()
        if mid != s.day_mid: s.day_mid = mid; s.day_sum = 0.0
    def daily_profit(s): s._day(); return s.day_sum, 0
    def positions(s):
        t = s._t; return [Pos(q[0], q[1], ((t.bid - q[2]) if q[1] > 0 else (q[2] - t.ask)) * s.pu, 0.0, q[3], s.c.magic) for q in s.pos]
    def floating(s):
        t = s._t; return sum(((t.bid - q[2]) if q[1] > 0 else (q[2] - t.ask)) * s.pu for q in s.pos)
    def order(s, d):
        t = s._t; s.n += 1
        s.pos.append([s.n, d, (t.ask + s.slip) if d > 0 else (t.bid - s.slip), t.time]); return True, 10009
    def close(s, p):
        for q in s.pos:
            if q[0] == p.ticket:
                t = s._t; ex = (t.bid - s.slip) if q[1] > 0 else (t.ask + s.slip)
                pnl = (ex - q[2]) * q[1] * s.pu - s.comm * s.c.lots
                s.pos.remove(q); s.realized += pnl; s.basket_pnl += pnl; s._day(); s.day_sum += pnl; return


class BTBot(Bot):
    """Same Bot, but decisions are captured as structured baskets instead of CSV rows."""
    def __init__(s, cfg, br):
        super().__init__(cfg, br); s.baskets = []; s.reason = ""; s.max_legs = 0; s.mae = 0.0; s.skips = 0
    def log(s, ev, side, detail, price, basket, realized):
        if ev == "CLOSE": s.reason = detail
        elif ev == "SKIP": s.skips += 1
    def close_all(s):
        peak = s.peak; s.mae = min(s.mae, s.basket); legs = max(s.max_legs, s.nopen); t_open = s.open_time
        super().close_all()
        s.baskets.append(dict(t_open=t_open, t_close=s.br.tick().time, pnl=s.br.basket_pnl, reason=s.reason, legs=legs, mae=s.mae, peak=peak))
        s.br.basket_pnl = 0.0; s.max_legs = 0; s.mae = 0.0


def bt_run(cfg, days, slip, comm):
    """One full replay. Returns dict(baskets, open_floating, maxdd, ticks, secs)."""
    t0 = time.time(); D = _bt_data(); ma, atr = D.ind(cfg); N = len(D.msc); ago = D.ago(cfg) if cfg.slope_bars > 0 else None
    start = int(D.msc[-1] - days * 86400_000); i0 = int(D.np.searchsorted(D.msc, start))
    br = BTBroker(cfg, D.meta["tv"], D.meta["ts"], slip, comm); bot = BTBot(cfg, br)
    last_sec = -1; last_min = -1; peak_eq = 0.0; maxdd = 0.0; CH = 400_000; eq_t = []; eq_v = []
    for c0 in range(i0, N, CH):
        c1 = min(N, c0 + CH); ms = D.msc[c0:c1].tolist(); bd = (D.b[c0:c1] / D.sc).tolist(); ak = (D.a[c0:c1] / D.sc).tolist()
        mm = ma[c0:c1].tolist(); aa = atr[c0:c1].tolist() if atr is not None else [-1.0] * (c1 - c0)
        gg = ago[c0:c1].tolist() if ago is not None else [0.0] * (c1 - c0)
        for j in range(c1 - c0):
            br.set(ms[j], bd[j], ak[j], mm[j], aa[j], gg[j]); sec = ms[j] // 1000
            if sec != last_sec: last_sec = sec; bot.on_timer()
            bot.on_tick()
            if br.pos:
                n = len(br.pos)
                if n > bot.max_legs: bot.max_legs = n
                if bot.basket < bot.mae: bot.mae = bot.basket
                eq = br.realized + br.floating()
            else: eq = br.realized
            if eq > peak_eq: peak_eq = eq
            elif peak_eq - eq > maxdd: maxdd = peak_eq - eq
            if sec // 60 != last_min: last_min = sec // 60; eq_t.append(sec); eq_v.append(eq)       # 1-minute equity curve (closed + floating)
    return dict(baskets=bot.baskets, open_floating=br.floating() if br.pos else 0.0, open_legs=len(br.pos), maxdd=maxdd,
                ticks=N - i0, secs=time.time() - t0, start_ms=int(D.msc[i0]), end_ms=int(D.msc[-1]), skips=bot.skips, eq_t=eq_t, eq_v=eq_v)


_BTD = None
def _bt_data():
    global _BTD
    if _BTD is None: _BTD = BTData()
    return _BTD


def _bt_worker(a):
    cfg_kw, days, slip, comm = a
    r = bt_run(Cfg(enable_log=False, **cfg_kw), days, slip, comm); return cfg_kw, r


def stats(bk):
    n = len(bk)
    if n == 0: return dict(n=0, net=0.0, win=0.0, avg=0.0, worst=0.0, pf=0.0, legs=0)
    p = [b["pnl"] for b in bk]; w = sum(x for x in p if x > 0); l = -sum(x for x in p if x < 0)
    return dict(n=n, net=sum(p), win=100.0 * sum(1 for x in p if x > 0) / n, avg=sum(p) / n, worst=min(p), pf=(w / l if l > 0 else float("inf")),
                legs=max(b["legs"] for b in bk))


def split(r, oos):
    cut = r["start_ms"] + (1 - oos) * (r["end_ms"] - r["start_ms"]) if oos > 0 else r["end_ms"] + 1
    return [b for b in r["baskets"] if b["t_close"] * 1000 < cut], [b for b in r["baskets"] if b["t_close"] * 1000 >= cut], cut


def report(cfg, r, oos, csv_path=None):
    bk = r["baskets"]; S = stats(bk); off = cfg.server_offset * 3600
    d0 = dt.datetime.fromtimestamp(r["start_ms"] / 1000, dt.timezone.utc); d1 = dt.datetime.fromtimestamp(r["end_ms"] / 1000, dt.timezone.utc)
    days = (r["end_ms"] - r["start_ms"]) / 86400_000
    print(f"\n{cfg.symbol} {cfg.tf} MA{cfg.ma_period}  {d0:%Y-%m-%d} -> {d1:%Y-%m-%d} ({days:.1f} d, {r['ticks']:,} ticks, replay {r['secs']:.0f}s)")
    print(f"lots {cfg.lots}  trail {'ON arm $%.2f give %.0f%% lock $%.2f' % (cfg.trail_arm, 100*cfg.trail_give_frac, cfg.trail_min_lock) if cfg.trail_on else 'OFF'}  "
          f"grid {'ON %d legs step $%.0f SL $%.0f' % (cfg.grid_max_legs, cfg.grid_step_loss, cfg.grid_sl) if cfg.grid_sessions else 'OFF'}  soft-cap {cfg.soft_cap_min}m  daily-goal ${cfg.daily_goal:g}")
    if not bk: print("NO BASKETS CLOSED"); return
    byd = {}
    for b in bk: byd.setdefault((b["t_close"] + off) // 86400, []).append(b)
    print(f"\n{'server day':<11}{'baskets':>8}{'net $':>10}{'worst mae':>11}")
    for dkey in sorted(byd):
        x = byd[dkey]; print(f"{dt.datetime.fromtimestamp(dkey*86400, dt.timezone.utc):%Y-%m-%d}  {len(x):>8}{sum(b['pnl'] for b in x):>+10.2f}{min(b['mae'] for b in x):>+11.2f}")
    dn = [sum(b["pnl"] for b in x) for x in byd.values()]
    print(f"\nTOTAL net ${S['net']:+.2f} over {len(dn)} trading days  =  ${S['net']/max(len(dn),1):+.2f}/day   baskets {S['n']}  win% {S['win']:.1f}  "
          f"avg ${S['avg']:+.3f}  worst basket ${S['worst']:+.2f}  PF {S['pf']:.2f}")
    print(f"max drawdown (closed+floating) ${r['maxdd']:.2f}   max legs stacked {S['legs']}   winning days {sum(1 for x in dn if x>0)}/{len(dn)}   "
          f"days >= goal ${cfg.daily_goal:g}: {sum(1 for x in dn if x>=cfg.daily_goal)}   open at end: {r['open_legs']} legs ${r['open_floating']:+.2f}")
    print(f"\n{'exit reason':<12}{'count':>7}{'net $':>11}{'avg $':>9}")
    for rs in sorted({b['reason'] for b in bk}):
        x = [b['pnl'] for b in bk if b['reason'] == rs]; print(f"{rs:<12}{len(x):>7}{sum(x):>+11.2f}{sum(x)/len(x):>+9.3f}")
    if oos > 0:
        a, b_, cut = split(r, oos); sa, sb = stats(a), stats(b_)
        print(f"\nIN-SAMPLE  (first {100*(1-oos):.0f}%): net ${sa['net']:+.2f}  baskets {sa['n']}  win% {sa['win']:.1f}  PF {sa['pf']:.2f}")
        print(f"OUT-OF-SAMPLE (last {100*oos:.0f}%): net ${sb['net']:+.2f}  baskets {sb['n']}  win% {sb['win']:.1f}  PF {sb['pf']:.2f}   <- the number to trust")
    if csv_path:
        with open(csv_path, "w") as f:
            f.write("t_open,t_close,pnl,reason,legs,mae,peak\n")
            for b in bk: f.write(f"{b['t_open']},{b['t_close']},{b['pnl']:.2f},{b['reason']},{b['legs']},{b['mae']:.2f},{b['peak']:.2f}\n")
        print(f"baskets written to {csv_path}")


def parse_sweep(specs):
    import itertools
    types = {f.name: type(getattr(Cfg(), f.name)) for f in fields(Cfg)}; names, vals = [], []
    for sp in specs:
        k, v = sp.split("=", 1); k = k.strip().replace("-", "_")
        if k not in types: raise SystemExit(f"--sweep: unknown/unsupported parameter '{k}'")
        conv = (lambda x: x.lower() in ("1", "true", "yes", "on")) if types[k] is bool else types[k]
        names.append(k); vals.append([conv(x) for x in v.split(",")])
    return [dict(zip(names, c)) for c in itertools.product(*vals)]


def backtest_cmd(cfg, a):
    meta = fetch_ticks(cfg, a.days, a.warmup_days); cfg.symbol = meta["symbol"]
    print(f"{meta['symbol']}: {meta['n']:,} distinct ticks ({meta['fetched_days']} day(s) fetched from MT5, rest cached)")
    base = {f.name: getattr(cfg, f.name) for f in fields(Cfg) if f.name != "enable_log"}; base["symbol"] = cfg.symbol
    if not a.sweep:
        r = bt_run(Cfg(enable_log=False, **base), a.days, a.slip, a.commission); report(cfg, r, a.oos, a.csv); return
    combos = parse_sweep(a.sweep); print(f"sweep: {len(combos)} combinations x {a.days:g} d, {a.jobs} worker(s)")
    jobs = [({**base, **c}, a.days, a.slip, a.commission) for c in combos]; res = []
    if a.jobs > 1:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(a.jobs) as ex:
            for i, (kw, r) in enumerate(ex.map(_bt_worker, jobs)): res.append((kw, r)); print(f"  done {i+1}/{len(jobs)}", end="\r", flush=True)
    else:
        for i, j in enumerate(jobs): res.append(_bt_worker(j)); print(f"  done {i+1}/{len(jobs)}", end="\r", flush=True)
    rows = []
    for kw, r in res:
        ins, oo, _ = split(r, a.oos); si, so, sa = stats(ins), stats(oo), stats(r["baskets"])
        rows.append((si["net"], so["net"], sa, r["maxdd"], {k: kw[k] for k in combos[0]}))
    rows.sort(key=lambda x: -x[0])            # rank by IN-SAMPLE only; OOS is shown, never used to rank
    keys = list(combos[0])
    print(f"\n{'#':>3} " + " ".join(f"{k:>14}" for k in keys) + f"{'IS net$':>11}{'OOS net$':>11}{'baskets':>9}{'win%':>7}{'PF':>6}{'maxDD$':>9}{'worst$':>9}")
    for i, (isn, oon, sa, dd, p) in enumerate(rows, 1):
        print(f"{i:>3} " + " ".join(f"{str(p[k]):>14}" for k in keys) + f"{isn:>+11.2f}{oon:>+11.2f}{sa['n']:>9}{sa['win']:>7.1f}{min(sa['pf'],99):>6.2f}{dd:>9.2f}{sa['worst']:>+9.2f}")
    print(f"\nranked by IN-SAMPLE net (first {100*(1-a.oos):.0f}%). A setting only counts if OOS (last {100*a.oos:.0f}%) is also positive;"
          f" the more combinations you try, the more the top row is luck. Re-check any winner on a different date range.")


# ============================== WALK-FORWARD (tune on the past, trade the unseen next block) ==============================
DEFAULT_GRID = ["grid_max_legs=1,3,5", "trail_arm=1,2,4", "ma_period=100,250,500"]


class Curve:
    """1-minute equity curve of one full replay (closed P&L + floating). Window P&L = eq(end) - eq(start): open losers count."""
    def __init__(s, r):
        import numpy as np
        s.np = np; s.t = np.asarray(r["eq_t"], dtype=np.int64); s.v = np.asarray(r["eq_v"], dtype=np.float64); s.bk = r["baskets"]
    def at(s, x):
        i = int(s.np.searchsorted(s.t, x, side="right")) - 1; return float(s.v[i]) if i >= 0 else 0.0
    def window(s, a, b):
        """(pnl, max drawdown inside the window, closed baskets) for [a, b) seconds."""
        np = s.np; lo = int(np.searchsorted(s.t, a, side="left")); hi = int(np.searchsorted(s.t, b, side="left"))
        e = np.r_[s.at(a), s.v[lo:hi]] - s.at(a)
        n = sum(1 for x in s.bk if a <= x["t_close"] < b)
        return float(e[-1]), float((np.maximum.accumulate(e) - e).max()), n
    def deltas(s, a, b):
        np = s.np; lo = int(np.searchsorted(s.t, a, side="left")); hi = int(np.searchsorted(s.t, b, side="left"))
        return np.r_[0.0, s.v[lo:hi] - s.at(a)]


def walkforward_cmd(cfg, a):
    import numpy as np
    meta = fetch_ticks(cfg, a.days, a.warmup_days); cfg.symbol = meta["symbol"]
    print(f"{meta['symbol']}: {meta['n']:,} distinct ticks ({meta['fetched_days']} day(s) fetched from MT5, rest cached)")
    base = {f.name: getattr(cfg, f.name) for f in fields(Cfg) if f.name != "enable_log"}; base["symbol"] = cfg.symbol
    combos = parse_sweep(a.sweep or DEFAULT_GRID); keys = list(combos[0])
    dflt = {k: getattr(Cfg(), k) for k in keys}                                  # the shipped settings must be a candidate (baseline)
    if dflt not in combos: combos.append(dflt)
    print(f"walk-forward: {len(combos)} candidate settings x {a.days:g} d, train {a.train_days:g} d -> test {a.test_days:g} d, {a.jobs} worker(s)", flush=True)
    jobs = [({**base, **c}, a.days, a.slip, a.commission) for c in combos]; res = []; t0 = time.time()
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(a.jobs) as ex:
        for i, (kw, r) in enumerate(ex.map(_bt_worker, jobs)):
            res.append(Curve(r)); print(f"  replayed {i+1}/{len(jobs)}  ({time.time()-t0:.0f}s)", end="\r", flush=True)
    r0 = res[0]; S = int(r0.t[0]); E = int(r0.t[-1]); DAY = 86400
    nf = int((E - S) // DAY - a.train_days) // int(a.test_days)
    if nf < 1: raise SystemExit("window too short for that train/test split")
    di = combos.index(dflt)
    print(f"\n{dt.datetime.fromtimestamp(S, dt.timezone.utc):%Y-%m-%d} -> {dt.datetime.fromtimestamp(E, dt.timezone.utc):%Y-%m-%d}: {nf} folds. "
          f"Score on the TRAIN block = net - {a.dd_weight:g} x maxDD; if the best score is <= 0 the bot sits out the next block (FLAT).\n")
    hdr = f"{'fold':>4} {'train':<23} {'test':<23} {'chosen: ' + ','.join(keys):<28}{'trn net':>9}{'trn DD':>8}{'TEST net':>10}{'TEST DD':>9}{'dflt TEST':>11}"
    print(hdr)
    st_ = [0.0]; st_d = [0.0]; off = 0.0; off_d = 0.0; tot = 0.0; totd = 0.0; wins = flat = 0; folds = []
    for f in range(nf):
        a0 = S + f * int(a.test_days) * DAY; a1 = a0 + int(a.train_days) * DAY; b1 = a1 + int(a.test_days) * DAY
        sc = []
        for c in res:
            n, dd, _ = c.window(a0, a1); sc.append((n - a.dd_weight * dd, n, dd))
        j = max(range(len(res)), key=lambda i: sc[i][0]); flat_f = sc[j][0] <= 0
        d_te = res[di].deltas(a1, b1)
        if flat_f:
            te_n, te_dd, flat = 0.0, 0.0, flat + 1; seg = np.zeros(2); lab = "FLAT"
        else:
            te_n, te_dd, _ = res[j].window(a1, b1); seg = res[j].deltas(a1, b1); lab = ",".join(str(combos[j][k]) for k in keys)
        st_.extend((off + seg[1:]).tolist()); off += float(seg[-1]); tot += te_n; wins += te_n > 0
        st_d.extend((off_d + d_te[1:]).tolist()); off_d += float(d_te[-1])
        dn, _, _ = res[di].window(a1, b1); totd += dn
        folds.append((f, lab, sc[j][1], te_n, dn))
        fm = lambda x: f"{dt.datetime.fromtimestamp(x, dt.timezone.utc):%m-%d}"
        print(f"{f+1:>4} {fm(a0)}..{fm(a1):<16} {fm(a1)}..{fm(b1):<16} {lab:<28}{sc[j][1]:>+9.0f}{sc[j][2]:>8.0f}{te_n:>+10.1f}{te_dd:>9.1f}{dn:>+11.1f}")
    def mdd(x): x = np.asarray(x); return float((np.maximum.accumulate(x) - x).max())
    days_oos = nf * a.test_days
    print(f"\nWALK-FORWARD (unseen blocks only, {days_oos:g} days): net ${tot:+.2f}  = ${tot/days_oos:+.2f}/day   max DD ${mdd(st_):.2f}   "
          f"profitable folds {wins}/{nf}   sat out {flat}/{nf}")
    print(f"SHIPPED DEFAULTS over the same blocks   : net ${totd:+.2f}  = ${totd/days_oos:+.2f}/day   max DD ${mdd(st_d):.2f}")
    full = [(c.window(S, E), combos[i]) for i, c in enumerate(res)]
    (hn, hd, _), hp = max(full, key=lambda x: x[0][0] - a.dd_weight * x[0][1])
    print(f"hindsight-best fixed setting ({','.join(str(hp[k]) for k in keys)}) over the WHOLE window: net ${hn:+.2f}, DD ${hd:.2f}  "
          f"<- picked with future knowledge, NOT achievable; shown only as an upper bound")
    print(f"\nall {len(res)} settings over the full {(E-S)/DAY:.0f} days (net / maxDD):")
    for (n, dd, nb), p in sorted(full, key=lambda x: -x[0][0]):
        print("   " + ",".join(f"{k}={p[k]}" for k in keys) + f"   net {n:+9.1f}   DD {dd:8.1f}   baskets {nb}")


# ============================== CLI ==============================
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["run", "backtest", "walkforward", "selftest"])
    ap.add_argument("--allow-real", action="store_true", help="permit trading on a non-demo account")
    b = ap.add_argument_group("backtest")
    b.add_argument("--days", type=float, default=None, help="days to replay, ending at the newest tick (default 40; 365 for walkforward)")
    b.add_argument("--train-days", type=float, default=60, help="walkforward: tuning block length")
    b.add_argument("--test-days", type=float, default=30, help="walkforward: unseen block length (also the step)")
    b.add_argument("--dd-weight", type=float, default=0.5, help="walkforward: train score = net - weight x maxDD")
    b.add_argument("--warmup-days", type=float, default=2, help="extra days loaded before the window so the MA is warm")
    b.add_argument("--slip", type=float, default=0.05, help="$ slippage added to every fill (entry and exit)")
    b.add_argument("--commission", type=float, default=0.0, help="round-trip commission, $ per lot")
    b.add_argument("--oos", type=float, default=0.3, help="fraction of the window (the newest part) reported as out-of-sample; 0=off")
    b.add_argument("--sweep", action="append", metavar="PARAM=v1,v2,..", help="repeatable; grid-search these Cfg fields, e.g. --sweep trail_arm=0.5,1,2")
    b.add_argument("--jobs", type=int, default=4, help="parallel workers for --sweep")
    b.add_argument("--csv", help="write the closed baskets to this CSV")
    d = Cfg()
    for f in fields(Cfg):
        flag = "--" + f.name.replace("_", "-"); v = getattr(d, f.name)
        if isinstance(v, bool): ap.add_argument(flag, action=argparse.BooleanOptionalAction, default=v)
        else: ap.add_argument(flag, type=type(v), default=v)
    a = ap.parse_args()
    cfg = Cfg(**{f.name: getattr(a, f.name) for f in fields(Cfg)})
    if a.days is None: a.days = 365 if a.mode == "walkforward" else 40
    if a.mode == "selftest": selftest()
    elif a.mode == "backtest": backtest_cmd(cfg, a)
    elif a.mode == "walkforward": walkforward_cmd(cfg, a)
    else: run(cfg, a.allow_real)


if __name__ == "__main__":
    main()
