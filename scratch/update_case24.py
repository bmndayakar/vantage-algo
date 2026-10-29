file_path = "AGENT_CONTEXT.md"
with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

case24 = """### Case 24: CSV Sync Sort Key Type Mismatch Fix
* **Date**: October 29, 2026
* **Trigger**: UI displayed `'<' not supported between instances of 'str' and 'int'`.
* **Root Cause**: `sync_closed_trades_to_csv()` used a hybrid sort key: `_close_ts` (integer) for newly constructed trades vs `close_time_server` (string) for rows loaded from disk. Sorting mixed types caused a Python `TypeError`.
* **Fix**: Unified sort key to `key=lambda r: str(r.get("close_time_server", ""))`. ISO formatted server timestamps sort chronologically and safely without type conflicts.

---
"""

anchor = "### Case 23:"
if anchor in text and "### Case 24:" not in text:
    text = text.replace(anchor, case24 + "\n" + anchor)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(text)

print("Updated AGENT_CONTEXT.md with Case 24")

