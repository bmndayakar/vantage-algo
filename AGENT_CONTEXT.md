# AGENT_CONTEXT.md — Vantage Algo Master Knowledge Base

> **Target Audience**: Any AI Agent, Pair Programmer, or Developer picking up this codebase.  
> **Primary Repository**: `https://github.com/bmndayakar/vantage-algo.git`  
> **Branch**: `main`  
> **Last Updated**: 2026-10-27 (Production Release v3.0.0 — Multi-Layer Risk Protections & Dual Radar)

---

## 1. Executive Summary & Codebase Anatomy

This repository is an algorithmic trading system, real-time monitoring dashboard, and terminal radar built for **MetaTrader 5 (MT5)**, primarily tuned for **Gold (`XAUUSD`)**, with full multi-asset capability across Forex, Indices, and Crypto.

### File Manifest:
| File | Role | Key Technologies |
| :--- | :--- | :--- |
| `up_down_tracker_win_bot_xauusd.py` | **Core Strategy Engine** | Python 3.11, `MetaTrader5`, `numpy`, `dataclasses`, `argparse` |
| `web_app.py` | **Backend Server & Telemetry** | `FastAPI`, `Uvicorn`, `WebSockets`, `asyncio`, `threading` |
| `terminal_monitor.py` | **Live CLI Radar Monitor** | Python 3.11, `MetaTrader5`, ASCII telemetry (0.5s refresh) |
| `templates/index.html` | **Interactive Frontend UI** | HTML5, Tailwind CSS (CDN), Chart.js, Vanilla JavaScript |
| `bot_config.json` | **Persistent Runtime Settings** | JSON config store loaded and saved across sessions |
| `run_ui.bat` | **One-Click Windows Launcher** | Windows Batch Script (launches `web_app.py` and opens browser) |
| `.env` / `.env.example` | **Credential Secrets** | Auto-login credentials for MT5 terminal (Git-ignored) |
| `SYSTEM_GUIDE.md` | **System & Mathematical Specs** | Markdown reference manual with Mermaid architecture & lifecycle diagrams |
| `README.md` | **Project Readme** | High-level quickstart and feature overview |

---

## 2. Chronological Failure & Debugging Log (Every Real-Time Issue & Resolution)

The following real-time failures occurred during live testing and trading sessions. Future agents **must** study these to avoid re-introducing previous bugs:

### Case 1: Python Architecture & Version Mismatch
* **The Failure**: Launching the bot crashed with:
  ```text
  ModuleNotFoundError: No module named 'MetaTrader5'
  ```
* **The Root Cause**: The user's system initially had Python 3.13 (32-bit) installed. MetaQuotes distributes pre-compiled MT5 wheels exclusively for **64-bit Windows** and supports versions up to Python 3.12 (not 3.13 at time of initial deployment).
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
  2. Hardened **Grid Max Legs**: Recommended `grid_max_legs = 2` or `3` on smaller accounts.
  3. Added **Emergency Grid SL**: Hard dollar cutoff (default \$20.00) to cut failing baskets before margin calls.

---

### Case 6: Open Positions Displaying "U" (User) Instead of "B" (Bot)
* **The Failure**: All bot-executed SELL orders were flagged with a `[U]` badge on the dashboard.
* **The Root Cause**: The HTML template had been reloaded, looking for `p.is_bot`. However, the background Python process hadn't been restarted, so `p.is_bot` was `undefined` in JSON.
* **The Resolution**: Updated the frontend to check the MT5 Magic Number directly:
  ```javascript
  const isBot = Boolean(p.is_bot || (p.magic && p.magic > 0));
  ```
  In MetaTrader, manual human orders carry `magic == 0`, while the bot tags all its orders with `magic == 123790` and recovery scalps with `magic == 789998`.

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

### Case 9: The "Falling Knife" Trap & Pullback Rejection Solution
* **The Failure**: In Classic mode, when price dipped toward the MA, the bot entered a BUY immediately the instant price touched the upper band. However, during strong selloffs, price was cascading downward with momentum, immediately putting the new BUY into deep drawdown.
* **The Resolution**: Engineered the **Pullback Rejection Engine (`entry_mode: "pullback"`)**:
  - Requires price to pull back to the MA zone ($|\text{Bid} - \text{MA}| \le \text{pullback\_zone}$, e.g. \$3.00).
  - Dynamically tracks the trough (for BUY) or crest (for SELL).
  - Demands a confirmed bounce of at least `pullback_rejection_dist` (e.g. +\$0.60) before firing the entry order.
  - Completely stops buying falling knives and selling into parabolic upward spikes.

