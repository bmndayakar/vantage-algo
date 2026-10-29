file_path = "AGENT_CONTEXT.md"
with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

rule5 = """### Rule 5: Continuous Chat Export (`CHAT_LOG.txt`)
The complete conversation transcript between the user and assistant is persisted to `CHAT_LOG.txt` in the root workspace.
* A background watcher (`python export_chat_history.py --watch`) automatically updates `CHAT_LOG.txt` whenever new messages arrive.
* If making changes or resuming sessions, verify `CHAT_LOG.txt` is updated or run `python export_chat_history.py`.

---
"""

anchor = "### Rule 4: Small Account Safety Defaults"
if anchor in text and "### Rule 5:" not in text:
    # Append after Rule 4 section
    idx = text.find(anchor)
    # Find next section or end of Rule 4
    next_anchor = "\n\n"
    end_of_r4 = text.find("\n\n---", idx)
    if end_of_r4 != -1:
        text = text[:end_of_r4 + 5] + "\n" + rule5 + text[end_of_r4 + 5:]
    else:
        text = text + "\n\n" + rule5

with open(file_path, "w", encoding="utf-8") as f:
    f.write(text)

print("Updated AGENT_CONTEXT.md with Rule 5")

