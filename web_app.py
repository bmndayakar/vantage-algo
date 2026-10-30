"""
web_app.py - Real-Time Web Dashboard for Vantage XAUUSD Trading Bot
Runs locally on http://localhost:8000 with real-time WebSockets, live charts,
parameter tuning, and manual safety controls.
"""
import asyncio
import csv
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
from fastapi.responses import HTMLResponse, FileResponse
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
    try:
        dt_local = dt_utc.replace(tzinfo=dt.timezone.utc).astimezone()
    except Exception:
        # Fallback for platforms/Windows CRT on near-epoch timestamps
        dt_local = dt_utc + dt.timedelta(hours=5, minutes=30)

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
    spread: float = 0.0,
    max_spread: float = 0.50,
    rollover_blackout: bool = True,
    rollover_start_ist: str = "02:15",
    rollover_end_ist: str = "03:30",
    tc: int = 0,
    server_offset: float = 2.0,
    atr: float = 0.0,
    max_atr: float = 0.0,
    htf_filter: bool = True,
    htf_tf: str = "M5",
    htf_dir: int = 0,
    htf_fast: float = 0.0,
    htf_slow: float = 0.0,
    trend_system: str = "hybrid",
    tcs_state: Optional[Dict[str, Any]] = None,
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
            "trend_system": trend_system,
            "tcs_dir": 0,
            "tcs_status": "CALCULATING...",
            "tcs_bull_score": 0,
            "tcs_bear_score": 0,
            "tcs_ema_fast": 0.0,
            "tcs_ema_slow": 0.0,
            "tcs_adx": 0.0,
            "tcs_adx_rising": False,
            "tcs_di_plus": 0.0,
            "tcs_di_minus": 0.0,
            "tcs_structure": "CALCULATING...",
            "tcs_macd": 0.0,
            "tcs_macd_sig": 0.0,
            "tcs_macd_hist": 0.0,
            "tcs_macd_rising": False,
            "tcs_p1_bull": False,
            "tcs_p1_bear": False,
            "tcs_p2_bull": False,
            "tcs_p2_bear": False,
            "tcs_p3_bull": False,
            "tcs_p3_bear": False,
            "tcs_p4_bull": False,
            "tcs_p4_bear": False,
            "tcs_bar_closed": True,
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

    # Directional Overrides: TCS (4-Pillar System) if active, else Lever 3 HTF
    tcs = tcs_state or {}
    tcs_dir = int(tcs.get("direction", 0))
    tcs_status = str(tcs.get("status", "NEUTRAL"))
    b_score = int(tcs.get("bull_score", 0))
    s_score = int(tcs.get("bear_score", 0))

    htf_status = "BULLISH" if htf_dir == 1 else ("BEARISH" if htf_dir == -1 else "NEUTRAL")

    if trend_system in ("tcs", "hybrid") and tcs:
        if tcs_dir == 1:
            sell_ready = False
            sell_desc = f"Blocked by TCS Bullish Confirmation ({b_score}/4 Pillars)"
            action_side = f"BUY ONLY (TCS BULLISH {b_score}/4)"
            target_entry_price = buy_price
            target_entry_desc = f"TCS Bullish ({b_score}/4): {buy_desc}"
        elif tcs_dir == -1:
            buy_ready = False
            buy_desc = f"Blocked by TCS Bearish Confirmation ({s_score}/4 Pillars)"
            action_side = f"SELL ONLY (TCS BEARISH {s_score}/4)"
            target_entry_price = sell_price
            target_entry_desc = f"TCS Bearish ({s_score}/4): {sell_desc}"
        else:
            buy_ready = False
            sell_ready = False
            in_entry_zone = False
            action_side = f"NO TRADE (TCS CHOP FILTERED {b_score}B/{s_score}S)"
            target_entry_desc = f"⚠️ Chop Filter Active ({b_score}B/{s_score}S < Min Pillars) - Orders Blocked"
            buy_desc = f"Blocked: TCS Choppy ({b_score}B/{s_score}S)"
            sell_desc = f"Blocked: TCS Choppy ({b_score}B/{s_score}S)"
    elif htf_filter and htf_dir != 0:
        if htf_dir == 1: # Bullish: BUY only
            sell_ready = False
            sell_desc = f"Blocked by {htf_tf} Bullish Momentum ({htf_fast:.2f} > {htf_slow:.2f})"
            if side == "both":
                action_side = f"BUY ONLY ({htf_tf} BULLISH)"
                target_entry_price = buy_price
                target_entry_desc = f"Dip to MA: {buy_desc} ({htf_tf} Bullish Aligned)"
        elif htf_dir == -1: # Bearish: SELL only
            buy_ready = False
            buy_desc = f"Blocked by {htf_tf} Bearish Momentum ({htf_fast:.2f} < {htf_slow:.2f})"
            if side == "both":
                action_side = f"SELL ONLY ({htf_tf} BEARISH)"
                target_entry_price = sell_price
                target_entry_desc = f"Rally to MA: {sell_desc} ({htf_tf} Bearish Aligned)"

    # Lever 2: Dynamic Gates & Rollover Blackout Overrides
    rollover_active = bool(rollover_blackout and bot_module.is_in_rollover_window(tc, server_offset, rollover_start_ist, rollover_end_ist))
    spread_wide = bool(max_spread > 0 and spread > max_spread)
    volatility_climax = bool(max_atr > 0 and atr > max_atr)

    if rollover_active:
        action_side = "SLEEP (ROLLOVER BLACKOUT)"
        target_entry_desc = f"Rollover Blackout Active ({rollover_start_ist}-{rollover_end_ist} IST) - High Spread Protection"
        buy_ready = False
        sell_ready = False
        in_entry_zone = False
    elif spread_wide:
        action_side = f"BLOCKED (SPREAD WIDE ${spread:.2f})"
        target_entry_desc = f"Spread ${spread:.2f} exceeds Max Limit ${max_spread:.2f}"
        buy_ready = False
        sell_ready = False
        in_entry_zone = False
    elif volatility_climax:
        action_side = f"BLOCKED (VOLATILITY CLIMAX ATR ${atr:.2f})"
        target_entry_desc = f"ATR ${atr:.2f} exceeds Volatility Ceiling ${max_atr:.2f}"
        buy_ready = False
        sell_ready = False
        in_entry_zone = False

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
        "rollover_active": rollover_active,
        "rollover_window": f"{rollover_start_ist} - {rollover_end_ist} IST",
        "spread": round(spread, 2),
        "max_spread": round(max_spread, 2),
        "spread_wide": spread_wide,
        "atr": round(atr, 2),
        "max_atr": round(max_atr, 2),
        "volatility_climax": volatility_climax,
        "htf_filter": htf_filter,
        "htf_tf": htf_tf,
        "htf_dir": htf_dir,
        "htf_status": htf_status,
        "htf_fast": round(htf_fast, 2),
        "htf_slow": round(htf_slow, 2),
        "trend_system": trend_system,
        "tcs_dir": tcs_dir,
        "tcs_status": tcs_status,
        "tcs_bull_score": b_score,
        "tcs_bear_score": s_score,
        "tcs_ema_fast": tcs.get("ema_fast", 0.0),
        "tcs_ema_slow": tcs.get("ema_slow", 0.0),
        "tcs_adx": tcs.get("adx", 0.0),
        "tcs_adx_rising": tcs.get("adx_rising", False),
        "tcs_di_plus": tcs.get("di_plus", 0.0),
        "tcs_di_minus": tcs.get("di_minus", 0.0),
        "tcs_structure": tcs.get("structure", "CHOPPY"),
        "tcs_macd": tcs.get("macd", 0.0),
        "tcs_macd_sig": tcs.get("macd_sig", 0.0),
        "tcs_macd_hist": tcs.get("macd_hist", 0.0),
        "tcs_macd_rising": tcs.get("macd_rising", False),
        "tcs_p1_bull": tcs.get("p1_bull", False),
        "tcs_p1_bear": tcs.get("p1_bear", False),
        "tcs_p2_bull": tcs.get("p2_bull", False),
        "tcs_p2_bear": tcs.get("p2_bear", False),
        "tcs_p3_bull": tcs.get("p3_bull", False),
        "tcs_p3_bear": tcs.get("p3_bear", False),
        "tcs_p4_bull": tcs.get("p4_bull", False),
        "tcs_p4_bear": tcs.get("p4_bear", False),
        "tcs_bar_closed": tcs.get("bar_closed", True),
    }


