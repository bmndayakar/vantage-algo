with open("templates/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'function updateTcsRadar', text)]
for idx in matches:
    print(text[idx:idx+400])
    print("="*40)

