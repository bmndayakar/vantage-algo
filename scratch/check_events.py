import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web_app import manager

print("Events count:", len(manager.events))
for e in manager.events[-10:]:
    print("EVENT:", e)

