import os
import sys
import unittest
import datetime as dt
import csv

# Ensure repo root in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from web_app import (
    classify_session,
    classify_duration,
    sync_closed_trades_to_csv,
    export_trades_csv,
    get_trade_analytics,
    CLOSED_TRADES_HEADERS,
)
import analyze_trades


class TestClosedTradesOfflineSync(unittest.TestCase):
    def setUp(self):
        self.test_csv = os.path.join(os.path.dirname(__file__), "unit_test_closed_trades.csv")
        if os.path.exists(self.test_csv):
            os.remove(self.test_csv)

    def tearDown(self):
        if os.path.exists(self.test_csv):
            os.remove(self.test_csv)

    def test_session_classification(self):
        # Asian Tokyo: 05:30 to 13:30 IST
        self.assertEqual(classify_session(dt.datetime(2026, 10, 29, 6, 0)), "Asian (Tokyo)")
        self.assertEqual(classify_session(dt.datetime(2026, 10, 29, 13, 0)), "Asian (Tokyo)")

        # London: 13:30 to 18:30 IST
        self.assertEqual(classify_session(dt.datetime(2026, 10, 29, 14, 0)), "London")
        self.assertEqual(classify_session(dt.datetime(2026, 10, 29, 18, 0)), "London")

        # London/NY Overlap: 18:30 to 21:30 IST
        self.assertEqual(classify_session(dt.datetime(2026, 10, 29, 19, 0)), "London/NY Overlap")
        self.assertEqual(classify_session(dt.datetime(2026, 10, 29, 21, 0)), "London/NY Overlap")

        # New York: 21:30 to 02:30 IST
        self.assertEqual(classify_session(dt.datetime(2026, 10, 29, 22, 0)), "New York")
        self.assertEqual(classify_session(dt.datetime(2026, 10, 29, 1, 30)), "New York")

        # Pacific / Late US: 02:30 to 05:30 IST
        self.assertEqual(classify_session(dt.datetime(2026, 10, 29, 3, 0)), "Pacific/Late US")

    def test_duration_classification(self):
        self.assertEqual(classify_duration(35), "< 1 min (Hyper Scalp)")
        self.assertEqual(classify_duration(180), "1 - 5 min (Fast Scalp)")
        self.assertEqual(classify_duration(600), "5 - 15 min (Standard Scalp)")
        self.assertEqual(classify_duration(1800), "15 - 60 min (Intraday Swing)")
        self.assertEqual(classify_duration(7200), "> 1 hr (Extended Swing)")

    def test_sync_and_deduplication(self):
        trades_batch_1 = [
            {
                "ticket": 1001,
                "symbol": "XAUUSD",
                "type": "BUY",
                "volume": 0.1,
                "price_open": 4040.0,
                "price_close": 4042.5,
                "profit": 25.0,
                "gross_profit": 25.7,
                "commission": -0.7,
                "swap": 0.0,
                "duration": "2m 30s",
                "duration_sec": 150,
                "open_time_ts": 1793217000,
                "close_time_ts": 1793217150,
                "magic": 123790,
                "origin": "B",
                "mfe": 30.0,
                "mae": -5.0,
            },
            {
                "ticket": 1002,
                "symbol": "XAUUSD",
                "type": "SELL",
                "volume": 0.05,
                "price_open": 4045.0,
                "price_close": 4047.0,
                "profit": -10.0,
                "gross_profit": -9.65,
                "commission": -0.35,
                "swap": 0.0,
                "duration": "45s",
                "duration_sec": 45,
                "open_time_ts": 1793218000,
                "close_time_ts": 1793218045,
                "magic": 123790,
                "origin": "B",
                "mfe": None,
                "mae": None,
            },
        ]

        # Initial write
        added = sync_closed_trades_to_csv(self.test_csv, trades_batch_1)
        self.assertEqual(added, 2)
        self.assertTrue(os.path.exists(self.test_csv))

        with open(self.test_csv, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["ticket"], "1002")  # Most recent first
        self.assertEqual(rows[1]["ticket"], "1001")
        self.assertEqual(rows[1]["pnl_per_lot"], "+250.00")
        self.assertEqual(rows[1]["outcome"], "WIN")

        # Second write with same trades: must NOT duplicate
        added_again = sync_closed_trades_to_csv(self.test_csv, trades_batch_1)
        self.assertEqual(added_again, 0)
        with open(self.test_csv, "r", encoding="utf-8") as f:
            rows_after = list(csv.DictReader(f))
        self.assertEqual(len(rows_after), 2)

        # Excursion update test: ticket 1002 now gets MFE/MAE
        trades_batch_1[1]["mfe"] = 8.5
        trades_batch_1[1]["mae"] = -15.0
        sync_closed_trades_to_csv(self.test_csv, trades_batch_1)

        with open(self.test_csv, "r", encoding="utf-8") as f:
            rows_updated = {r["ticket"]: r for r in csv.DictReader(f)}
        self.assertEqual(rows_updated["1002"]["mfe"], "+8.50")
        self.assertEqual(rows_updated["1002"]["mae"], "-15.00")
        self.assertEqual(rows_updated["1002"]["mfe_mae_ratio"], "0.57")

    def test_analyze_trades_script(self):
        trades_batch = [
            {
                "ticket": 2001,
                "symbol": "XAUUSD",
                "type": "BUY",
                "volume": 0.1,
                "price_open": 4040.0,
                "price_close": 4042.5,
                "profit": 25.0,
                "gross_profit": 25.7,
                "commission": -0.7,
                "swap": 0.0,
                "duration": "2m 30s",
                "duration_sec": 150,
                "open_time_ts": 1793217000,
                "close_time_ts": 1793217150,
                "magic": 123790,
                "origin": "B",
                "mfe": 30.0,
                "mae": -5.0,
            }
        ]
        sync_closed_trades_to_csv(self.test_csv, trades_batch)

        loaded = analyze_trades.load_trades(self.test_csv)
        self.assertEqual(len(loaded), 1)
        analyze_trades.run_analysis(loaded)

    def test_api_export_and_analytics(self):
        res_export = export_trades_csv()
        self.assertEqual(res_export.media_type, "text/csv")
        self.assertIn("closed_trades_", res_export.filename)

        res_analytics = get_trade_analytics()
        self.assertEqual(res_analytics["status"], "ok")
        self.assertIn("total_trades", res_analytics)
        self.assertIn("win_rate", res_analytics)


if __name__ == "__main__":
    unittest.main()