CONFIG_FILE = os.path.join(HERE, "bot_config.json")
SAVED_ACCOUNTS_FILE = os.path.join(HERE, "saved_accounts.json")
TRADE_EXCURSIONS_FILE = os.path.join(HERE, "trade_excursions.json")
CLOSED_TRADES_FILE = os.path.join(HERE, "closed_trades.csv")

CLOSED_TRADES_HEADERS = [
    "ticket",
    "symbol",
    "type",
    "volume",
    "open_time_ist",
    "open_time_server",
    "close_time_ist",
    "close_time_server",
    "open_hour_ist",
    "close_hour_ist",
    "day_of_week",
    "session_tag",
    "duration_sec",
    "duration_str",
    "timeframe_tag",
    "open_price",
    "close_price",
    "price_diff",
    "gross_profit",
    "commission",
    "swap",
    "net_pnl",
    "pnl_per_lot",
    "outcome",
    "mfe",
    "mae",
    "mfe_mae_ratio",
    "magic",
    "trade_tag",
]


def classify_session(dt_ist: dt.datetime) -> str:
    """
    Classifies the trading session based on Indian Standard Time (IST):
    - Asian (Tokyo): 05:30 to 13:30 IST
    - London: 13:30 to 18:30 IST
    - London/NY Overlap: 18:30 to 21:30 IST (Prime Gold volatility)
    - New York: 21:30 to 02:30 IST
    - Pacific / Late US: 02:30 to 05:30 IST
    """
    h = dt_ist.hour + dt_ist.minute / 60.0
    if 5.5 <= h < 13.5:
        return "Asian (Tokyo)"
    elif 13.5 <= h < 18.5:
        return "London"
    elif 18.5 <= h < 21.5:
        return "London/NY Overlap"
    elif 21.5 <= h or h < 2.5:
        return "New York"
    else:
        return "Pacific/Late US"


def classify_duration(sec: int) -> str:
    """Classifies trade duration into practical scalping and swing categories."""
    if sec < 60:
        return "< 1 min (Hyper Scalp)"
    elif sec < 300:
        return "1 - 5 min (Fast Scalp)"
    elif sec < 900:
        return "5 - 15 min (Standard Scalp)"
    elif sec < 3600:
        return "15 - 60 min (Intraday Swing)"
    else:
        return "> 1 hr (Extended Swing)"


