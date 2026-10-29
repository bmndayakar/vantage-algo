import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta

TRANSCRIPT_PATH = r"C:\Users\dayam\.gemini\antigravity\brain\20df2690-628c-48ce-a2e4-ce780340443a\.system_generated\logs\transcript_full.jsonl"
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CHAT_LOG.txt")

def format_time(iso_str):
    if not iso_str:
        return "Unknown Time"
    try:
        dt_utc = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        dt_ist = dt_utc + timedelta(hours=5, minutes=30)
        return f"{dt_ist.strftime('%Y-%m-%d %H:%M:%S')} IST ({dt_utc.strftime('%H:%M:%S')} UTC)"
    except Exception:
        return iso_str

def clean_user_text(raw_text):
    if not raw_text:
        return ""
    # Extract clean text from inside <USER_REQUEST> tags if present
    match = re.search(r"<USER_REQUEST>(.*?)</USER_REQUEST>", raw_text, re.DOTALL)
    if match:
        req = match.group(1).strip()
    else:
        req = raw_text.strip()
    return req

def export_transcript(verbose=True):
    if not os.path.exists(TRANSCRIPT_PATH):
        if verbose:
            print(f"Transcript path not found: {TRANSCRIPT_PATH}")
        return 0

    conversation = []
    current_user = None

    with open(TRANSCRIPT_PATH, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue

            source = obj.get("source", "")
            mtype = obj.get("type", "")
            content = obj.get("content", "")
            t = obj.get("created_at", "")

            if source == "USER_EXPLICIT" or mtype == "USER_INPUT":
                user_msg = clean_user_text(content)
                if user_msg:
                    current_user = {
                        "time": format_time(t),
                        "text": user_msg,
                    }
            elif source == "MODEL" and mtype == "PLANNER_RESPONSE" and content:
                if current_user:
                    conversation.append({
                        "user": current_user,
                        "assistant": {
                            "time": format_time(t),
                            "text": content.strip()
                        }
                    })
                    current_user = None

    # Write formatted TXT
    lines = []
    lines.append("=" * 90)
    lines.append("                        VANTAGE ALGO -- FULL CHAT CONVERSATION LOG")
    lines.append("=" * 90)
    lines.append(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Local IST")
    lines.append(f"Total Turns : {len(conversation)}")
    lines.append("=" * 90)
    lines.append("\n")

    for idx, turn in enumerate(conversation, 1):
        u = turn["user"]
        a = turn["assistant"]

        lines.append("-" * 90)
        lines.append(f"[TURN {idx:02d}] USER -- {u['time']}")
        lines.append("-" * 90)
        lines.append(u["text"])
        lines.append("\n")

        lines.append("." * 90)
        lines.append(f"[TURN {idx:02d}] ASSISTANT (ANTIGRAVITY) -- {a['time']}")
        lines.append("." * 90)
        lines.append(a["text"])
        lines.append("\n\n")

    output_path = os.path.abspath(OUTPUT_FILE)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    if verbose:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Exported {len(conversation)} turns to {output_path} ({os.path.getsize(output_path):,} bytes)")
    return len(conversation)

def watch_mode():
    print(f"Starting continuous chat sync watcher for: {OUTPUT_FILE}")
    last_mtime = 0
    while True:
        try:
            if os.path.exists(TRANSCRIPT_PATH):
                mtime = os.path.getmtime(TRANSCRIPT_PATH)
                if mtime != last_mtime:
                    last_mtime = mtime
                    export_transcript(verbose=True)
            time.sleep(3.0)
        except KeyboardInterrupt:
            print("\nChat watcher stopped.")
            break
        except Exception as e:
            time.sleep(3.0)

if __name__ == "__main__":
    if "--watch" in sys.argv:
        watch_mode()
    else:
        export_transcript(verbose=True)
