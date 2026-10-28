import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web_app import manager

s = manager.snapshot()
b = s.get("bot", {})
print("Bot status:", b.get("status"))
print("Daily (Session):", b.get("daily"))
print("Deals (Session):", b.get("deals"))
print("Broker Daily:", b.get("broker_daily"))
print("Broker Deals:", b.get("broker_deals"))
print("History Period:", s.get("history_period"))
print("Positions count:", len(s.get("positions", [])))
print("Closed positions count:", len(s.get("closed_positions", [])))
