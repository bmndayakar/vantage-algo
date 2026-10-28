import sys
import os
import unittest
from collections import namedtuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web_app import reconstruct_closed_positions, format_mt5_time, format_duration

TradeDeal = namedtuple('TradeDeal', [
    'ticket', 'order', 'position_id', 'symbol', 'type', 'entry',
    'volume', 'price', 'profit', 'swap', 'commission', 'magic', 'time'
])

class TestMT5PositionSync(unittest.TestCase):
    def test_single_roundtrip_buy(self):
        # Buy 0.01 @ 2700, Sell 0.01 @ 2705
        d_in = TradeDeal(1, 10, 501, 'XAUUSD', 0, 0, 0.01, 2700.0, 0.0, 0.0, -0.05, 123790, 1000)
        d_out = TradeDeal(2, 20, 501, 'XAUUSD', 1, 1, 0.01, 2705.0, 5.0, -0.02, -0.05, 123790, 1120)
        
        res = reconstruct_closed_positions([d_in, d_out], server_offset=2)
        self.assertEqual(len(res), 1)
        p = res[0]
        self.assertEqual(p['ticket'], 501)
        self.assertEqual(p['symbol'], 'XAUUSD')
        self.assertEqual(p['type'], 'BUY')
        self.assertEqual(p['volume'], 0.01)
        self.assertEqual(p['price_open'], 2700.0)
        self.assertEqual(p['price_close'], 2705.0)
        self.assertEqual(p['profit'], 4.88)  # 5.0 - 0.02 - 0.10
        self.assertEqual(p['duration'], '2m 0s')
        self.assertEqual(p['origin'], 'B')
        self.assertTrue(p['is_bot'])

    def test_multi_scalein_grid_recovery(self):
        # Leg 1: 0.05 @ 2700, Leg 2: 0.05 @ 2690 -> Weighted Avg: 2695.0
        # Exit: 0.10 @ 2702 -> Profit = 70.0, comm = -0.80, swap = -0.50 -> Net = 68.70
        d1 = TradeDeal(10, 100, 777, 'XAUUSD', 0, 0, 0.05, 2700.0, 0.0, 0.0, -0.20, 789998, 500)
        d2 = TradeDeal(11, 101, 777, 'XAUUSD', 0, 0, 0.05, 2690.0, 0.0, 0.0, -0.20, 789998, 550)
        d3 = TradeDeal(12, 102, 777, 'XAUUSD', 1, 1, 0.10, 2702.0, 70.0, -0.50, -0.40, 789998, 700)

        res = reconstruct_closed_positions([d1, d2, d3])
        self.assertEqual(len(res), 1)
        p = res[0]
        self.assertEqual(p['ticket'], 777)
        self.assertEqual(p['price_open'], 2695.0)
        self.assertEqual(p['price_close'], 2702.0)
        self.assertEqual(p['volume'], 0.10)
        self.assertEqual(p['profit'], 68.70)
        self.assertEqual(p['origin'], 'REC')

    def test_missing_entry_deal_fallback(self):
        # Entry deal happened last week, not in query window
        # Exit deal is in query window
        d_out = TradeDeal(55, 550, 999, 'XAUUSD', 0, 1, 0.02, 2680.0, 20.0, 0.0, -0.10, 0, 9000)
        
        # Mock database that knows all deals for position 999
        historical_db = {
            999: [
                TradeDeal(22, 220, 999, 'XAUUSD', 1, 0, 0.02, 2690.0, 0.0, 0.0, -0.10, 0, 1000),
                TradeDeal(55, 550, 999, 'XAUUSD', 0, 1, 0.02, 2680.0, 20.0, 0.0, -0.10, 0, 9000),
            ]
        }
        
        def mock_fetch(pos_id):
            return historical_db.get(pos_id, [])

        res = reconstruct_closed_positions([d_out], fetch_pos_deals_fn=mock_fetch)
        self.assertEqual(len(res), 1)
        p = res[0]
        self.assertEqual(p['ticket'], 999)
        self.assertEqual(p['type'], 'SELL')
        self.assertEqual(p['price_open'], 2690.0)
        self.assertEqual(p['price_close'], 2680.0)
        self.assertEqual(p['origin'], 'U')
        self.assertFalse(p['is_bot'])
        self.assertEqual(p['profit'], 19.80)

    def test_excursion_telemetry_integration(self):
        d_in = TradeDeal(1, 10, 888, 'XAUUSD', 0, 0, 0.01, 2700.0, 0.0, 0.0, 0.0, 123790, 1000)
        d_out = TradeDeal(2, 20, 888, 'XAUUSD', 1, 1, 0.01, 2705.0, 5.0, 0.0, 0.0, 123790, 1100)
        
        excursions = {
            "888": {"mfe": 8.50, "mae": -1.25}
        }
        res = reconstruct_closed_positions([d_in, d_out], trade_excursions=excursions)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['mfe'], 8.50)
        self.assertEqual(res[0]['mae'], -1.25)

if __name__ == '__main__':
    unittest.main()