def sync_closed_trades_to_csv(filepath: str, closed_positions: List[Dict[str, Any]], server_offset: float = 2.0) -> int:
    """
    Persists closed trades offline into a structured CSV ledger with zero duplicates.
    Enriches each trade with IST/Server timestamps, session tags, duration brackets,
    and excursion telemetry (MFE/MAE) for offline quantitative analysis.
    """
    if not closed_positions:
        return 0

    existing_rows: Dict[str, Dict[str, Any]] = {}
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    t = str(row.get("ticket", "")).strip()
                    if t:
                        existing_rows[t] = row
        except Exception as e:
            logger.error(f"Error reading existing closed_trades.csv: {e}")

    added_count = 0
    updated_count = 0

    for pos in closed_positions:
        ticket = str(pos.get("ticket", "")).strip()
        if not ticket:
            continue

        open_ts = int(pos.get("open_time_ts", 0))
        close_ts = int(pos.get("close_time_ts", 0))
        duration_sec = int(pos.get("duration_sec", 0))
        vol = float(pos.get("volume", 0.0))
        p_open = float(pos.get("price_open", 0.0))
        p_close = float(pos.get("price_close", 0.0))
        net_pnl = float(pos.get("profit", 0.0))
        pos_type = str(pos.get("type", "BUY")).upper()

        if open_ts > 0:
            dt_open_server = dt.datetime.utcfromtimestamp(open_ts)
            dt_open_utc = dt_open_server - dt.timedelta(hours=server_offset)
            dt_open_ist = dt_open_utc + dt.timedelta(hours=5, minutes=30)
        else:
            dt_open_server = dt.datetime.utcfromtimestamp(close_ts) if close_ts > 0 else dt.datetime.utcnow()
            dt_open_ist = dt_open_server

        if close_ts > 0:
            dt_close_server = dt.datetime.utcfromtimestamp(close_ts)
            dt_close_utc = dt_close_server - dt.timedelta(hours=server_offset)
            dt_close_ist = dt_close_utc + dt.timedelta(hours=5, minutes=30)
        else:
            dt_close_server = dt_open_server
            dt_close_ist = dt_open_ist

        open_time_ist_str = dt_open_ist.strftime("%Y-%m-%d %H:%M:%S IST")
        open_time_srv_str = dt_open_server.strftime("%Y-%m-%d %H:%M:%S")
        close_time_ist_str = dt_close_ist.strftime("%Y-%m-%d %H:%M:%S IST")
        close_time_srv_str = dt_close_server.strftime("%Y-%m-%d %H:%M:%S")

        day_of_week = dt_open_ist.strftime("%A")
        session_tag = classify_session(dt_open_ist)
        timeframe_tag = classify_duration(duration_sec)

        price_diff = round(p_close - p_open if pos_type == "BUY" else p_open - p_close, 2)
        pnl_per_lot = round(net_pnl / vol, 2) if vol > 0 else 0.0
        outcome = "WIN" if net_pnl > 0.001 else ("LOSS" if net_pnl < -0.001 else "BE")

        mfe = pos.get("mfe")
        mae = pos.get("mae")
        mfe_val_str = f"{float(mfe):+.2f}" if mfe is not None else ""
        mae_val_str = f"{float(mae):+.2f}" if mae is not None else ""
        if mfe is not None and mae is not None and abs(float(mae)) > 0.001:
            ratio_str = f"{abs(float(mfe) / float(mae)):.2f}"
        else:
            ratio_str = ""

        row_data = {
            "ticket": ticket,
            "symbol": str(pos.get("symbol", "XAUUSD")),
            "type": pos_type,
            "volume": f"{vol:.2f}",
            "open_time_ist": open_time_ist_str,
            "open_time_server": open_time_srv_str,
            "close_time_ist": close_time_ist_str,
            "close_time_server": close_time_srv_str,
            "open_hour_ist": str(dt_open_ist.hour),
            "close_hour_ist": str(dt_close_ist.hour),
            "day_of_week": day_of_week,
            "session_tag": session_tag,
            "duration_sec": str(duration_sec),
            "duration_str": str(pos.get("duration", "")),
            "timeframe_tag": timeframe_tag,
            "open_price": f"{p_open:.2f}",
            "close_price": f"{p_close:.2f}",
            "price_diff": f"{price_diff:+.2f}",
            "gross_profit": f"{float(pos.get('gross_profit', 0.0)):.2f}",
            "commission": f"{float(pos.get('commission', 0.0)):.2f}",
            "swap": f"{float(pos.get('swap', 0.0)):.2f}",
            "net_pnl": f"{net_pnl:+.2f}",
            "pnl_per_lot": f"{pnl_per_lot:+.2f}",
            "outcome": outcome,
            "mfe": mfe_val_str,
            "mae": mae_val_str,
            "mfe_mae_ratio": ratio_str,
            "magic": str(pos.get("magic", 0)),
            "trade_tag": str(pos.get("origin", "B")),
            "_close_ts": close_ts,
        }

        if ticket not in existing_rows:
            existing_rows[ticket] = row_data
            added_count += 1
        else:
            curr = existing_rows[ticket]
            if (not curr.get("mfe") and mfe_val_str) or (not curr.get("mae") and mae_val_str):
                curr["mfe"] = mfe_val_str
                curr["mae"] = mae_val_str
                curr["mfe_mae_ratio"] = ratio_str
                updated_count += 1

    if added_count > 0 or updated_count > 0 or not os.path.exists(filepath):
        sorted_rows = sorted(
            existing_rows.values(),
            key=lambda r: str(r.get("close_time_server", "")),
            reverse=True,
        )
        try:
            with open(filepath, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=CLOSED_TRADES_HEADERS, extrasaction="ignore")
                writer.writeheader()
                for r in sorted_rows:
                    writer.writerow(r)
        except Exception as e:
            logger.error(f"Failed to write closed_trades.csv: {e}")

    return added_count


