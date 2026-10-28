"""
web_app.py - Real-Time Web Dashboard for Vantage XAUUSD Trading Bot
Runs locally on http://localhost:8000 with real-time WebSockets, live charts,
parameter tuning, and manual safety controls.
"""
import asyncio
import collections
import dataclasses
import datetime as dt
import json
import logging
import os
import re
import sys
import threading
import time
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# Import bot and broker components from the existing script
import up_down_tracker_win_bot_xauusd as bot_module
from up_down_tracker_win_bot_xauusd import Cfg, Bot, MT5Broker, Pos, Tick

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(HERE, "templates")
STATIC_DIR = os.path.join(HERE, "static")
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("web_bot")

app = FastAPI(title="Vantage XAUUSD Bot Dashboard")


def format_mt5_time(epoch_seconds: int, server_offset_hours: float = 2.0) -> Dict[str, str]:
    """
    Converts MT5 broker server timestamps (which represent broker server wall-clock time)
    into true Local IST time (India Standard Time, UTC+5:30) as well as displaying
    the original MT5 server time for desktop cross-referencing.
    """
    if not epoch_seconds or epoch_seconds <= 0:
        return {
            "local": "---",
            "server": "---",
            "full": "---"
        }
    dt_server = dt.datetime.utcfromtimestamp(epoch_seconds)
    # Subtract broker server UTC offset to get true UTC
    dt_utc = dt_server - dt.timedelta(hours=server_offset_hours)
    # Convert true UTC to machine local timezone (IST, UTC+5:30)
    dt_local = dt_utc.replace(tzinfo=dt.timezone.utc).astimezone()

    tz_name = dt_local.strftime("%Z")
    if not tz_name or tz_name.startswith("+") or tz_name.startswith("-"):
        tz_offset = dt_local.strftime("%z")
        tz_name = f"UTC{tz_offset[:3]}:{tz_offset[3:]}" if len(tz_offset) >= 5 else (tz_offset or "IST")
    elif "India" in tz_name:
        tz_name = "IST"

    local_str = dt_local.strftime("%H:%M:%S") + f" {tz_name}"
    server_str = dt_server.strftime("%H:%M:%S") + " Server"

    return {
        "local": local_str,
        "server": server_str,
        "full": f"{local_str} ({server_str})"
    }


def format_local_tz(epoch_seconds: int, server_offset_hours: float = 2.0) -> str:
    return format_mt5_time(epoch_seconds, server_offset_hours)["local"]


def format_duration(sec: int) -> str:
    sec = max(0, int(sec))
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}h {m}m"
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


