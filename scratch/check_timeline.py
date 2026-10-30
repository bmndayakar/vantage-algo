import sys
sys.path.insert(0, ".")
import MetaTrader5 as mt5
from up_down_tracker_win_bot_xauusd import MT5Broker, Cfg
from datetime import datetime

if not mt5.initialize():
    print("mt5 init failed")
    quit()

cfg = Cfg()
broker = MT5Broker(cfg)

rates = mt5.copy_rates_from_pos('XAUUSD', mt5.TIMEFRAME_M1, 0, 150)

# Let's inspect recent 40 bars (last 40 minutes)
for i in range(len(rates) - 40, len(rates)):
    # evaluate TCS on rates up to i
    sub_rates = rates[:i]
    t = datetime.fromtimestamp(sub_rates[-1][0]).strftime('%H:%M')
    # Use broker._tcs_from_rates
    # Let's see what broker has
    pass

mt5.shutdown()