def compute_win_rate_stats(filepath: str, server_offset: float = 2.0) -> Dict[str, Any]:
    """
    Computes institutional win rate and loss statistics across four key horizons:
    - Today (current IST calendar day)
    - Yesterday (previous IST calendar day)
    - This Week (Monday 00:00:00 to now)
    - This Month (1st day of month 00:00:00 to now)

    Returns structured metrics:
    - wins, losses, scratches/breakeven, total
    - win_pct (float), loss_pct (float)
    - net_pnl (float)
    """
    now_ist = dt.datetime.utcnow() + dt.timedelta(hours=5, minutes=30)
    today_date = now_ist.date()
    yesterday_date = today_date - dt.timedelta(days=1)
    week_start = today_date - dt.timedelta(days=today_date.weekday())
    month_start = today_date.replace(day=1)

    periods = {
        "today": {"label": "Today", "wins": 0, "losses": 0, "be": 0, "total": 0, "pnl": 0.0, "win_pct": 0.0, "loss_pct": 0.0},
        "yesterday": {"label": "Yesterday", "wins": 0, "losses": 0, "be": 0, "total": 0, "pnl": 0.0, "win_pct": 0.0, "loss_pct": 0.0},
        "this_week": {"label": "This Week", "wins": 0, "losses": 0, "be": 0, "total": 0, "pnl": 0.0, "win_pct": 0.0, "loss_pct": 0.0},
        "this_month": {"label": "This Month", "wins": 0, "losses": 0, "be": 0, "total": 0, "pnl": 0.0, "win_pct": 0.0, "loss_pct": 0.0},
    }

    if not os.path.exists(filepath):
        return periods

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                close_str = r.get("close_time_ist", "")
                if not close_str:
                    continue
                date_part = close_str.split(" ")[0]
                try:
                    d_obj = dt.datetime.strptime(date_part, "%Y-%m-%d").date()
                except Exception:
                    continue

                try:
                    pnl = float(r.get("net_pnl", 0.0))
                except Exception:
                    pnl = 0.0

                is_win = pnl > 0.001
                is_loss = pnl < -0.001
                is_be = not is_win and not is_loss

                matches = []
                if d_obj == today_date:
                    matches.append("today")
                if d_obj == yesterday_date:
                    matches.append("yesterday")
                if week_start <= d_obj <= today_date:
                    matches.append("this_week")
                if month_start <= d_obj <= today_date:
                    matches.append("this_month")

                for m in matches:
                    bucket = periods[m]
                    bucket["total"] += 1
                    bucket["pnl"] += pnl
                    if is_win:
                        bucket["wins"] += 1
                    elif is_loss:
                        bucket["losses"] += 1
                    else:
                        bucket["be"] += 1

        for k, b in periods.items():
            tot = b["total"]
            w = b["wins"]
            l = b["losses"]
            b["win_pct"] = round((w / tot * 100.0), 1) if tot > 0 else 0.0
            b["loss_pct"] = round((l / tot * 100.0), 1) if tot > 0 else 0.0
            b["pnl"] = round(b["pnl"], 2)

    except Exception as e:
        logger.error(f"Error computing win rate stats: {e}")

    return periods


