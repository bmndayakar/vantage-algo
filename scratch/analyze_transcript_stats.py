import json
import re

path = r"C:\Users\dayam\\.gemini\antigravity\brain\20df2690-628c-48ce-a2e4-ce780340443a\\.system_generated\logs\transcript_full.jsonl"
path = path.replace("\\\\", "\\")

user_msgs = 0
model_msgs = 0
tool_msgs = 0

with open(path, "r", encoding="utf-8") as f:
    for line_num, line in enumerate(f):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except Exception as e:
            continue
        source = obj.get("source", "")
        mtype = obj.get("type", "")
        content = obj.get("content", "")
        
        if source == "USER_EXPLICIT" or mtype == "USER_INPUT":
            user_msgs += 1
        elif source == "MODEL" and mtype == "PLANNER_RESPONSE" and content:
            model_msgs += 1
        else:
            tool_msgs += 1

print(f"Total lines: {line_num+1}")
print(f"User messages: {user_msgs}")
print(f"Model response messages: {model_msgs}")
print(f"Tool / internal steps: {tool_msgs}")