---

### Case 10: The Stuck Max-Legs Drawdown & Break-Even Bailout Solution
* **The Failure**: When a grid reached its max leg limit (e.g. 3 legs), it was stuck deep underwater needing a huge market rebound to reach the full target profit (`+$2.00`), exposing the account to prolonged drawdown.
* **The Resolution**: Created **Max-Legs Bailout (`bailout_on_max_legs: True`, `bailout_target: 0.05`)**:
  - The instant $N_{\text{open}} \ge N_{\text{max}}$, the profit target drops from $+\$2.00$ down to $+\$0.05$ (break-even plus minor commission buffer).
  - The basket escapes at zero loss on the very first small market retracement instead of greedily waiting for full profit.

---

### Case 11: Trend Invalidation Runaway & Dynamic Trend Cut Solution
* **The Failure**: A buy basket was opened during an uptrend, but a major macroeconomic news event caused Gold to break completely below the 250-MA and enter a sustained multi-hour bear trend. The grid continued holding hope while price plummeted \$30.
* **The Resolution**: Built the **Trend Invalidation Stop (`trend_stop_dist: 6.00`)**:
  - If a BUY basket is open and price plunges to $\text{Bid} < \text{MA} - \text{trend\_stop\_dist}$, the trend has failed. The bot liquidates the basket immediately.
  - If a SELL basket is open and price spikes to $\text{Bid} > \text{MA} + \text{trend\_stop\_dist}$, the downtrend has failed and the basket is cut.

---

### Case 12: Direction Bias "Both" Radar Truncation / Single Side Masking
* **The Issue**: When direction bias was configured as `BOTH` (Buy & Sell), the Entry Radar previously picked only whichever side price happened to be on (e.g. if price was above MA, it only showed BUY conditions; SELL was completely invisible).
* **The Resolution**: Upgraded `compute_entry_telemetry()` to calculate both BUY and SELL conditions simultaneously on every tick. The UI renders dual color-coded badges (Emerald BUY and Rose SELL) with live distances, target prices, and pulse dots.

---

### Case 13: Windows Sandbox MT5 IPC Isolation vs Bypass Mode
* **The Failure**: Running Python commands that call `mt5.initialize()` inside standard sandbox mode hung indefinitely or timed out.
* **The Root Cause**: Standard Windows Sandbox isolates named pipes and inter-process communication (IPC) between the sandbox container and host desktop processes (`terminal64.exe`).
* **The Resolution**: All commands connecting to live MT5 terminals must be executed with `BypassSandbox: true` (or via external terminal scripts like `terminal_monitor.py`), while static scripts, unit tests, and compilers run sandboxed.

---

### Case 14: Multi-Account Auto-Discovery and Seamless Account Switching
* **The Issue**: When MT5 was already open and logged in, the UI previously popped up a login modal asking the user to manually enter their account number, password, and server. Furthermore, there was no way to easily switch between multiple accounts.
* **The Resolution**:
  1. Updated `web_app.py` and `up_down_tracker_win_bot_xauusd.py` to prioritize attaching directly to the running MT5 terminal session via `mt5.initialize()` without arguments. Zero credentials or login screens required when MT5 is already active.
  2. Implemented `get_available_accounts()` which automatically scans active MT5 accounts, terminal authorization logs (`data_path/logs/*.log`), and `saved_accounts.json`.
  3. Built an interactive **Account Switcher Dropdown** in the dashboard header showing the active account pill (`#Login • Server • Balance • DEMO/REAL`), allowing instant 1-click switching between accounts with live synchronization when accounts are changed inside MT5 desktop.

---