def load_trade_excursions() -> Dict[str, Any]:
    if not os.path.exists(TRADE_EXCURSIONS_FILE):
        return {}
    try:
        with open(TRADE_EXCURSIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_trade_excursions(excursions: Dict[str, Any]):
    try:
        with open(TRADE_EXCURSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(excursions, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save trade excursions: {e}")


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


def reconstruct_closed_positions(
    deals,
    fetch_pos_deals_fn=None,
    magics=(123790, 789998),
    server_offset=0,
    trade_excursions=None,
) -> List[Dict[str, Any]]:
    """
    Reconstructs closed positions from MT5 trade deals matching MT5 Desktop's 'Positions' tab:
    - Ticket: Position ID
    - Type: BUY or SELL based on opening entry direction
    - Lots: Total closed volume
    - Open Price: Volume-weighted average entry fill price
    - Close Price: Volume-weighted average exit fill price
    - Profit: Net realized PnL (sum(deal.profit) + sum(deal.swap) + sum(deal.commission))
    - Excursion: MFE & MAE looked up by position ticket
    - Symbol: Deal symbol
    - Timestamps: In IST and Server time
    """
    if not deals:
        return []

    # Deal entry flags in MT5:
    # 0 = DEAL_ENTRY_IN, 1 = DEAL_ENTRY_OUT, 2 = DEAL_ENTRY_INOUT, 3 = DEAL_ENTRY_OUT_BY
    # Deal types: 0 = BUY, 1 = SELL (2+ are balance/credit)
    closed_pos_ids = {
        getattr(d, "position_id", 0)
        for d in deals
        if getattr(d, "entry", -1) in (1, 2, 3)
        and getattr(d, "position_id", 0) > 0
        and getattr(d, "type", -1) in (0, 1)
    }

    if not closed_pos_ids:
        return []

    deals_by_pos: Dict[int, List[Any]] = collections.defaultdict(list)
    for d in deals:
        pid = getattr(d, "position_id", 0)
        if pid in closed_pos_ids and getattr(d, "type", -1) in (0, 1):
            deals_by_pos[pid].append(d)

    closed_data = []
    magic_set = set(magics)

    for pos_id in sorted(closed_pos_ids, reverse=True):
        pdeals = deals_by_pos.get(pos_id, [])

        # If entry deals occurred outside the queried deals window, fetch full deals for this position
        if fetch_pos_deals_fn and not any(getattr(d, "entry", -1) in (0, 2) for d in pdeals):
            try:
                extra = fetch_pos_deals_fn(pos_id)
                if extra:
                    pdeals = [
                        d for d in extra
                        if getattr(d, "position_id", 0) == pos_id and getattr(d, "type", -1) in (0, 1)
                    ]
            except Exception:
                pass

        entries = [d for d in pdeals if getattr(d, "entry", -1) in (0, 2)]
        exits = [d for d in pdeals if getattr(d, "entry", -1) in (1, 3)]

        if not exits:
            continue

        tot_closed_vol = sum(float(getattr(d, "volume", 0.0)) for d in exits)
        if tot_closed_vol <= 0:
            tot_closed_vol = sum(float(getattr(d, "volume", 0.0)) for d in entries) or 0.01

        weighted_close_p = (
            sum(float(getattr(d, "price", 0.0)) * float(getattr(d, "volume", 0.0)) for d in exits)
            / sum(float(getattr(d, "volume", 0.0)) for d in exits)
            if any(float(getattr(d, "volume", 0.0)) > 0 for d in exits)
            else float(getattr(exits[-1], "price", 0.0))
        )

        if entries and any(float(getattr(d, "volume", 0.0)) > 0 for d in entries):
            weighted_open_p = (
                sum(float(getattr(d, "price", 0.0)) * float(getattr(d, "volume", 0.0)) for d in entries)
                / sum(float(getattr(d, "volume", 0.0)) for d in entries)
            )
            pos_type = "BUY" if getattr(entries[0], "type", 0) == 0 else "SELL"
            open_time = min(int(getattr(d, "time", 0)) for d in entries)
        elif exits:
            weighted_open_p = 0.0
            # If exit deal was SELL (1), position was BUY. If exit was BUY (0), position was SELL.
            pos_type = "BUY" if getattr(exits[0], "type", 0) == 1 else "SELL"
            open_time = min(int(getattr(d, "time", 0)) for d in exits)
        else:
            continue

        close_time = max(int(getattr(d, "time", 0)) for d in exits)
        duration_sec = max(0, close_time - open_time) if (open_time > 0 and close_time >= open_time) else 0

        gross_profit = sum(float(getattr(d, "profit", 0.0)) for d in pdeals)
        swap = sum(float(getattr(d, "swap", 0.0)) for d in pdeals)
        comm = sum(float(getattr(d, "commission", 0.0)) for d in pdeals)
        net_profit = round(gross_profit + swap + comm, 2)

        magic = max((int(getattr(d, "magic", 0)) for d in pdeals), default=0)
        is_bot = bool(magic in magic_set or magic > 0)
        origin = "REC" if magic == 789998 else ("B" if is_bot else "U")

        sym = (
            getattr(exits[0], "symbol", "")
            if exits and getattr(exits[0], "symbol", "")
            else (getattr(entries[0], "symbol", "") if entries else "")
        )

        t_in = format_mt5_time(open_time, server_offset)
        t_out = format_mt5_time(close_time, server_offset)

        ticket_str = str(pos_id)
        exc = (trade_excursions or {}).get(ticket_str)
        mfe_val = round(float(exc["mfe"]), 2) if (exc and "mfe" in exc) else None
        mae_val = round(float(exc["mae"]), 2) if (exc and "mae" in exc) else None

        closed_data.append({
            "ticket": pos_id,
            "symbol": sym,
            "type": pos_type,
            "volume": round(tot_closed_vol, 2),
            "price_open": round(weighted_open_p, 2),
            "price_close": round(weighted_close_p, 2),
            "gross_profit": round(gross_profit, 2),
            "swap": round(swap, 2),
            "commission": round(comm, 2),
            "profit": net_profit,
            "mfe": mfe_val,
            "mae": mae_val,
            "time_open": t_in["local"],
            "time_open_server": t_in["server"],
            "time_close": t_out["local"],
            "time_close_server": t_out["server"],
            "time": t_out["local"],
            "duration": format_duration(duration_sec),
            "duration_sec": duration_sec,
            "open_time_ts": open_time,
            "magic": magic,
            "is_bot": is_bot,
            "origin": origin,
            "close_time_ts": close_time,
        })

    # Sort descending by close timestamp (most recent exit first)
    closed_data.sort(key=lambda x: x["close_time_ts"], reverse=True)
    return closed_data


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
        self.live_atr: float = 0.0
        self.live_htf_dir: int = 0
        self.live_htf_fast: float = 0.0
        self.live_htf_slow: float = 0.0
        self.live_tcs_state: Dict[str, Any] = {}
        self.last_tcs_calc_time: float = 0.0
        self.trade_excursions: Dict[str, Any] = load_trade_excursions()
        self.last_excursions_save: float = 0.0
        self.history_period: str = "7d"
        self.session_profit: float = 0.0
        self.session_deals: int = 0
        self.has_initial_history_sync: bool = False
        self.last_history_sync_time: float = 0.0
        self.last_deals_count: int = -1
        self._cached_win_rate_stats: Dict[str, Any] = {}
        self._last_win_rate_calc_time: float = 0.0
        self._last_csv_mtime: float = 0.0

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

    def get_win_rate_stats(self) -> Dict[str, Any]:
        """Returns institutional win rate metrics cached against closed_trades.csv mtime."""
        try:
            mtime = os.path.getmtime(CLOSED_TRADES_FILE) if os.path.exists(CLOSED_TRADES_FILE) else 0.0
        except Exception:
            mtime = 0.0
        if mtime != self._last_csv_mtime or (time.time() - self._last_win_rate_calc_time > 5.0) or not self._cached_win_rate_stats:
            self._cached_win_rate_stats = compute_win_rate_stats(CLOSED_TRADES_FILE, self.get_server_offset())
            self._last_csv_mtime = mtime
            self._last_win_rate_calc_time = time.time()
        return self._cached_win_rate_stats

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

            # Sync or calculate live MA, RSI, HTF trend, and TCS state
            if self.bot and getattr(self.bot, "ma", 0.0) > 0:
                self.live_ma = float(self.bot.ma)
                self.live_rsi = float(getattr(self.bot, "rsi", 50.0))
                self.live_atr = float(getattr(self.bot, "atr", 0.0))
                self.live_htf_dir = int(getattr(self.bot, "htf_dir", 0))
                self.live_htf_fast = float(getattr(self.bot, "htf_fast", 0.0))
                self.live_htf_slow = float(getattr(self.bot, "htf_slow", 0.0))
                self.live_tcs_state = getattr(self.bot, "tcs_state", {}) or {}
            else:
                if time.time() - self.last_tcs_calc_time > 1.0:
                    self.last_tcs_calc_time = time.time()
                    try:
                        br = MT5Broker(self.cfg)
                        self.live_tcs_state = br.tcs_eval(
                            tf_str=getattr(self.cfg, "tcs_tf", "M1"),
                            ema_fast=getattr(self.cfg, "tcs_ema_fast", 50),
                            ema_slow=getattr(self.cfg, "tcs_ema_slow", 200),
                            adx_period=getattr(self.cfg, "tcs_adx_period", 14),
                            adx_min=getattr(self.cfg, "tcs_adx_min", 25.0),
                            require_rising=getattr(self.cfg, "tcs_adx_require_rising", False),
                            lookback=getattr(self.cfg, "tcs_structure_bars", 20),
                            min_pillars=getattr(self.cfg, "tcs_min_pillars", 3),
                        )
                    except Exception:
                        pass
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
            excursions_dirty = False
            for p in raw_pos:
                ticket_str = str(p.ticket)
                curr_pnl = round(float(p.profit + p.swap), 2)
                if ticket_str not in self.trade_excursions:
                    self.trade_excursions[ticket_str] = {
                        "mfe": max(0.0, curr_pnl),
                        "mae": min(0.0, curr_pnl),
                    }
                    excursions_dirty = True
                else:
                    exc = self.trade_excursions[ticket_str]
                    if curr_pnl > exc.get("mfe", 0.0):
                        exc["mfe"] = curr_pnl
                        excursions_dirty = True
                    if curr_pnl < exc.get("mae", 0.0):
                        exc["mae"] = curr_pnl
                        excursions_dirty = True

                exc = self.trade_excursions.get(ticket_str, {})
                mfe_val = round(float(exc.get("mfe", 0.0)), 2)
                mae_val = round(float(exc.get("mae", 0.0)), 2)

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
                    "sl": float(getattr(p, "sl", 0.0) or 0.0),
                    "tp": float(getattr(p, "tp", 0.0) or 0.0),
                    "profit": curr_pnl,
                    "gross_profit": round(float(p.profit), 2),
                    "swap": round(float(p.swap), 2),
                    "mfe": mfe_val,
                    "mae": mae_val,
                    "time": t_open["local"],
                    "time_open": t_open["local"],
                    "time_open_server": t_open["server"],
                    "duration": format_duration(age_sec),
                    "magic": p.magic,
                    "is_bot": is_bot,
                    "origin": "REC" if p.magic == self.cfg.magic_recovery else ("B" if is_bot else "U"),
                })
            self.positions_list = pos_data

            # Fetch closed deals / trades directly from MT5 based on selected history period (aligned with broker server time)
            server_midnight = server_now_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            end_dt = server_now_dt + dt.timedelta(days=1)

            if self.history_period == "today":
                start_dt = server_midnight
            elif self.history_period == "3d":
                start_dt = server_now_dt - dt.timedelta(days=3)
            elif self.history_period == "30d":
                start_dt = server_now_dt - dt.timedelta(days=30)
            elif self.history_period == "all":
                start_dt = dt.datetime(2020, 1, 1)
            else:  # "7d" default
                start_dt = server_now_dt - dt.timedelta(days=7)

            # One-time startup / account switch historical catchup (last 90 days)
            if not self.has_initial_history_sync:
                self.has_initial_history_sync = True
                try:
                    catchup_start = server_now_dt - dt.timedelta(days=90)
                    all_deals = mt5.history_deals_get(catchup_start, end_dt) or ()
                    all_closed = reconstruct_closed_positions(
                        deals=all_deals,
                        fetch_pos_deals_fn=lambda pid: mt5.history_deals_get(position=pid),
                        magics=magics,
                        server_offset=server_offset,
                        trade_excursions=self.trade_excursions,
                    )
                    if all_closed:
                        sync_closed_trades_to_csv(CLOSED_TRADES_FILE, all_closed, server_offset=server_offset)
                except Exception as ex:
                    logger.debug(f"Initial trade history sync: {ex}")

            now_t = time.time()
            cur_deals = getattr(self.bot, "deals", 0) if self.bot else 0
            deals_changed = (cur_deals != self.last_deals_count)
            time_since_sync = now_t - self.last_history_sync_time

            # Throttle history deal reconstruction: run every 10s or when a trade closes
            if not self.has_initial_history_sync or deals_changed or (time_since_sync >= 10.0):
                self.last_history_sync_time = now_t
                self.last_deals_count = cur_deals
                deals = mt5.history_deals_get(start_dt, end_dt) or ()
                self.closed_positions_list = reconstruct_closed_positions(
                    deals=deals,
                    fetch_pos_deals_fn=lambda pid: mt5.history_deals_get(position=pid),
                    magics=magics,
                    server_offset=server_offset,
                    trade_excursions=self.trade_excursions,
                )

                # Auto-sync closed trades to offline CSV ledger
                if self.closed_positions_list:
                    sync_closed_trades_to_csv(
                        filepath=CLOSED_TRADES_FILE,
                        closed_positions=self.closed_positions_list,
                        server_offset=server_offset,
                    )

            if excursions_dirty and (time.time() - self.last_excursions_save > 5.0):
                self.last_excursions_save = time.time()
                save_trade_excursions(self.trade_excursions)

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

                def intercepted_log(ev, side, detail, price, basket, realized, mfe=None, mae=None):
                    orig_log(ev, side, detail, price, basket, realized, mfe, mae)
                    time_str = dt.datetime.now().strftime("%H:%M:%S")
                    mfe_val = self.bot.peak if mfe is None else mfe
                    mae_val = self.bot.mae if mae is None else mae
                    exc_str = f" [Peak: +${mfe_val:.2f}, Dip: -${abs(mae_val):.2f}]" if (mfe_val != 0 or mae_val != 0) else ""
                    msg = f"[{time_str}] {ev} {side} {detail} (Price: {price:.2f}, Basket: ${basket:.2f}{exc_str})"
                    self.events.append({
                        "time": time_str,
                        "event": ev,
                        "side": side,
                        "detail": detail,
                        "price": price,
                        "basket": basket,
                        "mfe": mfe_val,
                        "mae": mae_val,
                        "message": msg
                    })

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
                self.has_initial_history_sync = False
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

                # If ui_mode is noob (or being updated to noob), apply noob preset
                req_ui_mode = str(new_cfg.get("ui_mode", getattr(self.cfg, "ui_mode", "noob"))).lower()
                req_noob_lvl = int(new_cfg.get("noob_level", getattr(self.cfg, "noob_level", 3)))

                if req_ui_mode == "noob":
                    bot_module.apply_noob_preset_to_cfg(self.cfg, req_noob_lvl)
                    self.cfg.ui_mode = "noob"

                for k, v in new_cfg.items():
                    if k == "symbol":
                        continue
                    # When in noob mode, do not let manual fields override noob presets except lots, side, etc.
                    if req_ui_mode == "noob" and k in ("tcs_min_pillars", "tcs_adx_min", "max_ma_dist", "pullback_zone", "grid_sl", "trail_arm", "trail_min_lock", "hard_cap_hours"):
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
                    # Clear stale margin cooldown and loss pause so new settings apply immediately
                    self.bot.margin_cooldown_until = 0
                    self.bot.loss_cooldown_until = 0
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

        server_offset = self.get_server_offset()
        ask_val = float(self.last_tick.get("ask", 0.0)) if self.last_tick else 0.0
        cur_spread = round(ask_val - bid_val, 2) if (ask_val > 0 and bid_val > 0) else 0.0
        atr_val = float(getattr(self.bot, "atr", 0.0)) if self.bot else float(getattr(self, "live_atr", 0.0))
        tk_time = int(self.last_tick.get("time", 0)) if self.last_tick else int(time.time())

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
            spread=cur_spread,
            max_spread=getattr(self.cfg, "max_spread", 0.50),
            rollover_blackout=getattr(self.cfg, "rollover_blackout", True),
            rollover_start_ist=getattr(self.cfg, "rollover_start_ist", "02:15"),
            rollover_end_ist=getattr(self.cfg, "rollover_end_ist", "03:30"),
            tc=tk_time,
            server_offset=server_offset,
            atr=atr_val,
            max_atr=getattr(self.cfg, "max_atr", 0.0),
            htf_filter=getattr(self.cfg, "htf_filter", True),
            htf_tf=getattr(self.cfg, "htf_tf", "M5"),
            htf_dir=int(getattr(self.bot, "htf_dir", self.live_htf_dir)),
            htf_fast=float(getattr(self.bot, "htf_fast", self.live_htf_fast)),
            htf_slow=float(getattr(self.bot, "htf_slow", self.live_htf_slow)),
            trend_system=getattr(self.cfg, "trend_system", "hybrid"),
            tcs_state=getattr(self.bot, "tcs_state", self.live_tcs_state) or {},
        )

        server_offset = self.get_server_offset()
        server_now_dt = dt.datetime.utcnow() + dt.timedelta(hours=server_offset)
        server_midnight_ts = int(server_now_dt.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=dt.timezone.utc).timestamp())

        today_bot_pos = [
            p for p in self.closed_positions_list
            if p.get("is_bot") and p.get("close_time_ts", 0) >= server_midnight_ts
        ]
        today_broker_pnl = sum(p["profit"] for p in today_bot_pos)
        today_broker_deals = len(today_bot_pos)

        sess_pnl = getattr(self.bot, "session_profit", self.session_profit) if self.bot else self.session_profit
        sess_deals = getattr(self.bot, "session_deals", self.session_deals) if self.bot else self.session_deals
        day_pnl = self.bot.daily if self.bot else today_broker_pnl
        day_deals = self.bot.deals if self.bot else today_broker_deals

        bot_data = {}
        if self.bot:
            bot_data = {
                "status": self.bot.status,
                "basket": round(self.bot.basket, 2),
                "peak": round(self.bot.peak, 2),
                "trail_stop": round(self.bot.trail_stop, 2),
                "daily": round(sess_pnl, 2),
                "deals": sess_deals,
                "session_profit": round(sess_pnl, 2),
                "session_deals": sess_deals,
                "broker_daily": round(day_pnl, 2),
                "broker_deals": day_deals,
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
                "lot_mult": round(self.cfg.lot_mult, 2),
                "eff_grid_step_loss": round(self.cfg.eff_grid_step_loss, 2),
                "eff_grid_sl": round(self.cfg.eff_grid_sl, 2),
                "eff_trail_arm": round(self.cfg.eff_trail_arm, 2),
                "eff_trail_min_lock": round(self.cfg.eff_trail_min_lock, 2),
                "eff_grid_tp": round(self.cfg.eff_grid_tp, 2),
                "eff_target_profit": round(self.cfg.eff_target_profit, 2),
                "eff_bailout_target": round(self.cfg.eff_bailout_target, 2),
                "loss_cooldown_rem": max(0, self.bot.loss_cooldown_until - int(time.time())) if self.bot.loss_cooldown_until > 0 else 0,
                "basket_mfe": round(self.bot.peak, 2),
                "basket_mae": round(self.bot.mae, 2),
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
                "daily": round(sess_pnl, 2),
                "deals": sess_deals,
                "session_profit": round(sess_pnl, 2),
                "session_deals": sess_deals,
                "broker_daily": round(day_pnl, 2),
                "broker_deals": day_deals,
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
                "lot_mult": round(self.cfg.lot_mult, 2),
                "eff_grid_step_loss": round(self.cfg.eff_grid_step_loss, 2),
                "eff_grid_sl": round(self.cfg.eff_grid_sl, 2),
                "eff_trail_arm": round(self.cfg.eff_trail_arm, 2),
                "eff_trail_min_lock": round(self.cfg.eff_trail_min_lock, 2),
                "eff_grid_tp": round(self.cfg.eff_grid_tp, 2),
                "eff_target_profit": round(self.cfg.eff_target_profit, 2),
                "eff_bailout_target": round(self.cfg.eff_bailout_target, 2),
                "loss_cooldown_rem": 0,
                "basket_mfe": 0.0,
                "basket_mae": 0.0,
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
            "closed_positions": self.closed_positions_list[:50],
            "history_period": self.history_period,
            "win_rate_stats": self.get_win_rate_stats(),
            "events": list(self.events),
            "pnl_history": list(self.pnl_history),
            "config": cfg_dict,
        }


