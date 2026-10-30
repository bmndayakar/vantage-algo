import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import unittest
import datetime
from web_app import compute_win_rate_stats

class TestWinRateStats(unittest.TestCase):
    def test_live_csv(self):
        csv_path = "closed_trades.csv"
        self.assertTrue(os.path.exists(csv_path), "closed_trades.csv should exist")
        stats = compute_win_rate_stats(csv_path)
        
        for k in ["today", "yesterday", "this_week", "this_month"]:
            self.assertIn(k, stats)
            b = stats[k]
            self.assertIn("wins", b)
            self.assertIn("losses", b)
            self.assertIn("total", b)
            self.assertIn("win_pct", b)
            self.assertIn("loss_pct", b)
            self.assertIn("pnl", b)
            self.assertEqual(b["wins"] + b["losses"] + b["be"], b["total"])
            if b["total"] > 0:
                self.assertAlmostEqual(b["win_pct"] + b["loss_pct"], (b["wins"] + b["losses"]) / b["total"] * 100.0, places=1)
                
    def test_empty_or_missing_csv(self):
        stats = compute_win_rate_stats("non_existent_file.csv")
        for k in ["today", "yesterday", "this_week", "this_month"]:
            self.assertIn(k, stats)
            self.assertEqual(stats[k]["total"], 0)
            self.assertEqual(stats[k]["win_pct"], 0.0)
            self.assertEqual(stats[k]["loss_pct"], 0.0)

if __name__ == "__main__":
    unittest.main()