### Case 15: Dynamic Global Tooltip Portal & Collision Edge Detection
* **The Issue**: Inline static CSS tooltips (`position: absolute`) were getting truncated at card boundaries due to parent `overflow-hidden` (such as Card 1 and Card 2) or getting hidden underneath subsequent sections due to nested stacking contexts. Top-row badges (like `TREND: BEARISH`) also popped upwards off-screen or were cut in half.
* **The Resolution**:
  1. Replaced nested inline tooltip rendering with a **Dynamic Global Tooltip Portal** (`#global-tooltip`) mounted directly onto `document.body` with `position: fixed` and `z-index: 999999`. This renders above all elements and is 100% immune to parent `overflow-hidden`, scrolling table clipping, or section stacking contexts.
  2. Implemented real-time **Collision & Viewport Edge Detection**:
     - *Vertical Collision*: Measures available space above vs. below. If top room is $< \text{height} + \text{gap} + \text{margin}$, it dynamically flips to display **BELOW** the target (`arrow-up`), preventing top-boundary clipping.
     - *Horizontal Clamping*: Calculates anchor center and clamps the box within viewport borders ($12\text{px}$ safety margin) on both left and right edges.
     - *Pinpoint Dynamic Arrow*: Calculates relative anchor offset and slides the arrow along the box edge so it always points precisely at the `ⓘ` icon without protruding past rounded corners.
  3. Added scroll & resize dismiss listeners (`capture: true`) and touch device toggle support. Removed unnecessary `overflow-hidden` classes from Card 1 and Card 2.

---

### Case 16: MT5 Broker Server Time vs Local IST Timezone Synchronization
* **The Issue**: Trade entry and exit timestamps in the web dashboard were shifted 2 hours into the future, and users were uncertain whether the MT5 desktop terminal itself displays IST time.
* **The Root Cause**:
  1. **MT5 Desktop Behavior**: MetaTrader 5 desktop client by design strictly displays **Broker Server Time** (EET, UTC+2 / UTC+3) in its charts, Market Watch, and Trade History. It has no native setting to convert history to the user's local operating system timezone (IST).
  2. **Timestamp Double-Offset Bug**: MT5 Python API returns timestamp integers representing the broker's server wall-clock time. When passed directly to Python's `datetime.fromtimestamp().astimezone()` on an IST machine, Python assumed the timestamp was UTC and added another +5:30 on top of the server's +2:00, resulting in a +7:30 offset (+2 hours ahead of real IST).
  3. **Open Position Duration Bug**: Calculating age via `time.time() - p.time` subtracted a Server timestamp (19:00) from a UTC timestamp (17:00), causing negative/0s duration.
* **The Resolution**:
  1. Added `get_server_offset()` in `web_app.py` to automatically detect the broker server's UTC offset from live ticks (typically UTC+2.0 EET).
  2. Implemented `format_mt5_time(epoch_seconds, server_offset_hours)` which converts:
     $$\text{Server Wall Clock} - \text{Server Offset} = \text{True UTC} \longrightarrow \text{True IST (UTC+5:30)}$$
  3. Standardized position age calculations using normalized server timestamps.
  4. Updated Open and Closed position tables in `templates/index.html` to prominently show exact **Indian Standard Time (IST)**, while also displaying the corresponding MT5 Server Time underneath for instant 1:1 cross-referencing with the MT5 desktop client.

---

### Case 17: Proportional Lot-Size Auto-Scaling & Post-Loss Anti-Rally Pause
* **The Issue**: When testing with `lots = 0.10` instead of `0.01` during a \$43 Gold rally, the bot incurred rapid successive losses (86 stop-outs, -\$727.38).
* **The Root Cause**:
  1. **Fixed Dollar vs Volume Distortion**: On XAUUSD, a \$1.00 move equals \$1.00 P&L on 0.01 lots, but equals \$10.00 P&L on 0.10 lots. Fixed dollar thresholds (`grid_step_loss = $10.00`, `grid_sl = $20.00`) meant that on 0.10 lots, normal 50-cent to \$1.00 price noise tripped Leg 2 and Leg 3 immediately, and hit `grid_sl = $20` after only a 66-cent move across 3 legs.
  2. **Anti-Chop Cooldown Insufficiency in Violent Trends**: After stopping out, the bot only waited 15 seconds (`min_entry_gap_sec = 15`) before immediately opening another position directly into the runaway trend, creating an 86-cycle loss spiral.