def compute_entry_telemetry(
    bid: float,
    ma: float,
    max_dist: float = 0.0,
    side: str = "both",
    entry_mode: str = "classic",
    pullback_zone: float = 3.0,
    pullback_rejection_dist: float = 0.6,
    rsi: float = 50.0,
    rsi_filter: bool = True,
    rsi_ob: float = 70.0,
    rsi_os: float = 30.0,
) -> Dict[str, Any]:
    max_dist = float(max_dist or 0.0)
    side = (side or "both").lower()
    entry_mode = (entry_mode or "classic").lower()
    pullback_zone = float(pullback_zone or 3.0)
    pullback_rejection_dist = float(pullback_rejection_dist or 0.6)
    rsi = float(rsi or 50.0)
    rsi_ob = float(rsi_ob or 70.0)
    rsi_os = float(rsi_os or 30.0)

    # RSI state: strictly oscillator boundaries (do not use directional labels like BULLISH/BEARISH)
    rsi_status = "NORMAL"
    if rsi >= rsi_ob:
        rsi_status = "OVERBOUGHT"
    elif rsi <= rsi_os:
        rsi_status = "OVERSOLD"

    if ma <= 0 or bid <= 0:
        return {
            "current_ma": round(ma, 2),
            "dist_ma": 0.0,
            "max_ma_dist": round(max_dist, 2),
            "entry_mode": entry_mode,
            "side": side,
            "target_entry_price": 0.0,
            "target_entry_desc": "Calculating MA...",
            "buy_target_price": 0.0,
            "buy_target_desc": "Calculating MA...",
            "buy_ready": False,
            "sell_target_price": 0.0,
            "sell_target_desc": "Calculating MA...",
            "sell_ready": False,
            "in_entry_zone": False,
            "action_side": "NONE",
            "rsi": round(rsi, 1),
            "rsi_status": rsi_status,
            "rsi_ob": round(rsi_ob, 1),
            "rsi_os": round(rsi_os, 1),
        }

    dist = abs(bid - ma)

    # 1. COMPUTE BUY TELEMETRY
    if entry_mode == "pullback":
        if bid >= ma:
            if dist <= pullback_zone:
                buy_price = round(bid, 2)
                buy_desc = f"Dip Zone (Wait +${pullback_rejection_dist:.2f} Bounce)"
                buy_ready = True
            else:
                target_buy = ma + pullback_zone
                dip_needed = bid - target_buy
                buy_price = round(target_buy, 2)
                buy_desc = f"<= {target_buy:.2f} (Dip -${dip_needed:.2f})"
                buy_ready = False
        else:
            rise_needed = ma - bid
            buy_price = round(ma, 2)
            buy_desc = f"> {ma:.2f} (Rise +${rise_needed:.2f} to Bull Zone)"
            buy_ready = False
    else:  # classic
        if max_dist > 0:
            upper_limit = ma + max_dist
            if bid > upper_limit:
                diff = bid - upper_limit
                buy_price = round(upper_limit, 2)
                buy_desc = f"<= {upper_limit:.2f} (Drop -${diff:.2f})"
                buy_ready = False
            elif bid < ma:
                diff = ma - bid
                buy_price = round(ma, 2)
                buy_desc = f"> {ma:.2f} (Rise +${diff:.2f})"
                buy_ready = False
            else:
                buy_price = round(upper_limit, 2)
                buy_desc = f"In Zone (<= {upper_limit:.2f}) - Ready"
                buy_ready = True
        else:
            if bid > ma:
                buy_price = round(ma, 2)
                buy_desc = f"In Zone (> {ma:.2f}) - Ready"
                buy_ready = True
            else:
                diff = ma - bid
                buy_price = round(ma, 2)
                buy_desc = f"> {ma:.2f} (Rise +${diff:.2f})"
                buy_ready = False

    # 2. COMPUTE SELL TELEMETRY
    if entry_mode == "pullback":
        if bid <= ma:
            if dist <= pullback_zone:
                sell_price = round(bid, 2)
                sell_desc = f"Rally Zone (Wait -${pullback_rejection_dist:.2f} Rejection)"
                sell_ready = True
            else:
                target_sell = ma - pullback_zone
                rally_needed = target_sell - bid
                sell_price = round(target_sell, 2)
                sell_desc = f">= {target_sell:.2f} (Rally +${rally_needed:.2f})"
                sell_ready = False
        else:
            drop_needed = bid - ma
            sell_price = round(ma, 2)
            sell_desc = f"< {ma:.2f} (Drop -${drop_needed:.2f} to Bear Zone)"
            sell_ready = False
    else:  # classic
        if max_dist > 0:
            lower_limit = ma - max_dist
            if bid < lower_limit:
                diff = lower_limit - bid
                sell_price = round(lower_limit, 2)
                sell_desc = f">= {lower_limit:.2f} (Rise +${diff:.2f})"
                sell_ready = False
            elif bid > ma:
                diff = bid - ma
                sell_price = round(ma, 2)
                sell_desc = f"< {ma:.2f} (Drop -${diff:.2f})"
                sell_ready = False
            else:
                sell_price = round(lower_limit, 2)
                sell_desc = f"In Zone (>= {lower_limit:.2f}) - Ready"
                sell_ready = True
        else:
            if bid < ma:
                sell_price = round(ma, 2)
                sell_desc = f"In Zone (< {ma:.2f}) - Ready"
                sell_ready = True
            else:
                diff = bid - ma
                sell_price = round(ma, 2)
                sell_desc = f"< {ma:.2f} (Drop -${diff:.2f})"
                sell_ready = False

    # 3. SYNTHESIZE FOR CONFIGURED DIRECTION BIAS
    if side == "buy":
        in_entry_zone = buy_ready
        action_side = "BUY"
        target_entry_price = buy_price
        target_entry_desc = f"BUY: {buy_desc}"
    elif side == "sell":
        in_entry_zone = sell_ready
        action_side = "SELL"
        target_entry_price = sell_price
        target_entry_desc = f"SELL: {sell_desc}"
    else:  # "both"
        in_entry_zone = bool(buy_ready or sell_ready)
        if buy_ready and not sell_ready:
            action_side = "BUY"
            target_entry_price = buy_price
        elif sell_ready and not buy_ready:
            action_side = "SELL"
            target_entry_price = sell_price
        else:
            action_side = "BOTH"
            target_entry_price = buy_price if bid >= ma else sell_price
        target_entry_desc = f"BUY: {buy_desc}  |  SELL: {sell_desc}"

    return {
        "current_ma": round(ma, 2),
        "dist_ma": round(dist, 2),
        "max_ma_dist": round(max_dist, 2),
        "entry_mode": entry_mode,
        "side": side,
        "target_entry_price": round(target_entry_price, 2),
        "target_entry_desc": target_entry_desc,
        "buy_target_price": round(buy_price, 2),
        "buy_target_desc": buy_desc,
        "buy_ready": buy_ready,
        "sell_target_price": round(sell_price, 2),
        "sell_target_desc": sell_desc,
        "sell_ready": sell_ready,
        "in_entry_zone": in_entry_zone,
        "action_side": action_side,
        "rsi": round(rsi, 1),
        "rsi_status": rsi_status,
        "rsi_ob": round(rsi_ob, 1),
        "rsi_os": round(rsi_os, 1),
    }


CONFIG_FILE = os.path.join(HERE, "bot_config.json")
SAVED_ACCOUNTS_FILE = os.path.join(HERE, "saved_accounts.json")


