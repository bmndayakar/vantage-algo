# Vantage Algo - Multi-Asset MT5 Trading Bot & Real-Time Dashboard

A robust, multi-asset algorithmic trading bot with an interactive real-time web dashboard for **MetaTrader 5 (MT5)**.

Built originally for Gold (`XAUUSD`), now extended to support any tradeable instrument (Forex majors, Indices, Crypto, Commodities) on your broker.

---

## Key Features

* **Algorithmic Strategy**:
  * **Trend Filter**: 250-period Simple Moving Average (SMA) on configurable timeframes (M1, M5, M15).
  * **Loss-Grid Averaging**: Dynamic leg scaling on pullbacks with customizable step loss and maximum leg cap.
  * **Profit-Peak Trailing Stop**: Arms when floating profit exceeds threshold, tracking the highest peak and locking in gains.
  * **Time Caps**: Soft time cap (exits only at profit $\ge \$0.00$) and emergency hard stop loss.
  * **Spread Protection**: Built-in maximum spread guard to avoid market-open slippage spikes.

* **Real-Time Web Dashboard (`web_app.py`)**:
  * **Financial Light & Dark Mode** with 1-click persistent toggle (`☀️` / `🌙`).
  * **Live Telemetry via WebSockets** (streaming 5 times/second): Bid, Ask, Spread, MA-250, Basket Floating P&L, Daily Goal meter.
  * **Market Open/Closed Status Indicator** (`🟢 LIVE` / `⚪ CLOSED`).
  * **Active Session P&L Trajectory Chart** (powered by Chart.js).
  * **Controls**: Start/Stop Bot, Emergency "Close All" panic button, and live parameter tuning.
  * **MT5 Login Modal**: Connects and auto-launches MT5 directly from the browser if no session is active.

* **Simulation & Analytics Suite**:
  * **Tick-Level Backtester**: Replays raw historical MT5 ticks with realistic slippage and commission models.
  * **Walk-Forward Optimizer**: Rolling out-of-sample forward testing against overfitting.
  * **Deterministic Self-Tests**: 10 unit checks verifying all strategy branches offline without needing MT5.

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

### 4. Running via Terminal / CLI
```bash
# Self-test (offline check)
python up_down_tracker_win_bot_xauusd.py selftest

# Run on Demo account
python up_down_tracker_win_bot_xauusd.py run

# Run on Real account
python up_down_tracker_win_bot_xauusd.py run --allow-real

# Backtest last 30 days on EURUSD
python up_down_tracker_win_bot_xauusd.py backtest --symbol EURUSD --days 30
```

---

## Documentation & Complete Guide
For the full architectural breakdown, mathematical formulas, state machine lifecycle diagrams, and parameter reference tables, see:
👉 **[SYSTEM_GUIDE.md](file:///c:/Users/dayam/Documents/vantage-algo/SYSTEM_GUIDE.md)**

---

## Configuration (`.env`)
To auto-launch and log into MT5 automatically, copy `.env.example` to `.env`:
```env
MT5_PATH=C:\Program Files\MetaTrader 5\terminal64.exe
MT5_LOGIN=12345678
MT5_PASSWORD=your_password
MT5_SERVER=VantageFX-Live
```
*(Credentials in `.env` are strictly git-ignored).*

