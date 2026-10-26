# AGENT_CONTEXT.md — Vantage Algo Master Knowledge Base

> **Target Audience**: Any AI Agent, Pair Programmer, or Developer picking up this codebase.  
> **Primary Repository**: `https://github.com/bmndayakar/vantage-algo.git`  
> **Branch**: `main`  
> **Last Updated**: 2026-10-26 (Post-Production Release v2.5.0)

---

## 1. Executive Summary & Codebase Anatomy

This repository is an algorithmic trading system and live monitoring dashboard built for **MetaTrader 5 (MT5)**, primarily tuned for **Gold (`XAUUSD`)**, with multi-asset support across Forex, Indices, and Crypto.

### File Manifest:
| File | Role | Key Technologies |
| :--- | :--- | :--- |
| `up_down_tracker_win_bot_xauusd.py` | **Core Strategy Engine** | Python 3.11, `MetaTrader5`, `numpy`, `dataclasses`, `argparse` |
| `web_app.py` | **Backend Server & Telemetry** | `FastAPI`, `Uvicorn`, `WebSockets`, `asyncio`, `threading` |
| `templates/index.html` | **Interactive Frontend UI** | HTML5, Tailwind CSS (CDN), Chart.js, Vanilla JavaScript |
| `run_ui.bat` | **One-Click Windows Launcher** | Windows Batch Script (launches `web_app.py` and opens browser) |
| `.env` / `.env.example` | **Credential Secrets** | Auto-login credentials for MT5 terminal (Git-ignored) |
| `SYSTEM_GUIDE.md` | **System & Mathematical Specs** | Markdown reference manual with Mermaid lifecycle diagrams |
| `README.md` | **Project Readme** | High-level quickstart and feature overview |

---

## 2. Chronological Failure & Debugging Log (Every Real-Time Issue & Resolution)

The following real-time failures occurred during live testing and trading sessions. Future agents **must** study these to avoid re-introducing previous bugs:

### Case 1: Python Architecture & Version Mismatch
* **The Failure**: Launching the bot crashed with:
  ```text
  ModuleNotFoundError: No module named 'MetaTrader5'
  ```
* **The Root Cause**: The user's system initially had Python 3.13 (32-bit) installed. MetaQuotes distributes pre-compiled MT5 wheels exclusively for **64-bit Windows** and supports versions up to Python 3.12 (not 3.13 at time of deployment).
* **The Resolution**: Installed Python 3.11.9 (64-bit) at `C:\Users\dayam\AppData\Local\Programs\Python\Python311\python.exe`.

---

### Case 2: MT5 Interactive Login Modal ("Undefined" Error)
* **The Failure**: Clicking "Connect" in the dashboard login modal produced an alert saying `undefined`.
* **The Root Cause**: The browser called `POST /api/mt5-login` while an older instance of `web_app.py` was running. FastAPI returned a 404 validation response formatted as `{"detail": ...}` instead of `{"message": ...}`.
* **The Resolution**:
  1. Updated frontend JS: `const msg = data.message || data.detail || JSON.stringify(data)`.
  2. Implemented `login_mt5()` in `BotManager` supporting dual connection modes: attaches to an already-open MT5 session, or auto-launches `terminal64.exe` using credentials.

---

### Case 3: WebSocket ASGI Error on Browser Tab Refresh
* **The Failure**: Terminal logs were spammed with:
  ```text
  [ERROR] WebSocket error: Unexpected ASGI message 'websocket.send', after sending 'websocket.close'.
  ```
* **The Root Cause**: When a user closed or refreshed a browser tab, Uvicorn closed the socket connection. The background broadcast loop in `websocket_endpoint` concurrently attempted `await ws.send_text()`, raising a benign `RuntimeError` / `WebSocketDisconnect`.
* **The Resolution**: Caught `(WebSocketDisconnect, RuntimeError)` gracefully in `web_app.py`:
  ```python
  try:
      while True:
          state = manager.snapshot()
          await ws.send_text(json.dumps(state))
          await asyncio.sleep(0.2)
  except (WebSocketDisconnect, RuntimeError):
      pass
  ```

---

