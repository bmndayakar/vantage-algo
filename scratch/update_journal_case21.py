import re

# 1. Update DEV_JOURNAL.md
with open("DEV_JOURNAL.md", "r", encoding="utf-8") as f:
    dev_content = f.read()

target_sec10 = "## 10. Current System Architecture & Roadmap"

chapter_9_text = """## 10. Chapter 9: The Offline Trade Ledger & Institutional Timeframe Analyzer

### The Inquiry & Need
The user asked:
*"are you storing all the closed trades offline along with date time stamp?"*
*"yes i want you to record every executed trade with all the details which is very useful to go back and analyze data. Especially to understand what is the best time frame to do trading for max profits"*

### The Architectural Problem
In live algorithmic trading, relying strictly on in-memory dynamic API queries to MT5 has several risks:
1. **Data Loss / Rollover**: When demo accounts expire, broker logs roll over, or MT5 history is cleared, trade records are permanently lost.
2. **Missing Time-of-Day Dimensions**: MT5 stores raw timestamps, but quantitative performance analysis requires session classification (Tokyo vs. London vs. London/NY Overlap vs. New York), hourly distribution (IST), holding duration brackets, price deltas, and excursion ratios ($MFE/MAE$).
3. **No Direct Offline Data Science Tooling**: Traders need a standalone CSV ledger that can be opened in Excel or analyzed via Python with one command.

### The Solutions Implemented
1. **Automated Offline Trade Persistence (`closed_trades.csv`)**:
   - Built `sync_closed_trades_to_csv()` in `web_app.py`.
   - Records every executed trade with zero duplicates, keyed by 64-bit MT5 Ticket ID.
   - Enriches each trade with 29 comprehensive dimensions:
     - Identification: `ticket`, `symbol`, `type`, `volume`, `magic`, `trade_tag` (`[BOT]`, `[USER]`, `[RECOVERY]`).
     - Timing & Timezones: `open_time_ist`, `open_time_server`, `close_time_ist`, `close_time_server`, `open_hour_ist`, `close_hour_ist`, `day_of_week`.
     - Market Sessions: Automatic classification into `Asian (Tokyo)`, `London`, `London/NY Overlap`, `New York`, and `Pacific/Late US`.
     - Durations: Exact `duration_sec`, formatted `duration_str`, and scalping bracket `timeframe_tag` (`< 1 min`, `1 - 5 min`, `5 - 15 min`, etc.).
     - Pricing: `open_price`, `close_price`, `price_diff` (points in favor of trade).
     - Financials: `gross_profit`, `commission`, `swap`, `net_pnl`, `pnl_per_lot` (normalized per 1.00 lot), `outcome` (`WIN`/`LOSS`/`BE`).
     - Excursion Telemetry: Peak favorable excursion (`mfe`), deepest drawdown (`mae`), and `mfe_mae_ratio`.
   - **Continuous Background Auto-Sync**: Automatically updates whenever a trade closes or new excursion telemetry is measured.
   - **90-Day Startup Catchup**: Automatically populates existing historical trades from MT5 on first boot or account switch.
2. **One-Click Web Export (`/api/export_trades_csv`)**:
   - Added `[ ⬇ Export CSV ]` button directly to the Closed Trades tab in the dashboard for instant browser download.
   - Added `GET /api/trade_analytics` endpoint for programmatic analysis.
3. **Institutional Quantitative Analyzer (`analyze_trades.py`)**:
   - Created standalone analytics CLI script: `python analyze_trades.py`.
   - Generates an institutional-grade scorecard:
     - **Executive KPIs**: Win Rate, Net PnL, Profit Factor, Expectancy, Payoff Ratio, Average MFE vs MAE.
     - **Market Session Table**: Direct profitability ranking across Tokyo, London, Overlap, and NY.
     - **Hourly Distribution (IST)**: 24-hour visual distribution identifying peak profit hours ("Gold Rush Hours") and hours to avoid.
     - **Holding Duration Analysis**: Compares scalping (< 1m, 1-5m) vs intraday swing performance.
     - **Directional Edge**: BUY vs SELL profitability.
     - **Actionable Strategic Takeaways**: Automatic text synthesis identifying optimal trading windows.
4. **Verification**:
   - Added 5 unit tests in `scratch/test_closed_trades_sync.py` (ALL PASS).
   - Core algo test suite remains 100% green (69/69 PASS + 4/4 MT5 Sync PASS).

---

## 11. Current System Architecture & Roadmap

```
Vantage Algo Status: v2.7 (Institutional Offline Ledger & Timeframe Analytics)
Self-Test Verification: 69/69 PASS + 4/4 MT5 Sync PASS + 5/5 CSV Sync PASS
```

### The Optimization Levers Ahead:
* **[COMPLETED] Lever 1: Trade Excursion Telemetry (MAE/MFE)** — Real-time and historical trade excursion tracking.
* **[COMPLETED] Ground Truth Sync: 1:1 MT5 Desktop Alignment** — Reconstructed positions, ticket IDs, period filter.
* **[COMPLETED] Session Isolation & Timezone Calibration** — Distinct session targets, broker midnight alignment, responsive layout.
* **[COMPLETED] Offline Trade Persistence & Analytics** — 29-column CSV ledger, automatic sync, session/hour/duration analyzer (`analyze_trades.py`).
* **[NEXT] Lever 2: Dynamic ATR Volatility & Spread Expansion Gates** — Automatically widen grid spacing or pause entries when broker spread spikes during economic releases.
* **[UPCOMING] Lever 3: Higher-Timeframe Macro Alignment** — Enforce trend alignment with M15/H1 Moving Averages to ensure the bot rides major momentum waves rather than fighting them.
"""

