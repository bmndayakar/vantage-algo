file_path = "web_app.py"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if 'key=lambda r: int(r.get("_close_ts", 0)) if "_close_ts" in r else r.get("close_time_server", "")' in line:
        new_lines.append('            key=lambda r: str(r.get("close_time_server", "")),\n')
        print("Replaced line successfully")
    else:
        new_lines.append(line)

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

