with open("web_app.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'def sync_closed_trades_to_csv', text)]
for idx in matches:
    print(text[idx:idx+800])
    print("="*40)

