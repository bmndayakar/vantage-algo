with open("templates/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")
for idx, line in enumerate(lines):
    l = line.strip()
    if any(k in l for k in ["WebSocket", "connectWs", "poll", "setInterval", "setTimeout", "Chart", "renderChart", "pnlChart"]):
        print(f"L{idx+1}: {l[:100]}")

