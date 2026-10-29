import json
import re

path = r"C:\Users\dayam\.gemini\antigravity\brain\20df2690-628c-48ce-a2e4-ce780340443a\.system_generated\logs\transcript_full.jsonl"

with open(path, "r", encoding="utf-8") as f:
    u_count = 0
    for line in f:
        if not line.strip():
            continue
        obj = json.loads(line)
        if obj.get("source") == "USER_EXPLICIT" or obj.get("type") == "USER_INPUT":
            u_count += 1
            content = obj.get("content", "")
            t = obj.get("created_at", "")
            # check if <USER_REQUEST> is present
            req_match = re.search(r"<USER_REQUEST>(.*?)</USER_REQUEST>", content, re.DOTALL)
            if req_match:
                req_text = req_match.group(1).strip()
            else:
                req_text = content[:150].strip()
            print(f"[{u_count}] {t} | {req_text[:90]}...")

