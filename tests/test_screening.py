import unittest

from app.screener import summarize_results
from app.strategies.base import ScreeningResult


class ScreeningSummaryTests(unittest.TestCase):
    def test_counts_unique_stocks_separately_from_strategy_hits(self):
        results = [
            ScreeningResult("600000", "浦发银行", "反包", 10, 2, 1, "a"),
            ScreeningResult("600000", "浦发银行", "放量突破", 10, 2, 1, "b"),
            ScreeningResult("000001", "平安银行", "反包", 11, 1, 1, "c"),
        ]

        summary = summarize_results(results)

        self.assertEqual(summary["total_stocks"], 2)
        self.assertEqual(summary["total_hits"], 3)
        self.assertEqual(summary["strategy_counts"], {"反包": 2, "放量突破": 1})


if __name__ == "__main__":
    unittest.main()