def load_saved_accounts() -> Dict[str, Any]:
    if not os.path.exists(SAVED_ACCOUNTS_FILE):
        return {}
    try:
        with open(SAVED_ACCOUNTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_saved_accounts(accounts: Dict[str, Any]):
    try:
        with open(SAVED_ACCOUNTS_FILE, "w", encoding="utf-8") as f:
            json.dump(accounts, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save accounts: {e}")


class BotManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.cfg = Cfg()
        self.load_persisted_config()
        self.broker: Optional[MT5Broker] = None
        self.bot: Optional[Bot] = None
        self.is_running: bool = False
        self.allow_real: bool = False
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.events = collections.deque(maxlen=150)
        self.pnl_history = collections.deque(maxlen=120)  # 2 hours of 1-minute points
        self.last_history_min = -1
        self.error_msg: str = ""
        self.last_tick: Optional[Dict[str, Any]] = None
        self.account_info: Optional[Dict[str, Any]] = None
        self.positions_list: List[Dict[str, Any]] = []
        self.closed_positions_list: List[Dict[str, Any]] = []
        self.available_symbols: List[str] = []
        self.last_tick_msc: int = -1
        self.last_tick_arrival: float = 0.0
        self.is_market_live: bool = False
        self.live_ma: float = 0.0
        self.live_rsi: float = 50.0

    def load_persisted_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for k, v in data.items():
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
                        setattr(self.cfg, k, val)
                logger.info(f"Loaded persisted config: symbol={self.cfg.symbol}, lots={self.cfg.lots}")
            except Exception as e:
                logger.error(f"Failed to load persisted config: {e}")

    def get_server_offset(self) -> float:
        """
        Computes the MT5 broker server's timezone offset from UTC in hours.
        Broker servers (e.g. MetaQuotes, Vantage) almost universally run on EET (UTC+2 or UTC+3).
        """
        try:
            sym = self.cfg.symbol or "XAUUSD"
            tick = mt5.symbol_info_tick(sym)
            if tick and tick.time > 0:
                server_dt = dt.datetime.utcfromtimestamp(tick.time)
                host_utc = dt.datetime.utcnow()
                diff_sec = (server_dt - host_utc).total_seconds()
                return round(diff_sec / 1800.0) * 0.5
        except Exception:
            pass
        return 2.0  # Fallback default: UTC+2 (EET)

    def save_persisted_config(self):
        try:
            cfg_dict = {f.name: getattr(self.cfg, f.name) for f in dataclasses.fields(Cfg)}
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg_dict, f, indent=2)
            logger.info("Saved persisted config to bot_config.json")
        except Exception as e:
            logger.error(f"Failed to save persisted config: {e}")

    def get_available_accounts(self) -> List[Dict[str, Any]]:
        """Pull active, saved, and log-discovered accounts from MetaTrader 5."""
        accounts: Dict[int, Dict[str, Any]] = {}
        saved = load_saved_accounts()

        # 1. Populated saved accounts
        for k, v in saved.items():
            try:
                l_num = int(k)
                t_mode = v.get("trade_mode", "DEMO")
                if t_mode == 0:
                    t_mode = "DEMO"
                elif t_mode == 1:
                    t_mode = "REAL"
                accounts[l_num] = {
                    "login": l_num,
                    "server": v.get("server", ""),
                    "name": v.get("name", ""),
                    "trade_mode": str(t_mode).upper(),
                    "balance": float(v.get("balance", 0.0)),
                    "equity": float(v.get("equity", 0.0)),
                    "currency": v.get("currency", "USD"),
                    "has_password": bool(v.get("password")),
                    "active": False,
                    "source": "saved",
                }
            except Exception:
                pass

        # 2. Add current active account from MT5
        active_login = None
        if self.account_info and self.account_info.get("login"):
            try:
                active_login = int(self.account_info["login"])
                t_mode = self.account_info.get("trade_mode", "DEMO")
                if t_mode == 0:
                    t_mode = "DEMO"
                elif t_mode == 1:
                    t_mode = "REAL"
                accounts[active_login] = {
                    "login": active_login,
                    "server": self.account_info.get("server", ""),
                    "name": self.account_info.get("name", ""),
                    "trade_mode": str(t_mode).upper(),
                    "balance": float(self.account_info.get("balance", 0.0)),
                    "equity": float(self.account_info.get("equity", 0.0)),
                    "currency": self.account_info.get("currency", "USD"),
                    "has_password": bool(saved.get(str(active_login), {}).get("password")),
                    "active": True,
                    "source": "active",
                }
            except Exception:
                pass

        # 3. Scan MT5 terminal logs for any other authorized accounts
        try:
            import MetaTrader5 as mt5
            ti = mt5.terminal_info()
            if ti and ti.data_path:
                log_dir = os.path.join(ti.data_path, "logs")
                if os.path.exists(log_dir):
                    for fname in sorted(os.listdir(log_dir), reverse=True)[:5]:
                        if fname.endswith(".log") and fname != "metaeditor.log":
                            with open(os.path.join(log_dir, fname), "r", encoding="utf-16le", errors="ignore") as f:
                                for line in f:
                                    m = re.search(r"'(\d+)':\s+authorized on\s+([^\s\(\)]+)", line)
                                    if m:
                                        l_int = int(m.group(1))
                                        s_str = m.group(2).strip()
                                        if l_int not in accounts:
                                            accounts[l_int] = {
                                                "login": l_int,
                                                "server": s_str,
                                                "name": "",
                                                "trade_mode": "DEMO" if "demo" in s_str.lower() else "REAL",
                                                "balance": 0.0,
                                                "equity": 0.0,
                                                "currency": "USD",
                                                "has_password": bool(saved.get(str(l_int), {}).get("password")),
                                                "active": (l_int == active_login),
                                                "source": "terminal",
                                            }
        except Exception:
            pass

        result = list(accounts.values())
        result.sort(key=lambda x: (not x["active"], str(x["login"])))
        return result

    def get_mt5_account_and_market(self):
        """Poll MT5 for account info, market tick, and positions without trading."""
        try:
            import MetaTrader5 as mt5
            # 1. Attach directly if an MT5 terminal is already open (don't force re-login!)
            initialized = False
            try:
                initialized = mt5.initialize()
            except Exception:
                pass

            if not initialized:
                # 2. If not running, fall back to launch via .env credentials
                if not mt5.initialize(**bot_module.mt5_env()):
                    self.error_msg = f"MT5 initialize failed: {mt5.last_error()}"
                    return

            self.error_msg = ""
            acc = mt5.account_info()
            ti = mt5.terminal_info()
            if acc:
                self.account_info = {
                    "login": acc.login,
                    "server": acc.server,
                    "name": acc.name,
                    "trade_mode": "DEMO" if acc.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO else "REAL",
                    "balance": float(acc.balance),
                    "equity": float(acc.equity),
                    "margin": float(acc.margin),
                    "free_margin": float(acc.margin_free),
                    "margin_level": float(acc.margin_level or 0.0),
                    "leverage": int(acc.leverage or 100),
                    "currency": acc.currency,
                    "algo_trading_allowed": bool(ti.trade_allowed) if ti else False,
                }
                # Sync into saved_accounts
                try:
                    s_accs = load_saved_accounts()
                    l_str = str(acc.login)
                    rec = s_accs.get(l_str, {})
                    rec.update({
                        "login": acc.login,
                        "server": acc.server,
                        "name": acc.name,
                        "trade_mode": "DEMO" if acc.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO else "REAL",
                        "balance": float(acc.balance),
                        "equity": float(acc.equity),
                        "currency": acc.currency,
                        "last_seen": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    s_accs[l_str] = rec
                    save_saved_accounts(s_accs)
                except Exception:
                    pass

            sym = self.cfg.symbol
            mt5.symbol_select(sym, True)
            tk = mt5.symbol_info_tick(sym)
            info = mt5.symbol_info(sym)
            cs = float(info.trade_contract_size) if (info and info.trade_contract_size > 0) else (100000.0 if ("USD" in sym and "XAU" not in sym and "GOLD" not in sym) else 100.0)

            if tk and tk.bid > 0 and tk.ask > 0:
                if tk.time_msc != self.last_tick_msc:
                    self.last_tick_msc = tk.time_msc
                    self.last_tick_arrival = time.time()

                now_utc_ts = dt.datetime.now(dt.timezone.utc).timestamp()
                server_offset_sec = self.cfg.server_offset * 3600
                approx_server_now = now_utc_ts + server_offset_sec
                tick_age = approx_server_now - tk.time
                trade_mode = getattr(info, "trade_mode", 4) if info else 4

                is_live = False
                if trade_mode == mt5.SYMBOL_TRADE_MODE_FULL:
                    # Live if a new tick arrived recently (< 60s) or quote age is within 10 mins (600s)
                    if (time.time() - self.last_tick_arrival < 60) or (0 <= tick_age < 600):
                        is_live = True

                self.is_market_live = is_live
                self.last_tick = {
                    "bid": float(tk.bid),
                    "ask": float(tk.ask),
                    "spread": round(float(tk.ask - tk.bid), 2),
                    "contract_size": cs,
                    "time": int(tk.time),
                    "is_live": is_live,
                    "tick_age_sec": max(0, int(tick_age)),
                }
            else:
                self.is_market_live = False
                if tk:
                    self.last_tick = {
                        "bid": float(tk.bid or 0.0),
                        "ask": float(tk.ask or 0.0),
                        "spread": 0.0,
                        "contract_size": cs,
                        "time": int(tk.time or 0),
                        "is_live": False,
                        "tick_age_sec": 999999,
                    }

            # Sync or calculate live MA and RSI
            if self.bot and getattr(self.bot, "ma", 0.0) > 0:
                self.live_ma = float(self.bot.ma)
                self.live_rsi = float(getattr(self.bot, "rsi", 50.0))
            else:
                try:
                    tf_attr = "TIMEFRAME_" + self.cfg.tf.upper()
                    tf_val = getattr(mt5, tf_attr, mt5.TIMEFRAME_M1)
                    r = mt5.copy_rates_from_pos(sym, tf_val, 0, self.cfg.ma_period)
                    if r is not None and len(r) >= self.cfg.ma_period:
                        self.live_ma = float(sum(r["close"]) / len(r["close"]))

                    period = self.cfg.rsi_period
                    rr = mt5.copy_rates_from_pos(sym, tf_val, 1, period + 2)
                    if rr is not None and len(rr) >= period + 1:
                        diffs = [float(rr["close"][i] - rr["close"][i - 1]) for i in range(1, len(rr))]
                        gains = [d for d in diffs[-period:] if d > 0]
                        losses = [-d for d in diffs[-period:] if d < 0]
                        avg_g = sum(gains) / period if gains else 0.0
                        avg_l = sum(losses) / period if losses else 0.0
                        if avg_l == 0:
                            self.live_rsi = 100.0 if avg_g > 0 else 50.0
                        else:
                            rs = avg_g / avg_l
                            self.live_rsi = float(100.0 - (100.0 / (1.0 + rs)))
                except Exception:
                    pass

            # Fetch broker trading symbols list once or when empty
            if not self.available_symbols:
                all_s = mt5.symbols_get()
                if all_s:
                    vis = [s.name for s in all_s if s.visible]
                    tradeable = [s.name for s in all_s if s.trade_mode != mt5.SYMBOL_TRADE_MODE_DISABLED]
                    seen = set()
                    sym_list = []
                    for name in vis + sorted(tradeable):
                        if name not in seen:
                            seen.add(name)
                            sym_list.append(name)
                    self.available_symbols = sym_list

            server_offset = self.get_server_offset()
            server_now_dt = dt.datetime.utcnow() + dt.timedelta(hours=server_offset)
            server_now_ts = int(server_now_dt.replace(tzinfo=dt.timezone.utc).timestamp())

            magics = {self.cfg.magic, self.cfg.magic_recovery}
            raw_pos = mt5.positions_get() or ()  # Fetch ALL open positions across all symbols
            pos_data = []
            for p in raw_pos:
                is_bot = p.magic in magics
                open_ts = int(p.time)
                age_sec = max(0, server_now_ts - open_ts) if open_ts > 0 else 0
                t_open = format_mt5_time(open_ts, server_offset)
                pos_data.append({
                    "ticket": p.ticket,
                    "symbol": p.symbol,
                    "type": "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL",
                    "volume": float(p.volume),
                    "price_open": float(p.price_open),
                    "price_current": float(p.price_current),
                    "profit": round(float(p.profit), 2),
                    "swap": round(float(p.swap), 2),
                    "time": t_open["local"],
                    "time_open": t_open["local"],
                    "time_open_server": t_open["server"],
                    "duration": format_duration(age_sec),
                    "magic": p.magic,
                    "is_bot": is_bot,
                    "origin": "REC" if p.magic == self.cfg.magic_recovery else ("B" if is_bot else "U"),
                })
            self.positions_list = pos_data

            # Fetch closed deals / trades for past 48 hours to guarantee full session coverage across timezones
            now_dt = dt.datetime.now()
            start_dt = now_dt - dt.timedelta(days=2)
            end_dt = now_dt + dt.timedelta(days=1)
            deals = mt5.history_deals_get(start_dt, end_dt) or ()
            ins = {d.position_id: d for d in deals if d.entry == 0}
            outs = [d for d in deals if d.entry == 1]
            closed_data = []
            for out in reversed(outs):
                in_d = ins.get(out.position_id)
                pos_type = "BUY" if in_d and in_d.type == 0 else ("SELL" if in_d and in_d.type == 1 else ("BUY" if out.type == 1 else "SELL"))
                open_p = float(in_d.price) if in_d else 0.0
                is_b = bool(out.magic in magics or out.magic > 0)
                in_time = int(in_d.time) if in_d else 0
                out_time = int(out.time)
                duration_sec = max(0, out_time - in_time) if in_time > 0 else 0
                t_in = format_mt5_time(in_time, server_offset)
                t_out = format_mt5_time(out_time, server_offset)
                closed_data.append({
                    "ticket": out.position_id,
                    "type": pos_type,
                    "volume": float(out.volume),
                    "price_open": open_p,
                    "price_close": float(out.price),
                    "profit": round(float(out.profit + out.swap + out.commission), 2),
                    "time_open": t_in["local"],
                    "time_open_server": t_in["server"],
                    "time_close": t_out["local"],
                    "time_close_server": t_out["server"],
                    "time": t_out["local"],
                    "duration": format_duration(duration_sec),
                    "magic": out.magic,
                    "is_bot": is_b,
                    "origin": "B" if is_b else "U",
                })
            self.closed_positions_list = closed_data

        except Exception as e:
            self.error_msg = str(e)

    def start(self, allow_real: bool = False) -> Dict[str, Any]:
        with self.lock:
            if self.is_running:
                return {"status": "error", "message": "Bot is already running."}

            self.allow_real = allow_real
            try:
                self.broker = MT5Broker(self.cfg)
                m = self.broker.mt5
                acc = m.account_info()
                is_demo = acc.trade_mode == m.ACCOUNT_TRADE_MODE_DEMO

                if not is_demo and not self.allow_real:
                    return {
                        "status": "error",
                        "message": "REAL account detected. Toggle 'Allow Real Account' switch to trade live.",
                    }

                ti = m.terminal_info()
                if ti and not ti.trade_allowed:
                    return {
                        "status": "error",
                        "message": "Terminal 'Algo Trading' is OFF in MT5. Please click the Algo Trading button in MT5's top toolbar.",
                    }

                self.bot = Bot(self.cfg, self.broker)
                # Intercept bot.log to forward to web events
                orig_log = self.bot.log

                def intercepted_log(ev, side, detail, price, basket, realized):
                    orig_log(ev, side, detail, price, basket, realized)
                    time_str = dt.datetime.now().strftime("%H:%M:%S")
                    msg = f"[{time_str}] {ev} {side} {detail} (Price: {price:.2f}, Basket: ${basket:.2f})"
                    self.events.append({"time": time_str, "event": ev, "side": side, "detail": detail, "price": price, "basket": basket, "message": msg})

                self.bot.log = intercepted_log

                self.stop_event.clear()
                self.is_running = True
                self.thread = threading.Thread(target=self._run_loop, daemon=True)
                self.thread.start()
                self.events.append({
                    "time": dt.datetime.now().strftime("%H:%M:%S"),
                    "event": "SYSTEM",
                    "side": "-",
                    "detail": "BOT STARTED",
                    "price": 0.0,
                    "basket": 0.0,
                    "message": f"[{dt.datetime.now().strftime('%H:%M:%S')}] SYSTEM: Trading engine started ({'REAL' if not is_demo else 'DEMO'})",
                })
                return {"status": "ok", "message": "Bot started successfully."}
            except BaseException as e:
                self.is_running = False
                self.error_msg = str(e)
                return {"status": "error", "message": f"Failed to start bot: {e}"}

    def stop(self) -> Dict[str, Any]:
        with self.lock:
            if not self.is_running:
                return {"status": "ok", "message": "Bot is not running."}
            self.stop_event.set()
            self.is_running = False
            self.events.append({
                "time": dt.datetime.now().strftime("%H:%M:%S"),
                "event": "SYSTEM",
                "side": "-",
                "detail": "BOT STOPPED",
                "price": 0.0,
                "basket": 0.0,
                "message": f"[{dt.datetime.now().strftime('%H:%M:%S')}] SYSTEM: Trading engine stopped by user.",
            })
            return {"status": "ok", "message": "Bot stopped."}

    def set_symbol(self, symbol: str) -> Dict[str, Any]:
        with self.lock:
            if self.is_running:
                return {"status": "error", "message": "Please stop the bot before switching the active symbol."}
            try:
                import MetaTrader5 as mt5
                if not mt5.initialize(**bot_module.mt5_env()):
                    return {"status": "error", "message": "MT5 not connected."}
                sym_clean = str(symbol).strip().upper()
                selected = False
                for candidate in [sym_clean, sym_clean + ".a", sym_clean + "m", sym_clean + ".", sym_clean + "+"]:
                    if mt5.symbol_select(candidate, True) and mt5.symbol_info(candidate) is not None:
                        sym_clean = candidate
                        selected = True
                        break
                if not selected:
                    return {"status": "error", "message": f"Could not select symbol '{sym_clean}' in MT5. Please ensure it is added in MT5 Market Watch."}

                self.cfg.symbol = sym_clean
                self.last_tick = None
                self.last_tick_msc = -1
                self.live_ma = 0.0
                if self.bot:
                    self.bot.c = self.cfg
                    self.bot.margin_cooldown_until = 0
                    self.bot.margin_reject_count = 0
                    self.bot.last_order_error = ""
                self.save_persisted_config()
                self.get_mt5_account_and_market()
                return {"status": "ok", "message": f"Active symbol changed to {sym_clean}", "symbol": sym_clean}
            except Exception as e:
                return {"status": "error", "message": str(e)}

    def emergency_close_all(self) -> Dict[str, Any]:
        with self.lock:
            try:
                if self.bot:
                    self.bot.close_all()
                elif self.broker:
                    # Fallback manual close
                    for _ in range(10):
                        ps = self.broker.positions()
                        if not ps:
                            break
                        for p in ps:
                            self.broker.close(p)
                        self.broker.sleep(0.3)
                else:
                    br = MT5Broker(self.cfg)
                    for p in br.positions():
                        br.close(p)

                self.events.append({
                    "time": dt.datetime.now().strftime("%H:%M:%S"),
                    "event": "PANIC",
                    "side": "-",
                    "detail": "CLOSE_ALL",
                    "price": 0.0,
                    "basket": 0.0,
                    "message": f"[{dt.datetime.now().strftime('%H:%M:%S')}] PANIC: Emergency close all positions executed.",
                })
                return {"status": "ok", "message": "Emergency close sent for all positions."}
            except Exception as e:
                return {"status": "error", "message": f"Emergency close failed: {e}"}

    def login_mt5(self, login: Any, password: str = "", server: str = "", path: str = None) -> Dict[str, Any]:
        with self.lock:
            try:
                import MetaTrader5 as mt5
                login_int = int(str(login).strip())
                saved = load_saved_accounts()
                rec = saved.get(str(login_int), {})

                pass_str = str(password).strip() if password else rec.get("password", "")
                server_str = str(server).strip() if server else rec.get("server", "")
                terminal_path = path or rec.get("path") or r"C:\Program Files\MetaTrader 5\terminal64.exe"

                if not pass_str or not server_str:
                    return {"status": "error", "message": f"Trading password and broker server are required for account #{login_int}."}

                bot_module.save_mt5_env(login_int, pass_str, server_str, terminal_path)

                logged_in = False
                # Try logging in directly if terminal is already open
                if mt5.initialize():
                    if mt5.login(login=login_int, password=pass_str, server=server_str):
                        logged_in = True

                if not logged_in:
                    mt5.shutdown()
                    time.sleep(0.5)
                    logged_in = mt5.initialize(path=terminal_path, login=login_int, password=pass_str, server=server_str)

                if not logged_in:
                    err = mt5.last_error()
                    self.error_msg = f"MT5 Login failed: {err}"
                    return {"status": "error", "message": f"Login failed ({err}). Check account number, password, and server name."}

                self.error_msg = ""
                # Update saved_accounts.json
                rec.update({
                    "login": login_int,
                    "server": server_str,
                    "password": pass_str,
                    "path": terminal_path,
                    "last_seen": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                saved[str(login_int)] = rec
                save_saved_accounts(saved)

                self.get_mt5_account_and_market()
                return {"status": "ok", "message": f"Successfully switched to MT5 account #{login_int} @ {server_str}!"}
            except Exception as e:
                self.error_msg = str(e)
                return {"status": "error", "message": f"Login error: {e}"}

    def update_config(self, new_cfg: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            try:
                # If symbol is being changed, validate it via set_symbol logic first
                if "symbol" in new_cfg and new_cfg["symbol"]:
                    new_sym = str(new_cfg["symbol"]).strip().upper()
                    if new_sym != self.cfg.symbol:
                        if self.is_running:
                            return {"status": "error", "message": "Please stop the bot before switching the active symbol."}
                        import MetaTrader5 as mt5
                        if mt5.initialize(**bot_module.mt5_env()):
                            selected = False
                            for candidate in [new_sym, new_sym + ".a", new_sym + "m", new_sym + ".", new_sym + "+"]:
                                if mt5.symbol_select(candidate, True) and mt5.symbol_info(candidate) is not None:
                                    new_sym = candidate
                                    selected = True
                                    break
                            if not selected:
                                return {"status": "error", "message": f"Could not find symbol '{new_sym}' in MT5 Market Watch."}
                        self.cfg.symbol = new_sym
                        self.last_tick = None
                        self.last_tick_msc = -1
                        self.live_ma = 0.0
                        self.get_mt5_account_and_market()

                for k, v in new_cfg.items():
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
                        setattr(self.cfg, k, val)

                if self.bot:
                    self.bot.c = self.cfg
                    # Clear stale margin cooldown so new settings apply immediately
                    self.bot.margin_cooldown_until = 0
                    self.bot.margin_reject_count = 0
                    self.bot.last_order_error = ""
                self.save_persisted_config()
                return {"status": "ok", "message": "Configuration updated successfully."}
            except Exception as e:
                return {"status": "error", "message": f"Failed to update config: {e}"}

    def _run_loop(self):
        last_msc = -1
        t_panel = 0.0
        while not self.stop_event.is_set():
            try:
                tk = self.broker.tick()
                if tk.msc != last_msc:
                    last_msc = tk.msc
                    self.bot.on_tick()

                if time.time() - t_panel >= 0.5:
                    t_panel = time.time()
                    self.bot.on_timer()
                    self.get_mt5_account_and_market()

                    # Record equity curve point every minute
                    curr_min = int(time.time() // 60)
                    if curr_min != self.last_history_min and self.account_info:
                        self.last_history_min = curr_min
                        self.pnl_history.append({
                            "time": dt.datetime.now().strftime("%H:%M"),
                            "equity": self.account_info["equity"],
                            "basket": self.bot.basket,
                            "daily": self.bot.daily,
                        })

            except Exception as e:
                logger.error(f"Trading loop error: {e}")
                self.error_msg = str(e)
                time.sleep(1.0)
            time.sleep(0.01)

    def snapshot(self) -> Dict[str, Any]:
        bid_val = float(self.last_tick.get("bid", 0.0)) if self.last_tick else 0.0
        ma_val = float(self.bot.ma) if (self.bot and self.bot.ma > 0) else float(self.live_ma)
        rsi_val = float(self.bot.rsi) if (self.bot and self.bot.ma > 0) else float(self.live_rsi)

        telemetry = compute_entry_telemetry(
            bid=bid_val,
            ma=ma_val,
            max_dist=self.cfg.max_ma_dist,
            side=self.cfg.side,
            entry_mode=getattr(self.cfg, "entry_mode", "classic"),
            pullback_zone=getattr(self.cfg, "pullback_zone", 3.0),
            pullback_rejection_dist=getattr(self.cfg, "pullback_rejection_dist", 0.6),
            rsi=rsi_val,
            rsi_filter=getattr(self.cfg, "rsi_filter", True),
            rsi_ob=getattr(self.cfg, "rsi_ob", 70.0),
            rsi_os=getattr(self.cfg, "rsi_os", 30.0),
        )

        bot_data = {}
        if self.bot:
            bot_data = {
                "status": self.bot.status,
                "basket": round(self.bot.basket, 2),
                "peak": round(self.bot.peak, 2),
                "trail_stop": round(self.bot.trail_stop, 2),
                "daily": round(self.bot.daily, 2),
                "deals": self.bot.deals,
                "nopen": self.bot.nopen,
                "tp_price": round(self.bot.tp_price, 2),
                "ma": round(ma_val, 2),
                "exposure": round(self.bot.exposure, 1),
                "dist_ma": telemetry["dist_ma"],
                "rsi": round(rsi_val, 1),
                "rsi_status": telemetry["rsi_status"],
                "max_ma_dist": telemetry["max_ma_dist"],
                "target_entry_price": telemetry["target_entry_price"],
                "target_entry_desc": telemetry["target_entry_desc"],
                "buy_target_price": telemetry["buy_target_price"],
                "buy_target_desc": telemetry["buy_target_desc"],
                "buy_ready": telemetry["buy_ready"],
                "sell_target_price": telemetry["sell_target_price"],
                "sell_target_desc": telemetry["sell_target_desc"],
                "sell_ready": telemetry["sell_ready"],
                "in_entry_zone": telemetry["in_entry_zone"],
            }
        else:
            bot_pos = [p for p in self.positions_list if p.get("is_bot")]
            n_bot = len(bot_pos)
            bot_basket = round(sum(p.get("profit", 0.0) + p.get("swap", 0.0) for p in bot_pos), 2)

            acc_eq = float(self.account_info.get("equity", 0.0)) if self.account_info else 0.0
            acc_mg = float(self.account_info.get("margin", 0.0)) if self.account_info else 0.0
            exposure_val = round((acc_mg / acc_eq * 100.0) if acc_eq > 0 else 0.0, 1)

            status_str = f"STANDBY ({n_bot} Bot Legs Active)" if n_bot > 0 else "STOPPED"

            bot_data = {
                "status": status_str,
                "basket": bot_basket,
                "peak": 0.0,
                "trail_stop": 0.0,
                "daily": 0.0,
                "deals": 0,
                "nopen": n_bot,
                "tp_price": 0.0,
                "ma": round(ma_val, 2),
                "exposure": exposure_val,
                "dist_ma": telemetry["dist_ma"],
                "rsi": round(rsi_val, 1),
                "rsi_status": telemetry["rsi_status"],
                "max_ma_dist": telemetry["max_ma_dist"],
                "target_entry_price": telemetry["target_entry_price"],
                "target_entry_desc": telemetry["target_entry_desc"],
                "buy_target_price": telemetry["buy_target_price"],
                "buy_target_desc": telemetry["buy_target_desc"],
                "buy_ready": telemetry["buy_ready"],
                "sell_target_price": telemetry["sell_target_price"],
                "sell_target_desc": telemetry["sell_target_desc"],
                "sell_ready": telemetry["sell_ready"],
                "in_entry_zone": telemetry["in_entry_zone"],
            }

        cfg_dict = {f.name: getattr(self.cfg, f.name) for f in dataclasses.fields(Cfg)}

        return {
            "is_running": self.is_running,
            "allow_real": self.allow_real,
            "error_msg": self.error_msg,
            "logged_in": bool(self.account_info and self.account_info.get("login")),
            "is_market_live": self.is_market_live,
            "symbol": self.cfg.symbol,
            "symbols": self.available_symbols,
            "account": self.account_info,
            "accounts": self.get_available_accounts(),
            "market": self.last_tick,
            "bot": bot_data,
            "telemetry": telemetry,
            "positions": self.positions_list,
            "closed_positions": self.closed_positions_list,
            "events": list(self.events),
            "pnl_history": list(self.pnl_history),
            "config": cfg_dict,
        }


manager = BotManager()


@app.on_event("startup")
async def startup_event():
    # Continuously poll MT5 state every 0.5s so prices, account info,
    # and "Algo Trading" button changes update in real-time even when bot is stopped.
    def continuous_poller():
        while True:
            try:
                if not manager.is_running:
                    manager.get_mt5_account_and_market()
            except Exception as e:
                logger.debug(f"MT5 background poller: {e}")
            time.sleep(0.5)

    threading.Thread(target=continuous_poller, daemon=True).start()


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = os.path.join(TEMPLATES_DIR, "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/api/state")
async def get_state():
    return manager.snapshot()


@app.get("/api/accounts")
async def get_accounts():
    return manager.get_available_accounts()


@app.post("/api/switch-account")
async def switch_account(payload: Dict[str, Any]):
    login = payload.get("login")
    password = payload.get("password", "")
    server = payload.get("server", "")
    path = payload.get("path")
    if not login:
        return {"status": "error", "message": "Account login is required."}
    if manager.is_running:
        return {"status": "error", "message": "Cannot switch accounts while the bot is actively running. Stop the bot first."}
    return manager.login_mt5(login, password, server, path)


@app.post("/api/mt5-login")
async def mt5_login(payload: Dict[str, Any]):
    login = payload.get("login")
    password = payload.get("password")
    server = payload.get("server")
    path = payload.get("path")
    if not login or not password or not server:
        return {"status": "error", "message": "Account login, password, and broker server name are required."}
    if manager.is_running:
        return {"status": "error", "message": "Cannot switch accounts while the bot is actively running. Stop the bot first."}
    return manager.login_mt5(login, password, server, path)


@app.post("/api/start")
async def start_bot(payload: Dict[str, Any] = {}):
    allow_real = bool(payload.get("allow_real", False))
    return manager.start(allow_real=allow_real)


@app.post("/api/stop")
async def stop_bot():
    return manager.stop()


@app.post("/api/close-all")
async def close_all():
    return manager.emergency_close_all()


@app.get("/api/symbols")
async def get_symbols():
    return {"current": manager.cfg.symbol, "symbols": manager.available_symbols}


@app.post("/api/symbol")
async def select_symbol(payload: Dict[str, Any]):
    sym = payload.get("symbol", "").strip()
    if not sym:
        return {"status": "error", "message": "Symbol name cannot be empty."}
    return manager.set_symbol(sym)


@app.post("/api/config")
async def update_config(payload: Dict[str, Any]):
    return manager.update_config(payload)


@app.post("/api/break-time")
async def toggle_break_time(payload: Dict[str, Any]):
    enabled = bool(payload.get("enabled", False))
    with manager.lock:
        manager.cfg.break_time = enabled
        if manager.bot:
            manager.bot.c.break_time = enabled
    return {"status": "ok", "break_time": enabled}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            # Send latest state to client 5 times per second
            state = manager.snapshot()
            await ws.send_text(json.dumps(state))
            await asyncio.sleep(0.2)
    except (WebSocketDisconnect, RuntimeError):
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


def main():
    import webbrowser
    port = 8000
    host = "127.0.0.1"
    url = f"http://{host}:{port}"
    print("\n" + "=" * 65)
    print(f"  Vantage XAUUSD Bot Dashboard starting on {url}")
    print("=" * 65 + "\n")

    # Auto-open browser after 1.5 seconds
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()

