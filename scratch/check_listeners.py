with open("templates/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
print("Length of index.html:", len(text))

# Check for event listeners added inside functions (which might accumulate)
listeners = re.findall(r'addEventListener\([^\n]+', text)
print(f"addEventListener count: {len(listeners)}")
for l in listeners:
    print(" ", l[:70])

