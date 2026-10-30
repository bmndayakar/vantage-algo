with open("templates/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("Lines containing grid or card headers:")
for i, line in enumerate(lines[:500]):
    l = line.strip()
    if "grid-cols" in l or "Session Goal" in l or "Daily Goal" in l or "Account" in l or "Signal Radar" in l:
        print(f"L{i+1}: {l[:120]}")

