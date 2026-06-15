import unittest
from unittest.mock import patch

import pandas as pd

from app.data_fetcher import (
    MarketDataError,
    filter_main_board_stocks,
    fetch_daily_kline,
)


class MarketUniverseTests(unittest.TestCase):
    def test_filters_to_active_shanghai_shenzhen_main_board(self):
        rows = pd.DataFrame(
            [
                {"代码": "000001", "名称": "平安银行", "最新价": 11.2},
                {"代码": "001696", "名称": "宗申动力", "最新价": 20.1},
                {"代码": "002594", "名称": "比亚迪", "最新价": 300.0},
                {"代码": "003816", "名称": "中国广核", "最新价": 4.1},
                {"代码": "600000", "名称": "浦发银行", "最新价": 10.0},
                {"代码": "601318", "名称": "中国平安", "最新价": 50.0},
                {"代码": "603259", "名称": "药明康德", "最新价": 70.0},
                {"代码": "605117", "名称": "德业股份", "最新价": 80.0},
                {"代码": "sh600004", "名称": "白云机场", "最新价": 9.0},
                {"代码": "sz000009", "名称": "中国宝安", "最新价": 10.0},
                {"代码": "300750", "名称": "宁德时代", "最新价": 400.0},
                {"代码": "688981", "名称": "中芯国际", "最新价": 90.0},
                {"代码": "920001", "名称": "北证样本", "最新价": 10.0},
                {"代码": "200002", "名称": "万科B", "最新价": 5.0},
                {"代码": "000002", "名称": "ST万科", "最新价": 5.0},
                {"代码": "600001", "名称": "*ST退市", "最新价": 1.0},
                {"代码": "600002", "名称": "退市整理", "最新价": 1.0},
                {"代码": "600003", "名称": "停牌股票", "最新价": None},
            ]
        )

        result = filter_main_board_stocks(rows)

        self.assertEqual(
            [item["code"] for item in result],
            [
                "000001", "001696", "002594", "003816",
                "600000", "601318", "603259", "605117", "600004", "000009",
            ],
        )

    @patch("app.data_fetcher.ak.stock_zh_a_daily", side_effect=RuntimeError("sina down"))
    @patch("app.data_fetcher.ak.stock_zh_a_hist", side_effect=RuntimeError("eastmoney down"))
    @patch("app.data_fetcher.ak.stock_zh_a_hist_tx", side_effect=RuntimeError("tencent down"))
    def test_history_failure_raises_and_never_generates_synthetic_data(
        self, _tx, _eastmoney, _sina
    ):
        with self.assertRaises(MarketDataError):
            fetch_daily_kline("600000", "20260101", "20260614")
        _tx.assert_called_once()
        _eastmoney.assert_called_once()
        _sina.assert_called_once()


if __name__ == "__main__":
    unittest.main()
