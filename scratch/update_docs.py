import re

# Update DEV_JOURNAL.md
with open('DEV_JOURNAL.md', 'r', encoding='utf-8') as f:
    dev_content = f.read()

target_dev = '## 9. Current System Architecture & Roadmap'
chapter_8 = '''## 9. Chapter 8: Session Isolation, Timezone Date Calibration & UI Rebalancing

### The Problem
During live demo testing in the early morning (IST), three usability issues emerged:
1. **Unwanted Daily Goal Progress (17 Deals Already Closed)**:
   When launching the bot without executing any trades, Card 5 already displayed progress toward the daily goal and claimed `17 Deals Closed`.
   *Root Cause*: The bot calculated daily profit and deal count using the broker's entire calendar day history. Deals executed during earlier testing sessions hours ago were included, leading to confusion and prematurely triggering the `GOAL REACHED` pause.
2. **Unresponsive History Filter Buttons (`Today`, `3D`, `7D`, etc.)**:
   Clicking the period buttons on the trade history card failed to show today's trades or appeared broken.
   *Root Cause*: Timezone misalignment between local client time and MT5 broker server time. At 01:50 AM IST (UTC+5:30), the broker server (EET, UTC+2) was still at 22:20 on the previous calendar day. Calculating "Today" midnight using naive local machine time created a start date 1 hour 40 minutes in the *future* relative to the broker server, causing MT5 to return zero deals. Furthermore, absence of immediate optimistic styling made the buttons feel unresponsive.
3. **Imbalanced Section 3 Layout**:
   The Session P&L Trajectory Chart occupied 2/3 of the screen width (`lg:col-span-2`) with 240px height, crowding the far more critical Positions and Trades ledger into a narrow 1/3 column (`lg:col-span-1`).

### The Solutions
1. **Session Goal Isolation vs. Calendar Day Total**:
   - Added explicit `session_profit` ($0.00) and `session_deals` (0) tracking to both the bot engine (`Bot`) and web supervisor (`BotManager`).
   - The active Daily Goal meter now strictly tracks the current trading session from launch.
   - Added a `[ ↺ Reset ]` button in the UI backed by `POST /api/reset_goal` allowing manual resets at any time.
   - Preserved full visibility of cumulative broker calendar day stats in Card 5's subtitle: `Day: $XX.XX (17)`.
2. **Broker Server Midnight Date Alignment & Optimistic UI**:
   - Calibrated history date cutoffs using the broker server's timezone offset:
     $$\\text{server\\_midnight} = (\\text{datetime.utcnow}() + \\Delta t_{\\text{server}}).\\text{replace}(\\text{hour}=0, \\text{minute}=0, \\text{second}=0)$$
   - Ensured that "Today" correctly queries all deals from broker midnight to current time.
   - Added instant optimistic styling updates to history period buttons upon click.
   - Guarded DOM element access in `index.html` to prevent silent JS exceptions.
3. **Section 3 Layout Rebalancing**:
   - Inverted the column allocations: Positions & Trades ledger expanded to primary 2/3 width (`lg:col-span-2`) with scrollable `max-h-[285px]` table containers.
   - Session Trajectory Chart compacted to 1/3 width (`lg:col-span-1`) with a sleek height of `160px–175px`.

---

## 10. Current System Architecture & Roadmap

```
Vantage Algo Status: v2.6 (Session-Calibrated, MT5 Ground-Truth Synced)
Self-Test Verification: 69/69 PASS + 4/4 MT5 Sync PASS
```

### The Optimization Levers Ahead:
* **[COMPLETED] Lever 1: Trade Excursion Telemetry (MAE/MFE)** — Real-time and historical trade excursion tracking.
* **[COMPLETED] Ground Truth Sync: 1:1 MT5 Desktop Alignment** — Reconstructed positions, ticket IDs, period filter.
* **[COMPLETED] Session Isolation & Timezone Calibration** — Distinct session targets, broker midnight alignment, responsive layout.
* **[NEXT] Lever 2: Dynamic ATR Volatility & Spread Expansion Gates** — Automatically widen grid spacing or pause entries when broker spread spikes during economic releases.
* **[UPCOMING] Lever 3: Higher-Timeframe Macro Alignment** — Enforce trend alignment with M15/H1 Moving Averages to ensure the bot rides major momentum waves rather than fighting them.
'''

if target_dev in dev_content:
    dev_content = dev_content.replace(target_dev, chapter_8)
    # Remove old Section 9 footer if present
    # Replace anything from "## 10. Current System Architecture & Roadmap" to the end with our new text
    idx = dev_content.find("## 10. Current System Architecture & Roadmap")
    dev_content = dev_content[:idx] + chapter_8[chapter_8.find("## 10. Current System Architecture & Roadmap"):]
    with open('DEV_JOURNAL.md', 'w', encoding='utf-8') as f:
        f.write(dev_content)
    print("DEV_JOURNAL.md successfully updated!")
else:
    print("target_dev not found in DEV_JOURNAL.md")

# Update AGENT_CONTEXT.md
with open('AGENT_CONTEXT.md', 'r', encoding='utf-8') as f:
    agent_content = f.read()

case_20 = '''
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
'''

target_agent = '## 3. Comprehensive Feature Catalog'
if target_agent in agent_content:
    agent_content = agent_content.replace(target_agent, case_20 + '\n---\n\n## 3. Comprehensive Feature Catalog')
    with open('AGENT_CONTEXT.md', 'w', encoding='utf-8') as f:
        f.write(agent_content)
    print("AGENT_CONTEXT.md successfully updated!")
else:
    print("target_agent not found in AGENT_CONTEXT.md")

