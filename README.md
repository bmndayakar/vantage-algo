# Vantage Algo - Multi-Asset MT5 Trading Bot & Real-Time Dashboard

A professional, high-performance algorithmic trading system and live monitoring dashboard for **MetaTrader 5 (MT5)**.

Built originally for Gold (`XAUUSD`), engineered to support any tradeable instrument (Forex majors, Indices, Crypto, Commodities) with institutional multi-layer risk controls.

---

## Key Features

* **Advanced Strategy Engines**:
  * **Pullback Rejection Engine (`entry_mode: "pullback"`)**: Eliminates knife-catching by waiting for price to pull back to the Moving Average zone and confirming a bounce/rejection before entering.
  * **Classic MA Trend Following (`entry_mode: "classic"`)**: High-momentum direct MA level and cross signals.
  * **Trend Filter**: 250-period Simple Moving Average (SMA) on configurable timeframes (`M1`, `M5`, `M15`).
  * **Direction Bias Control**: Instant switching between `BOTH` (Buy & Sell), `BUY ONLY` (Bullish), or `SELL ONLY` (Bearish).

* **Multi-Layer Risk & Catastrophe Protections**:
  * **Max-Legs Break-Even Bailout**: When a grid reaches max legs, automatically lowers TP to break-even (`+$0.05`) to escape on the first minor bounce.
  * **Trend Invalidation Stop**: Instantly cuts trades if price breaks past the MA by a configured distance (e.g. `$6.00`), acknowledging trend reversal.
  * **Max Equity Risk Stop**: Hard account equity safety ceiling (e.g. 20%) to prevent critical account damage.
  * **Automated Loss Recycler**: Actively opens counter-recovery scalps on bounces to harvest profits and prune underwater grid legs.
  * **Loss-Grid Averaging**: Dynamic leg scaling on adverse moves with customizable step loss and maximum leg cap.
  * **Profit-Peak Trailing Stop**: Dynamic peak tracker with percentage giveback and minimum profit lock.
  * **Time Caps**: Soft time cap (exits only at profit $\ge \$0.00$ after 45m) and emergency hard cap.
  * **Pre-Check Margin Guard**: Native `order_calc_margin` pre-flight check with 20% buffer and 60-second anti-flood throttling.

* **Real-Time Web Dashboard (`web_app.py`)**:
  * **Dual Condition Entry Radar**: When direction bias is `BOTH`, displays live conditions for both BUY and SELL simultaneously with color-coded status badges and distance calculations.
  * **Expanded Market & Technical Slate**: Live Bid/Ask/Spread, MA-250, RSI-14, MA Distance, and dual waiting targets.
  * **Financial Light & Dark Mode** with 1-click persistent toggle (`☀️` / `🌙`).
  * **Live Telemetry via WebSockets** (5 Hz streaming): Real-time tick quotes, basket P&L, daily goal meter.
  * **Interactive Charting**: Session P&L trajectory curve powered by Chart.js.
  * **Full Controls**: Start/Stop, "Allow Real" safety lock, ☕ Break Time toggle, Emergency "Close All" panic button, and live Settings modal.

* **Live Terminal Monitor (`terminal_monitor.py`)**:
  * Standalone CLI terminal radar with **0.5-second auto-refresh**.
  * ASCII dashboard displaying live technicals, open bot legs with Recovery vs. Grid tags, floating basket P&L, and active safety guards.

* **Simulation & Self-Test Suite**:
  * **Deterministic Self-Tests**: **55 offline unit checks** verifying all strategy logic, risk guards, trailing stop mathematics, and execution rules without MT5.
  * **Tick-Level Backtester**: Replays raw historical ticks with realistic slippage and commission models.
  * **Walk-Forward Optimizer**: Rolling out-of-sample forward testing against overfitting.

---

## Quickstart

### 1. Requirements
* Windows 10 / 11 (64-bit)
* Python 3.11 (64-bit)
* MetaTrader 5 Desktop Terminal

### 2. Installation
Clone the repository and install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Launching the Web Dashboard
Double-click **`run_ui.bat`** or run:
```bash
python web_app.py
```
Your browser will automatically open to `http://localhost:8000`.

### 4. Running the Live Terminal Monitor
Open a separate terminal window and run:
```bash
python terminal_monitor.py
```
Provides a 0.5-second live ASCII radar of bot execution, positions, and technicals.

### 5. Running via Terminal / CLI
```bash
# Offline Self-Test (55 checks)
python up_down_tracker_win_bot_xauusd.py selftest

# Run on Demo account
python up_down_tracker_win_bot_xauusd.py run

# Run on Real account (requires safety override)
python up_down_tracker_win_bot_xauusd.py run --allow-real

# Backtest last 30 days on XAUUSD
python up_down_tracker_win_bot_xauusd.py backtest --symbol XAUUSD --days 30
```

---

## Documentation & Architecture
For the full architectural breakdown, mathematical formulas, state machine lifecycle diagrams, and complete parameter reference:
👉 **[SYSTEM_GUIDE.md](file:///c:/Users/dayam/Documents/vantage-algo/SYSTEM_GUIDE.md)**  
👉 **[AGENT_CONTEXT.md](file:///c:/Users/dayam/Documents/vantage-algo/AGENT_CONTEXT.md)**

---

## Configuration (`.env`)
To auto-launch and log into MT5 automatically, configure `.env`:
```env
MT5_PATH=C:\Program Files\MetaTrader 5\terminal64.exe
MT5_LOGIN=5057915586
MT5_PASSWORD=your_password
MT5_SERVER=MetaQuotes-Demo
```
*(Credentials in `.env` are strictly git-ignored).*
