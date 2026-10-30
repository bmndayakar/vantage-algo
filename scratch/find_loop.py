with open("web_app.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'def _tick_loop|def tick_loop|while self\.is_running|while True', text)]
for idx in matches[:10]:
    print(text[idx-20:idx+200])
    print("="*40)

