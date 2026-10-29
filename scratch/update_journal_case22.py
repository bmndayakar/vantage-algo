# Update DEV_JOURNAL.md
with open("DEV_JOURNAL.md", "r", encoding="utf-8") as f:
    dev = f.read()

target_sec11 = "## 11. Current System Architecture & Roadmap"

chapter_10 = """## 11. Chapter 10: Lever 2 — Dynamic ATR Volatility, Spread Expansion Gates & Midnight Rollover Blackout

### The Incident: The -$207 Flash Stop-Out
During live testing at 02:29 AM IST (04:29 broker time), the bot entered a `BUY 0.10 lots` on Gold and was stopped out **240 milliseconds later** with an instantaneous loss of **-$207.40**.
Forensic analysis revealed:
1. **The Broker Midnight Rollover Spread Blowout**: At 02:29 AM IST (21:00 UTC / 23:00 broker time), the global gold market enters its daily rollover settlement window. Interbank liquidity evaporates, and brokers widen spreads massively. Gold spread spiked to **$21.13 per ounce** (Ask: 4077.58 vs Bid: 4056.45).
2. **The Inactive Guard (`max_spread = 0.0`)**: The spread guard was previously disabled (`0.0`), allowing the bot to buy at the Ask (`4077.38`). The position was immediately valued at the Bid (`4056.64`), creating an instantaneous mark-to-market loss of $(4056.64 - 4077.38) \\times 10 = -\\$207.40$.
3. **Emergency SL Execution**: Because `grid_sl = $20.00` scaled proportionally to `eff_grid_sl = $200.00` on 0.10 lots, the loss of `-$207.40` tripped the emergency stop on the very next tick.

### The Solutions: Lever 2 Implemented
1. **Midnight Rollover Blackout Window (`rollover_blackout: True`)**:
   - Built `is_in_rollover_window(tc, server_offset, start_ist="02:15", end_ist="03:30")`.
   - Automatically pauses all new initial entries during the high-spread rollover window (02:15 to 03:30 AM IST).
   - Displays `🌙 ROLLOVER BLACKOUT (02:15-03:30 IST)` on the radar and telemetry banner.
2. **Spread Expansion Gates**:
   - **Absolute Ceiling (`max_spread: 0.50`)**: Enforced 50-cent maximum spread on Gold. Any spread exceeding $0.50 halts entries with `SPREAD WIDE $X.XX > $0.50`.
   - **Relative Spread Spike Gate (`spread_spike_mult: 2.0`)**: Continuous 30-tick rolling baseline tracker (`spread_history`). If live spread surges beyond 2.0x normal baseline during sudden news events, entries are blocked with `SPREAD SPIKE $X.XX > $0.XX`.
3. **Dynamic ATR Volatility Grid Adaptation**:
   - Fixed dollar steps risk bunching grid legs together in violent momentum candles.
   - When volatility surges, the required adverse move for the next grid leg dynamically widens:
     $$\\text{eff\\_step} = \\max(\\text{eff\\_grid\\_step\\_loss}, \\text{ATR}(14) \\times \\text{atr\\_grid\\_mult} \\times \\text{perUnit})$$
   - Prevents premature leg addition during rapid trending moves.
4. **Volatility Climax Ceiling (`max_atr: 0.0`)**:
   - Blocks new entries if ATR(14) exceeds an extreme ceiling during economic releases.
5. **UI & Dashboard Integration**:
   - Added full settings controls for Lever 2 in the Settings Modal.
   - Live spread in Card 1 flashes rose-red with `⚠️ Wide` whenever spread exceeds the threshold.

---

## 12. Current System Architecture & Roadmap

```
Vantage Algo Status: v2.8 (Lever 2 Active: Dynamic ATR & Spread Shields)
Self-Test Verification: 76/76 PASS + 4/4 MT5 Sync PASS + 5/5 CSV Sync PASS
```

### The Optimization Levers Ahead:
* **[COMPLETED] Lever 1: Trade Excursion Telemetry (MAE/MFE)** — Real-time and historical trade excursion tracking.
* **[COMPLETED] Ground Truth Sync: 1:1 MT5 Desktop Alignment** — Reconstructed positions, ticket IDs, period filter.
* **[COMPLETED] Session Isolation & Timezone Calibration** — Distinct session targets, broker midnight alignment, responsive layout.
* **[COMPLETED] Offline Trade Persistence & Analytics** — 29-column CSV ledger, automatic sync, session/hour/duration analyzer (`analyze_trades.py`).
* **[COMPLETED] Lever 2: Dynamic ATR Volatility & Spread Expansion Gates** — Rollover blackout window (02:15-03:30 IST), max spread ceiling ($0.50), relative spread spike gate (2.0x), and dynamic ATR grid widening.
* **[NEXT] Lever 3: Higher-Timeframe Macro Alignment** — Enforce trend alignment with M15/H1 Moving Averages to ensure the bot rides major momentum waves rather than fighting them.
"""

