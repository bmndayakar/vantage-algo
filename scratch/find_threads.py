with open("web_app.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'def start\(|def run\(|threading\.Thread', text)]
for idx in matches[:10]:
    print(text[idx-20:idx+250])
    print("="*40)

