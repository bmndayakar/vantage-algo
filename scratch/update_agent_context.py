import os

with open('AGENT_CONTEXT.md', 'r', encoding='utf-8') as f:
    text = f.read()

target = '### Case 18'
pos = text.find(target)
if pos != -1:
    end_of_c18 = text.find('\n---\n\n## 3. Comprehensive Feature Catalog', pos)
    if end_of_c18 != -1:
        case_19 = """

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
  5. Verified with 4 unit tests in `scratch/test_mt5_sync.py` and all 69 core bot self-tests passing."""

        updated = text[:end_of_c18] + case_19 + text[end_of_c18:]
        with open('AGENT_CONTEXT.md', 'w', encoding='utf-8') as fw:
            fw.write(updated)
        print("AGENT_CONTEXT.md updated successfully")
    else:
        print("End of Case 18 not found")
else:
    print("Case 18 not found")

