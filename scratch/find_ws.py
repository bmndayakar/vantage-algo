with open("web_app.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'/ws', text)]
for idx in matches:
    print(text[idx-50:idx+250])
    print("="*40)