* **The Resolution**:
  1. **Point 1 (Proportional Lot Auto-Scaling)**:
     - Added `scale_by_lots: bool = True` and `base_lot: float = 0.01` to `Cfg`.
     - Calculated dynamic lot multiplier: $\text{lot\_mult} = \frac{\text{lots}}{\text{base\_lot}}$ (e.g. 10.0x for 0.10 lots).
     - Scaled all dollar-based price distance thresholds dynamically via property getters:
       `eff_grid_step_loss`, `eff_grid_sl`, `eff_trail_arm`, `eff_trail_min_lock`, `eff_grid_tp`, `eff_target_profit`, `eff_bailout_target`, `eff_recycle_tp`, `eff_recycle_sl`, and `eff_stop_loss`.
     - Preserves exact market price distances ($10 Gold move per grid step, $1 move for trail arm, $0.20 move for TP target) invariant of lot size.
  2. **Point 2 (Extended Post-Loss Anti-Rally Pause)**:
     - Added `loss_cooldown_sec: int = 180` (3 minutes default).
     - Updated catastrophic stop-loss triggers (`grid-sl`, `trend-inval`, `equity-risk-sl`, `stop-loss`, and losing `time-hard`) to call `close_all(loss_pause=True)`.
     - Enforced `s.loss_cooldown_until = tc + loss_cooldown_sec` which halts new entries with status `PAUSED AFTER LOSS <rem>s` to allow the runaway market to calm before re-engaging.
  3. **UI Integration**:
     - Added `Proportional Lot Auto-Scaling` and `Post-Loss Pause` controls to Settings modal.
     - Live preview calculation in margin box displays effective scaled values.
     - Red/rose pulsing visual badge in header telemetry and Entry Radar whenever a post-loss pause is active.
     - Self-test suite expanded to 66 passing checks covering scaling math, grid step spacing on 0.10 lots, and post-loss cooldown enforcement.

---

### Case 18: Lever 1 — Empirical Trade Excursion Telemetry (MAE & MFE)
* **The Inquiry & Context**: User explored whether 0.5-second clock logs could make the bot "almost no loss". 
* **The Architectural Insight**:
  1. Fixed time sampling (0.5s) produces redundant flat logs during quiet sessions and misses 90% of micro-ticks during fast news bursts; sub-second indicators result in spread churn.
  2. The pursuit of "zero loss" leads to runaway martingales. Sustainable quantitative profitability requires **Positive Mathematical Expectancy** with controlled, asymmetric losses.
  3. Real algorithmic optimization requires **Event-Driven Trade Excursions**: Maximum Favorable Excursion (MFE: highest unrealized profit) and Maximum Adverse Excursion (MAE: deepest unrealized drawdown).