### Case 4: The "Climax Top" Problem (Buying at the Peak of a Parabolic Move)
* **The Failure**: Gold spiked rapidly from 4005 to 4020.11. The bot's trailing stop locked profit and closed the trade. 15 seconds later (after cooldown), the bot immediately re-entered a **BUY at 4019.75** (the exact ceiling). Price immediately corrected down to 4016, trapping the bot in drawdown.
* **The Root Cause**: The raw entry condition was simply: `if bid > s.ma: BUY`. Because price was way above the 250-MA, the bot considered `price > MA` a valid signal even when price was $15 overextended and RSI was severely overbought (~80).
* **The Resolution**:
  1. **Overextension Guard (`max_ma_dist`)**: Computes $|\text{Bid} - \text{MA}|$. If distance exceeds threshold (e.g. $5.00), it rejects the entry with status `OVEREXTENDED`.
  2. **RSI Climax Guard (`rsi_filter`)**: Computes 14-period RSI on M1 closed bars. Blocks BUY if $RSI \ge 70$, blocks SELL if $RSI \le 30$.

---

### Case 5: The Runaway 5-Leg Short Trap (Grid Loss Runaway)
* **The Failure**: Gold entered a powerful bull rally. The bot took an initial SELL at 3997.87. As gold pumped through 4007, 4012, 4016, and 4018, the bot added Leg 2, 3, 4, and 5 (`grid-add`), accumulating 0.05 lots total against a \$25 runaway rally, producing a -$60 floating loss on a \$126 account.
* **The Root Cause**:
  1. Default parameter `side` was set to `"both"`. Whenever price dipped for even one tick below the M1 MA, it initiated a short position against the dominant multi-hour bull trend.
  2. Small account leverage: On 0.05 lots of Gold, each \$1 move costs \$5. On a \$60–\$120 account, 5 stacked legs exhausted available margin.
* **The Resolution**:
  1. Added **Direction Bias Selector** (`side`): `Both`, `Buy Only` (Bullish), or `Sell Only` (Bearish). Setting `Buy Only` during bull sessions completely eliminates shorts.
  2. Hardened **Grid Max Legs**: Recommended `grid_max_legs = 2` on accounts under \$200.
  3. Added **Emergency Grid SL**: Hard dollar cutoff (default \$15.00) to cut failing baskets before margin calls.

---

### Case 6: Open Positions Displaying "U" (User) Instead of "B" (Bot)
* **The Failure**: All 5 bot-executed SELL orders were flagged with a `[U]` badge on the dashboard.
* **The Root Cause**: The HTML template had been reloaded, looking for `p.is_bot`. However, the background Python process hadn't been restarted, so `p.is_bot` was `undefined` in JSON.
* **The Resolution**: Updated the frontend to check the MT5 Magic Number directly:
  ```javascript
  const isBot = Boolean(p.is_bot || (p.magic && p.magic > 0));
  ```
  In MetaTrader, manual human orders always carry `magic == 0`, while the bot tags all its orders with `magic == 123790`.

---

### Case 7: Broker Account Lockout (Order Flooding from Margin Rejection)
* **The Failure**: The broker locked the user's account with:
  *"algo is trying to place orders without sufficient margin or funds"*.
* **The Root Cause**: Free margin dropped below \$8.04. When the bot attempted an entry, MT5 rejected the deal with `10019 (TRADE_RETCODE_NO_MONEY)`. Because no cooldown was enforced on failed orders, the `on_tick` loop (running 10–50 ticks/second) **re-sent the rejected order on every single incoming tick**, flooding the broker's server with hundreds of rejected orders per minute.
* **The Resolution**:
  1. **Pre-Check Margin (`check_margin`)**: Calls `mt5.order_calc_margin()`. Verifies that $\text{FreeMargin} \ge \text{Margin}_{\text{needed}} \times 1.20$ and $\text{FreeMargin} \ge \$10.00$ locally before `order_send` is ever called.
  2. **Anti-Flood 60s Silencing Cooldown**: If an order fails or margin pre-check fails:
     ```python
     s.last_exit = tc
     s.margin_cooldown_until = tc + 60
     s.status = f"MARGIN GUARD: {rc}"
     ```
     The engine refuses to send orders for 60 seconds, completely preventing flood lockouts.

---

### Case 8: Misunderstanding "Max MA Distance = 1"
* **The Issue**: The user set `Max MA Distance = 1` thinking it would make entries faster, but the bot waited forever.
* **The Root Cause**: `max_ma_dist` is an upper ceiling ($|\text{Bid} - \text{MA}| \le \text{Threshold}$). If distance was \$5.28, setting it to 1 blocked everything until price was within \$1.00 of the MA.
* **The Clarification**: Documented calibration: `0` = Off, `5.0 – 8.0` = Gold balanced, `1.0 – 2.0` = Ultra-tight touch.

