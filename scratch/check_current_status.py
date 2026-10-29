import MetaTrader5 as mt5
from datetime import datetime, timezone

if not mt5.initialize():
    print("Failed to initialize MT5")
    exit(1)

symbol = "XAUUSD"
pos = mt5.positions_get(symbol=symbol)
print(f"--- OPEN POSITIONS ({len(pos) if pos else 0}) ---")
if pos:
    for p in pos:
        print(f"Ticket: {p.ticket}, Type: {'BUY' if p.type==0 else 'SELL'}, Lots: {p.volume}, OpenPrice: {p.price_open}, Current: {p.price_current}, SL: {p.sl}, TP: {p.tp}, PnL: {p.profit}")

acc = mt5.account_info()
if acc:
    print(f"Account: Login={acc.login}, Balance={acc.balance}, Equity={acc.equity}, Margin={acc.margin}, FreeMargin={acc.margin_free}")

# Check M1, M5, M15, H1 trend
for tf_name, tf in [("M1", mt5.TIMEFRAME_M1), ("M5", mt5.TIMEFRAME_M5), ("M15", mt5.TIMEFRAME_M15), ("H1", mt5.TIMEFRAME_H1)]:
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, 5)
    if rates is not None and len(rates) > 0:
        latest = rates[-1]
        prev = rates[-2]
        print(f"[{tf_name}] Latest Close: {latest['close']}, Prev Close: {prev['close']}, High: {latest['high']}, Low: {latest['low']}")

mt5.shutdown()

