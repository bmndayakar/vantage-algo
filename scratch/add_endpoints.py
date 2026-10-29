with open("web_app.py", "r", encoding="utf-8") as f:
    code = f.read()

target = '    return {"status": "ok", "message": "Session goal & deals reset."}'
replacement = '''    return {"status": "ok", "message": "Session goal & deals reset."}


@app.get("/api/export_trades_csv")
async def export_trades_csv():
    """Download the complete offline closed trades CSV ledger."""
    if not os.path.exists(CLOSED_TRADES_FILE):
        with open(CLOSED_TRADES_FILE, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CLOSED_TRADES_HEADERS)
            writer.writeheader()
    filename = f"closed_trades_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return FileResponse(CLOSED_TRADES_FILE, media_type="text/csv", filename=filename)


@app.get("/api/trade_analytics")
async def get_trade_analytics():
    """Returns parsed quantitative performance metrics across sessions and hours."""
    if not os.path.exists(CLOSED_TRADES_FILE):
        return {"status": "ok", "total_trades": 0, "trades": []}
    try:
        trades = []
        with open(CLOSED_TRADES_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                trades.append(r)
        n_total = len(trades)
        n_wins = sum(1 for t in trades if t.get("outcome") == "WIN")
        tot_pnl = round(sum(float(t.get("net_pnl", 0.0)) for t in trades), 2)
        win_rate = round((n_wins / n_total) * 100.0, 1) if n_total > 0 else 0.0
        return {
            "status": "ok",
            "total_trades": n_total,
            "win_rate": win_rate,
            "net_pnl": tot_pnl,
            "trades": trades[:100],
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}'''

if target in code:
    code = code.replace(target, replacement, 1)
    with open("web_app.py", "w", encoding="utf-8") as f:
        f.write(code)
    print("Added endpoints to web_app.py successfully!")
else:
    print("Target not found in web_app.py")

