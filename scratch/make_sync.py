with open("web_app.py", "r", encoding="utf-8") as f:
    code = f.read()

code = code.replace(
    '@app.get("/api/export_trades_csv")\nasync def export_trades_csv():',
    '@app.get("/api/export_trades_csv")\ndef export_trades_csv():'
)
code = code.replace(
    '@app.get("/api/trade_analytics")\nasync def get_trade_analytics():',
    '@app.get("/api/trade_analytics")\ndef get_trade_analytics():'
)

with open("web_app.py", "w", encoding="utf-8") as f:
    f.write(code)
print("Updated endpoints to def")

