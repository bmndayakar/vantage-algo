import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import web_app
import asyncio

print("Calling export_trades_csv...")
res = asyncio.run(web_app.export_trades_csv())
print("Result:", res)
