import MetaTrader5 as mt5
from datetime import datetime, timezone

if not mt5.initialize():
    print("MT5 init failed")
    exit(1)

pos = mt5.positions_get(symbol="XAUUSD")
print(f"Current open positions ({len(pos) if pos else 0}):")
if pos:
    for p in pos:
        print(f"Ticket: {p.ticket}, Type: {'BUY' if p.type==0 else 'SELL'}, Vol: {p.volume}, Open: {p.price_open}, Current: {p.price_current}, PnL: {p.profit}")

acc = mt5.account_info()
if acc:
    print(f"Account Balance: ${acc.balance:.2f}, Equity: ${acc.equity:.2f}")

mt5.shutdown()

