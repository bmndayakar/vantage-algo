import json

path = r"C:\Users\dayam\.gemini\antigravity\brain\20df2690-628c-48ce-a2e4-ce780340443a\.system_generated\logs\transcript_full.jsonl"

turns = []
current_user = None

with open(path, "r", encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue
        obj = json.loads(line)
        source = obj.get("source", "")
        mtype = obj.get("type", "")
        content = obj.get("content", "")
        t = obj.get("created_at", "")
        
        if source == "USER_EXPLICIT" or mtype == "USER_INPUT":
            current_user = {"time": t, "content": content}
        elif source == "MODEL" and mtype == "PLANNER_RESPONSE" and content:
            if current_user:
                turns.append((current_user, {"time": t, "content": content}))
                current_user = None

print(f"Total conversation turns paired: {len(turns)}")
for i, (u, a) in enumerate(turns[:5]):
    print(f"\n--- TURN {i+1} ---")
    print(f"User ({u['time']}): {repr(u['content'][:80])}")
    print(f"Assistant ({a['time']}): {repr(a['content'][:80])}")