if target_sec11 in dev:
    idx = dev.find(target_sec11)
    dev = dev[:idx] + chapter_10
    with open("DEV_JOURNAL.md", "w", encoding="utf-8") as f:
        f.write(dev)
    print("DEV_JOURNAL.md updated with Chapter 10!")
else:
    print("target_sec11 not found in DEV_JOURNAL.md")

# Update AGENT_CONTEXT.md
with open("AGENT_CONTEXT.md", "r", encoding="utf-8") as f:
    agent = f.read()

case_22 = """
### Case 22: Lever 2 — Dynamic ATR Volatility, Spread Expansion Gates & Rollover Blackout Shield
* **The Incident & Context**: User asked: *"why did i just lost $207? Implement lever 2 along with rollover blackout window. test it thoroughly"*
* **Forensic Diagnosis**:
  - At 02:29 AM IST (04:29 broker time), MT5 broker entered midnight rollover.
  - XAUUSD spread spiked from normal $0.30 to **$21.13 per ounce**.
  - `max_spread` was previously set to `0.0` (off). Bot entered `BUY 0.10 lots` at Ask `4077.38` and was instantly marked at Bid `4056.64` (-$207.40).
  - Tripped proportional `eff_grid_sl = $200.00` within 240 milliseconds.
* **The Resolution (Lever 2 Full Implementation)**:
  1. **Rollover Blackout Window (`rollover_blackout: True`)**:
     - Automatically pauses all initial entries between 02:15 AM and 03:30 AM IST (broker settlement window).
     - Status updates to `🌙 ROLLOVER BLACKOUT (02:15-03:30 IST)`.
  2. **Spread Expansion Gates**:
     - Absolute ceiling: `max_spread = 0.50` on Gold.
     - Relative spike multiplier: `spread_spike_mult = 2.0` vs rolling 30-tick baseline.
  3. **Dynamic ATR Volatility Grid Adaptation**:
     - Dynamic step widening: `step = max(eff_grid_step_loss, atr * atr_grid_mult * perUnit)`.
     - Prevents adding grid legs prematurely during volatile momentum runs.
  4. **Volatility Climax Gate**: `max_atr` ceiling blocks entry during economic hurricanes.
  5. **Verification**: 7 new unit tests in `up_down_tracker_win_bot_xauusd.py` bringing the self-test suite to **76 passing checks**.
"""

target_case = "## 3. Comprehensive Feature Catalog"
if target_case in agent:
    agent = agent.replace(target_case, case_22 + "\n---\n\n## 3. Comprehensive Feature Catalog")
    with open("AGENT_CONTEXT.md", "w", encoding="utf-8") as f:
        f.write(agent)
    print("AGENT_CONTEXT.md updated with Case 22!")
else:
    print("target_case not found in AGENT_CONTEXT.md")