---

## 3. Comprehensive Feature Catalog

### 1. Strategy Engine (`up_down_tracker_win_bot_xauusd.py`)
* **MA Trend Following**: 250-period SMA on M1/M5.
* **Direction Bias**: `both`, `buy` only, or `sell` only.
* **Overextension Guard**: Rejects entries when price is overstretched from the MA.
* **RSI Climax Guard**: Rejects BUY $\ge 70$, rejects SELL $\le 30$.
* **Margin Pre-Check**: Native `order_calc_margin` check with 20% safety buffer.
* **Anti-Flood Silencing**: 60-second cooldown on rejected deals.
* **Break Time ☕**: Gracefully finishes active positions; halts all new entries once flat.
* **Dynamic Trailing Stop**: Dynamic peak tracker with percentage giveback and minimum profit lock.
* **Grid Loss Averaging**: Multi-leg averaging down with leg caps and emergency basket stop loss.
* **Time Caps**: Soft time cap (exits at profit $\ge \$0$ after 45m) and hard emergency cap (6 hours).

### 2. Live Web Dashboard (`web_app.py` & `templates/index.html`)
* **Light / Dark Theme**: Persistent financial light mode by default with dark mode toggle.
* **Top Control Bar**: Start/Stop button, "Allow Real" safety interlock, "☕ Break Time" toggle button, "⚠️ Close All" panic button, and Settings modal.
* **Real-Time Entry Telemetry & MA Radar**:
  * Calculates live MA, current distance from MA (`|Bid - MA|`), and user-configured `Max MA Dist`.
  * Computes exact target entry price and condition (e.g. `BUY: <= 2732.50 (Drop -$2.50)` or `In Zone - Ready`) in real time, active continuously even when bot is stopped.
  * Radar banner with pulsing status dot, mode badge (`BOTH`, `BUY`, `SELL`), and descriptive engine state headlines.
* **Live Telemetry (5 Hz via WebSockets)**: Bid/Ask with flash animations, Spread, MA-250, RSI-14, Basket P&L, Daily Goal Meter.
* **Account Info**: Equity, Balance, Free Margin, and Margin Level % in real time.
* **Dual Positions Tabs**:
  * **Open Positions**: Live P&L, lot size, entry price, and `[B]` (Bot) / `[U]` (User) badges.
  * **Closed Trades**: Historical audit table with entry & exit prices, close timestamps, and realized P&L.
* **Audit Event Log**: Streaming terminal box logging all engine signals (`ENTRY`, `CLOSE`, `SKIP`, `PANIC`).

---

## 4. Instructions for Future AI Agents

When tasked with modifying, refactoring, or extending this codebase, **adhere strictly to these rules**:

### Rule 1: Always Run the Offline Self-Test First
Before and after touching `up_down_tracker_win_bot_xauusd.py`, run:
```powershell
& "C:\Users\dayam\AppData\Local\Programs\Python\Python311\python.exe" up_down_tracker_win_bot_xauusd.py selftest
```
All **44 unit checks** must pass. If you add a feature, add a corresponding test check in `selftest()`.

### Rule 2: Never Remove the Margin Pre-Check or Anti-Flood Cooldown
Never bypass `check_margin()` or remove `margin_cooldown_until`. Doing so risks broker lockout for order spamming.

### Rule 3: Git Hygiene & Windows Sandbox Precautions
* **Branching**: Do not modify production `main` directly during active live trading. Branch out (`git checkout -b feature/...`), commit, verify with `selftest`, and merge.
* **Terminal Sandbox vs. IPC**:
  * Standard code editing and git commands run inside the sandbox (`BypassSandbox: false`).
  * Commands interacting with live MT5 (`mt5.initialize()`, `mt5.positions_get()`) or pushing to GitHub (`git push`) require network/IPC and must run with `BypassSandbox: true`.
* **Line Endings**: When modifying files on Windows, maintain LF (`\n`) to prevent target matching mismatches.

### Rule 4: Small Account Safety Defaults
When testing or assisting the user, never advise setting `grid_max_legs > 2` or `lots > 0.01` on accounts with balance $< \$200$. Always pair grid averaging with an `Emergency Grid SL` of \$15.00–\$20.00.