manager = BotManager()
@app.get("/api/performance")
async def get_performance():
    return manager.get_win_rate_stats()



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


@app.post("/api/history_period")
async def set_history_period(payload: Dict[str, Any]):
    period = str(payload.get("period", "7d")).strip().lower()
    if period in ("today", "3d", "7d", "30d", "all"):
        manager.history_period = period
        manager.get_mt5_account_and_market()
    return {"status": "ok", "period": manager.history_period}


@app.post("/api/reset_goal")
async def reset_goal():
    with manager.lock:
        manager.session_profit = 0.0
        manager.session_deals = 0
        if manager.bot:
            manager.bot.session_profit = 0.0
            manager.bot.session_deals = 0
            manager.bot.daily = 0.0
            manager.bot.deals = 0
    return {"status": "ok", "message": "Session goal & deals reset."}


@app.get("/api/export_trades_csv")
def export_trades_csv():
    """Download the complete offline closed trades CSV ledger."""
    if not os.path.exists(CLOSED_TRADES_FILE):
        with open(CLOSED_TRADES_FILE, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CLOSED_TRADES_HEADERS)
            writer.writeheader()
    filename = f"closed_trades_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return FileResponse(CLOSED_TRADES_FILE, media_type="text/csv", filename=filename)


@app.get("/api/trade_analytics")
def get_trade_analytics():
    """Returns parsed quantitative performance metrics across sessions and hours."""
    if not os.path.exists(CLOSED_TRADES_FILE):
        return {"status": "ok", "total_trades": 0, "trades": []}
    try:
        trades = []
        with open(CLOSED_TRADES_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                trades.append(r)
        n_total = len(trades)
        n_wins = sum(1 for t in trades if t.get("outcome") == "WIN")
        tot_pnl = round(sum(float(t.get("net_pnl", 0.0)) for t in trades), 2)
        win_rate = round((n_wins / n_total) * 100.0, 1) if n_total > 0 else 0.0
        return {
            "status": "ok",
            "total_trades": n_total,
            "win_rate": win_rate,
            "net_pnl": tot_pnl,
            "trades": trades[:100],
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            # Send latest state to client ~1.25 times per second (smooth, low-latency, zero-leak)
            state = manager.snapshot()
            await ws.send_text(json.dumps(state))
            await asyncio.sleep(0.8)
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