* **The Resolution**:
  1. Updated `Bot` class to track `s.peak` (MFE) and `s.mae` (MAE) continuously on every incoming tick.
  2. Added `mfe,mae` columns to `up_down_tracker_decisions_py.csv`.
  3. Added persistent excursion storage in `trade_excursions.json` managed by `BotManager`.
  4. Updated Open and Closed positions tables in `templates/index.html` to display live and historical `Peak (+$MFE)` and `Dip (-$MAE)` with explanatory tooltips.
  5. Established [`DEV_JOURNAL.md`](file:///c:/Users/dayam/Documents/vantage-algo/DEV_JOURNAL.md) documenting the complete development chronicle and engineering journey.
  6. Self-test suite expanded to **69 passing checks**.


### Case 19: 100% MT5 API Ground-Truth Synchronization (Positions & Deal Lifecycle Reconstruction)
* **The Inquiry & Context**: User noticed that open and closed trades in the web app were not matching trade history in MT5 desktop, and proposed: *"Is it a good idea to always get that data from mt5? What i am proposing is that get those trade details from mt5 always whether open or closed."*
* **The Architectural Insight**:
  1. **MT5 as Ground Truth**: In algorithmic trading, the broker terminal is the single authoritative source of truth for executions, volume fills, commissions, swaps, and realized net PnL.
  2. **Why Discrepancies Existed Previously**:
     - **Missing Ticket Numbers**: MT5 desktop indexes every position by its unique 64-bit Ticket ID, whereas the web dashboard omitted ticket IDs, making row-by-row matching impossible.
     - **48-Hour Hardcoded Query Window**: Web app only queried deals from `now - 2 days`. If a trade was opened 3 days ago and closed today, its entry deal was omitted from the query, displaying `$0.00` open price and `0s` duration.
     - **Multi-Fill Scale-In Overwrite**: The grid recovery engine often scales into a position across multiple legs. The previous `{d.position_id: d}` dictionary comprehension dropped earlier entry deals and distorted the volume-weighted open price.
     - **Missing Asset Symbol**: Closed trade records omitted `symbol`.
* **The Resolution**:
  1. Built `reconstruct_closed_positions()`: Reconstructs closed positions by aggregating all deals sharing a `position_id`, computing volume-weighted entry fill prices, volume-weighted exit fill prices, net realized PnL (`profit + swap + commission`), and exact durations.
  2. Dynamic Missing Entry Fallback: If an entry deal occurred outside the queried date window, queries `mt5.history_deals_get(position=pos_id)` on-demand.
  3. Interactive Period Filter: Added `[ Today | 3D | 7D | 30D | All ]` history selector in `templates/index.html` backed by `POST /api/history_period` and WebSocket updates.
  4. UI Enhancements: Added `#Ticket` monospace labels, asset symbols, SL/TP tags, and Net PnL tooltips with commission/swap breakdowns.
  5. Verified with 4 unit tests in `scratch/test_mt5_sync.py` and all 69 core bot self-tests passing.
---


### Case 20: Session Goal Isolation, Broker Server Timezone Midnight & UI Layout Rebalancing
* **The Inquiry & Context**:
  1. *"without executing trades, why is it showing progress in daily goal and showing 17 deals close."*
  2. *"Also the under buttons in history 3D, 3D, today etc are not working."*
  3. *"Another thing we can work on is to adjust the size of session P&L trajectory section and trades section. We don't need such long session trajectory occupying the screen."*
* **The Root Causes**:
  - **Daily Goal Over-counting**: The bot engine queried MT5 broker deals for the entire calendar day to track `daily_profit()`. If the user ran tests earlier in the day, the bot booted up with `$15.20 / $20` and `17 Deals Closed`, locking into `GOAL REACHED` or causing confusion.
  - **Timezone Drift on "Today" Filter**: In early morning IST (UTC+5:30), the MT5 broker server (EET/UTC+2) was still on the previous calendar day. Calculating midnight using local machine time created a start date 1.5–3.5 hours in the *future* relative to the broker server, returning zero deals.
  - **Screen Real Estate Imbalance**: Section 3 dedicated 2/3 width to the trajectory chart, crowding the open and closed trade ledgers.
* **The Resolution**:
  1. **Session-Isolated Tracking**:
     - Added `s.session_profit = 0.0` and `s.session_deals = 0` in `Bot.__init__` and `BotManager`.
     - Incremented on `close_all()` / basket close.
     - Card 5 now displays active `Session Goal` starting at `$0.00` and `0 Deals`, with cumulative MT5 calendar day stats displayed cleanly in the subtitle: `Day: $XX.XX (17)`.
     - Added `[ ↺ Reset ]` button in the UI backed by `POST /api/reset_goal`.
  2. **Broker Server Midnight Date Alignment**:
     - Formulated `server_midnight` using UTC plus `server_offset`:
       `server_midnight = (datetime.utcnow() + timedelta(hours=server_offset)).replace(hour=0, minute=0, second=0)`
     - Aligned history query for `"today"` to `server_midnight`, ensuring consistent retrieval of all trades executed on the broker's current day.
     - Added optimistic button styling for instant visual feedback on click.
  3. **Section 3 Rebalancing**:
     - Expanded Positions & Trades card to `lg:col-span-2` (wide 2/3) with `max-h-[285px]` scrollable container.
     - Compacted Session P&L Trajectory chart to `lg:col-span-1` (compact 1/3) with height reduced to `160px–175px`.
  4. Verified with full test suite: 69/69 self-test pass, 4/4 MT5 sync pass.

---

## 3. Comprehensive Feature Catalog

### 1. Strategy Engines (`up_down_tracker_win_bot_xauusd.py`)
* **Pullback Rejection Engine (`entry_mode: "pullback"`)**:
  * Dip & rally zone tracking (`pullback_zone = 3.00`).
  * Dynamic trough/crest tracking and bounce confirmation (`pullback_rejection_dist = 0.60`).
* **Classic MA Mode (`entry_mode: "classic"`)**:
  * Direct level and cross execution.
* **Direction Bias**: `both`, `buy` only, or `sell` only.
* **Overextension Guard**: Rejects entries when price is overstretched from the MA (`max_ma_dist`).
* **RSI Climax Guard**: Rejects BUY $\ge 70$, rejects SELL $\le 30$.
* **Automated Loss Recycler (`loss_recycler: True`)**:
  * Detects stalled grids in drawdown.
  * Opens counter recovery scalps (`magic_recovery = 789998`) on verified bounces.
  * Uses recovery TP to automatically close/prune the worst underwater grid leg.
* **Max-Legs Break-Even Bailout (`bailout_on_max_legs: True`)**:
  * Lowers target to `+$0.05` once max legs are reached.
* **Trend Invalidation Stop (`trend_stop_dist = 6.00`)**:
  * Emergency cut if price crosses past MA against the trade.
* **Max Equity Risk Stop (`max_equity_risk_pct = 20.0`)**:
  * Hard account equity loss ceiling.
* **Emergency Basket SL (`grid_sl = 20.00`)**:
  * Hard dollar catastrophe cutoff.
* **Margin Pre-Check**: Native `order_calc_margin` check with 20% safety buffer.
* **Anti-Flood Silencing**: 60-second cooldown on rejected deals.
* **Break Time ☕**: Gracefully finishes active positions; halts all new entries once flat.
* **Dynamic Trailing Stop**: Dynamic peak tracker with percentage giveback and minimum profit lock.
* **Time Caps**: Soft time cap (exits at profit $\ge \$0$ after 45m) and hard emergency cap (2 hours).

### 2. Live Web Dashboard (`web_app.py` & `templates/index.html`)
* **Financial Light / Dark Theme**: Persistent financial light mode by default with dark mode toggle.
* **Top Control Bar**: Start/Stop button, "Allow Real" safety interlock, "☕ Break Time" toggle button, "⚠️ Close All" panic button, and Settings modal.
* **Real-Time Entry Telemetry & Dual Radar**:
  * Computes live MA, distance from MA, and user-configured `Max MA Dist`.
  * Dual condition rendering when Direction Bias is `BOTH`: Side-by-side Emerald BUY and Rose SELL badges with exact price triggers and dollar distances.
  * Single-direction filtering when `BUY` or `SELL` is selected.
  * Animated radar status beacon with descriptive engine state headlines.
* **Expanded Market Price Slate (Card 1)**:
  * 2-column wide layout: Live Bid/Ask/Spread on left, MA-250, RSI-14, MA Distance, Max Cap, and dual stacked Waiting Prices on right.
* **Live Telemetry (5 Hz via WebSockets)**: Real-time quotes, Basket P&L, Daily Goal Meter.
* **Dual Positions Tabs**: Open positions with `[B]` (Bot) / `[U]` (User) / `[RECOVERY]` badges, and closed historical audit table.

### 3. Live Terminal Monitor (`terminal_monitor.py`)
* Dedicated CLI dashboard with **0.5s auto-refresh**.
* ASCII radar displaying engine status, market quotes, MA/RSI indicators, open positions table with floating P&L and tags, and active safety guard indicators.

---

## 4. Instructions for Future AI Agents

When tasked with modifying, refactoring, or extending this codebase, **adhere strictly to these rules**:

### Rule 1: Always Run the Offline Self-Test First
Before and after touching `up_down_tracker_win_bot_xauusd.py`, run:
```powershell
python up_down_tracker_win_bot_xauusd.py selftest
```
All **55 unit checks** must pass. If you add a feature, add a corresponding test check in `selftest()`.

### Rule 2: Never Remove the Margin Pre-Check or Anti-Flood Cooldown
Never bypass `check_margin()` or remove `margin_cooldown_until`. Doing so risks broker lockout for order spamming.

### Rule 3: Git Hygiene & Windows Sandbox Precautions
* **Branching**: Do not modify production `main` directly during active live trading. Branch out, commit, verify with `selftest`, and merge.
* **Sandbox & MT5 IPC**: Live MT5 queries require IPC and need `BypassSandbox: true` if executed from tool calls.
* **Line Endings**: Maintain consistent line endings across Windows and Unix platforms.

### Rule 4: Small Account Safety Defaults
When assisting users or configuring bots:
* For accounts $< \$200$: Set `grid_max_legs = 2` or `3`, `lots = 0.01`, `grid_sl = 20.00`, and `bailout_on_max_legs = True`.
* Recommend `entry_mode = "pullback"` for calmer, higher-probability entries on Gold (`XAUUSD`).