if target_sec10 in dev_content:
    idx = dev_content.find(target_sec10)
    dev_content = dev_content[:idx] + chapter_9_text
    with open("DEV_JOURNAL.md", "w", encoding="utf-8") as f:
        f.write(dev_content)
    print("DEV_JOURNAL.md updated with Chapter 9!")
else:
    print("target_sec10 not found in DEV_JOURNAL.md")

# 2. Update AGENT_CONTEXT.md
with open("AGENT_CONTEXT.md", "r", encoding="utf-8") as f:
    agent_content = f.read()

case_21 = """
### Case 21: Automated Offline Trade Persistence (`closed_trades.csv`) & Session/Timeframe Analytics (`analyze_trades.py`)
* **The Inquiry & Context**: User requested: *"are you storing all the closed trades offline along with date time stamp? yes i want you to record every executed trade with all the details which is very useful to go back and analyze data. Especially to understand what is the best time frame to do trading for max profits"*
* **The Root Architectural Need**:
  - Previously, closed trades were only retrieved dynamically in-memory from MT5 API (`mt5.history_deals_get()`).
  - If MT5 history rolled over or demo expired, historical audit records were lost.
  - Analyzing "what is the best time frame for max profits" requires structured offline data science columns: entry hour in IST, market session tag, duration brackets, price deltas, normalized PnL per lot, and MFE/MAE ratios.
* **The Resolution**:
  1. **Automated Offline CSV Sync Engine (`closed_trades.csv`)**:
     - Added `sync_closed_trades_to_csv()` in `web_app.py`.
     - Automatically updates on every deal and trade close with deduplication by ticket ID.
     - 29 rich quantitative columns: `ticket`, `symbol`, `type`, `volume`, `open_time_ist`, `open_time_server`, `close_time_ist`, `close_time_server`, `open_hour_ist`, `close_hour_ist`, `day_of_week`, `session_tag`, `duration_sec`, `duration_str`, `timeframe_tag`, `open_price`, `close_price`, `price_diff`, `gross_profit`, `commission`, `swap`, `net_pnl`, `pnl_per_lot`, `outcome`, `mfe`, `mae`, `mfe_mae_ratio`, `magic`, `trade_tag`.
     - 90-day initial catchup on boot to capture existing account history.
  2. **Institutional Analyzer Tool (`analyze_trades.py`)**:
     - Dedicated standalone CLI tool (`python analyze_trades.py`) printing:
       - Executive scorecard: Win Rate %, Net Realized PnL, Profit Factor, Expectancy, Payoff Ratio, Excursion Efficiency.
       - Performance breakdown across Market Sessions (`Asian`, `London`, `London/NY Overlap`, `New York`, `Pacific`).
       - Hourly distribution (00:00 to 23:00 IST) highlighting peak profit hours.
       - Holding duration breakdown (< 1m, 1-5m, 5-15m, 15-60m, > 1h).
       - Directional edge (BUY vs SELL).
  3. **One-Click UI Export**:
     - Added `[ ⬇ Export CSV ]` download button in Closed Trades header in `templates/index.html`.
     - Backed by `GET /api/export_trades_csv` and `GET /api/trade_analytics`.
  4. Verified with 5 unit tests in `scratch/test_closed_trades_sync.py` and 69 core self-tests.
"""

target_case = "## 3. Comprehensive Feature Catalog"
if target_case in agent_content:
    agent_content = agent_content.replace(target_case, case_21 + "\n---\n\n## 3. Comprehensive Feature Catalog")
    with open("AGENT_CONTEXT.md", "w", encoding="utf-8") as f:
        f.write(agent_content)
    print("AGENT_CONTEXT.md updated with Case 21!")
else:
    print("target_case not found in AGENT_CONTEXT.md")

