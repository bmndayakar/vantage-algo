import json

path = r"C:\Users\dayam\.gemini\antigravity\brain\20df2690-628c-48ce-a2e4-ce780340443a\.system_generated\logs\transcript_full.jsonl"
with open(path, "r", encoding="utf-8") as f:
    for i in range(10):
        line = f.readline()
        if not line:
            break
        obj = json.loads(line)
        print(f"Line {i}: source={obj.get('source')}, type={obj.get('type')}, role={obj.get('role')}")
        content = obj.get("content", "")
        if content:
            print("  content preview:", repr(str(content)[:120]))

