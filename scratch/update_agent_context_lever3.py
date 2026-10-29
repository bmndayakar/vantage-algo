import os

file_path = "AGENT_CONTEXT.md"
with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Update selftest checks count
text = text.replace("All **55 unit checks** must pass.", "All **83 unit checks** must pass.")
text = text.replace("76 unit checks", "83 unit checks")

# 2. Add Case 23 in Case Log / Evolution History
case23 = """### Case 23: The Counter-Trend Whipsaw & Lever 3 (Higher-Timeframe Macro Alignment)
* **Date**: October 29, 2026
* **Trigger**: Consecutive -$200 basket stop-outs during Gold's +$32.57 rally and -$25.06 collapse.
* **Root Causes**:
  1. *Lagging Single-Timeframe MA*: 250-period M1 MA forced counter-trend shorts during vertical rallies and counter-trend longs during waterfalls.
  2. *Blind Grid Averaging*: Added Leg 2 into adverse momentum candles without waiting for exhaustion.
  3. *Process Runtime Lifetime*: Server was running 01:30 AM code in memory before Lever 2 had been restarted.
* **Fix (Lever 3)**:
  1. *HTF Trend Filter (`htf_filter: True`, `htf_tf: "M5"`, EMA 9 vs 21)*: Strictly blocks BUY when M5 is Bearish; strictly blocks SELL when M5 is Bullish. Automatically directs pullback engine to buy dips with the macro trend.
  2. *Anti-Averaging Grid Momentum Guard (`grid_bounce_req: 0.40`)*: Holds grid additions during adverse moves until price confirms a $0.40 bounce/rejection.
  3. *Clean Verification*: Expanded self-test suite to 83 checks (ALL PASS).

---
"""

if "### Case 23:" not in text:
    # Insert before ## 4. Instructions for Future AI Agents
    anchor = "## 4. Instructions for Future AI Agents"
    if anchor in text:
        text = text.replace(anchor, case23 + "\n" + anchor)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(text)

print("Updated AGENT_CONTEXT.md successfully")

