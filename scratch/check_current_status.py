import urllib.request
import json

req = urllib.request.urlopen('http://localhost:8000/api/state')
data = json.loads(req.read().decode('utf-8'))
telem = data.get('telemetry', {})
bot = data.get('bot', {})
market = data.get('market', {})

print("=== CURRENT LIVE TELEMETRY ===")
print("Bot Status:", bot.get('status'))
print("Action Side:", telem.get('action_side'))
print("Target Desc:", telem.get('target_entry_desc', '').encode('ascii', 'ignore').decode())
print("Buy Desc:", telem.get('buy_target_desc', '').encode('ascii', 'ignore').decode())
print("Sell Desc:", telem.get('sell_target_desc', '').encode('ascii', 'ignore').decode())
print(f"MA: {telem.get('current_ma')} | Dist: {telem.get('dist_ma')} | Max Dist: {telem.get('max_ma_dist')}")
print(f"TCS Status: {telem.get('tcs_status')} | Dir: {telem.get('tcs_dir')} | Bull: {telem.get('tcs_bull_score')} | Bear: {telem.get('tcs_bear_score')}")
print(f"ADX: {telem.get('tcs_adx')} (Min: 25.0) | Rising: {telem.get('tcs_adx_rising')} | DI+: {telem.get('tcs_di_plus')} | DI-: {telem.get('tcs_di_minus')}")
print(f"Structure: {telem.get('tcs_structure')} | MACD Hist: {telem.get('tcs_macd_hist')}")
print(f"Pillars: P1_bull={telem.get('tcs_p1_bull')} P1_bear={telem.get('tcs_p1_bear')} | P2_bull={telem.get('tcs_p2_bull')} P2_bear={telem.get('tcs_p2_bear')}")
print(f"         P3_bull={telem.get('tcs_p3_bull')} P3_bear={telem.get('tcs_p3_bear')} | P4_bull={telem.get('tcs_p4_bull')} P4_bear={telem.get('tcs_p4_bear')}")
