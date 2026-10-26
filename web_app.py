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


class BotManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.cfg = Cfg()
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

    def get_mt5_account_and_market(self):
        """Poll MT5 for account info, market tick, and positions without trading."""
        try:
            import MetaTrader5 as mt5
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
                    "currency": acc.currency,
                    "algo_trading_allowed": bool(ti.trade_allowed) if ti else False,
                }

            sym = self.cfg.symbol
            mt5.symbol_select(sym, True)
            tk = mt5.symbol_info_tick(sym)
            info = mt5.symbol_info(sym)

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
                        "time": int(tk.time or 0),
                        "is_live": False,
                        "tick_age_sec": 999999,
                    }

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

            magics = {self.cfg.magic, self.cfg.magic_recovery}
            raw_pos = mt5.positions_get(symbol=sym) or ()
            pos_data = []
            for p in raw_pos:
                is_bot = p.magic in magics
                pos_data.append({
                    "ticket": p.ticket,
                    "type": "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL",
                    "volume": float(p.volume),
                    "price_open": float(p.price_open),
                    "price_current": float(p.price_current),
                    "profit": round(float(p.profit), 2),
                    "swap": round(float(p.swap), 2),
                    "time": dt.datetime.fromtimestamp(p.time, dt.timezone.utc).strftime("%H:%M:%S"),
                    "magic": p.magic,
                    "is_bot": is_bot,
                    "origin": "B" if is_bot else "U",
                })
            self.positions_list = pos_data

            # Fetch closed deals / trades for past 24 hours
            now_dt = dt.datetime.now()
            start_dt = now_dt - dt.timedelta(days=1)
            deals = mt5.history_deals_get(start_dt, now_dt) or ()
            ins = {d.position_id: d for d in deals if d.entry == 0}
            outs = [d for d in deals if d.entry == 1]
            closed_data = []
            for out in reversed(outs):
                in_d = ins.get(out.position_id)
                pos_type = "BUY" if in_d and in_d.type == 0 else ("SELL" if in_d and in_d.type == 1 else ("BUY" if out.type == 1 else "SELL"))
                open_p = float(in_d.price) if in_d else 0.0
                is_b = bool(out.magic in magics or out.magic > 0)
                closed_data.append({
                    "ticket": out.position_id,
                    "type": pos_type,
                    "volume": float(out.volume),
                    "price_open": open_p,
                    "price_close": float(out.price),
                    "profit": round(float(out.profit + out.swap + out.commission), 2),
                    "time": dt.datetime.fromtimestamp(out.time).strftime("%H:%M:%S"),
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
                if not mt5.symbol_select(symbol, True):
                    return {"status": "error", "message": f"Could not select symbol '{symbol}' in MT5."}
                self.cfg.symbol = symbol
                self.get_mt5_account_and_market()
                return {"status": "ok", "message": f"Active symbol changed to {symbol}", "symbol": symbol}
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

    def login_mt5(self, login: Any, password: str, server: str, path: str = None) -> Dict[str, Any]:
        with self.lock:
            try:
                import MetaTrader5 as mt5
                terminal_path = path or r"C:\Program Files\MetaTrader 5\terminal64.exe"
                login_int = int(str(login).strip())
                pass_str = str(password).strip()
                server_str = str(server).strip()

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
                self.get_mt5_account_and_market()
                return {"status": "ok", "message": f"Successfully connected to MT5 account #{login_int} @ {server_str}!"}
            except Exception as e:
                self.error_msg = str(e)
                return {"status": "error", "message": f"Login error: {e}"}

    def update_config(self, new_cfg: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            try:
                for k, v in new_cfg.items():
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
                "ma": round(self.bot.ma, 2),
                "exposure": round(self.bot.exposure, 1),
                "dist_ma": round(getattr(self.bot, "dist_ma", 0.0), 2),
                "rsi": round(getattr(self.bot, "rsi", 50.0), 1),
            }
        else:
            bot_data = {
                "status": "STOPPED",
                "basket": 0.0,
                "peak": 0.0,
                "trail_stop": 0.0,
                "daily": 0.0,
                "deals": 0,
                "nopen": len([p for p in self.positions_list if p.get("is_bot")]),
                "tp_price": 0.0,
                "ma": 0.0,
                "exposure": 0.0,
                "dist_ma": 0.0,
                "rsi": 50.0,
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
            "market": self.last_tick,
            "bot": bot_data,
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


@app.post("/api/mt5-login")
async def mt5_login(payload: Dict[str, Any]):
    login = payload.get("login")
    password = payload.get("password")
    server = payload.get("server")
    path = payload.get("path")
    if not login or not password or not server:
        return {"status": "error", "message": "Account login, password, and broker server name are required."}
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

