import unittest

from app.strategies import ALL_STRATEGIES, STRATEGY_CATEGORIES


class StrategyRegistryTests(unittest.TestCase):
    def test_limit_up_gene_strategy_is_not_registered(self):
        names = [strategy.name for strategy in ALL_STRATEGIES]

        self.assertNotIn("涨停基因", names)
        self.assertNotIn("涨停基因", STRATEGY_CATEGORIES["情绪趋势类"])


if __name__ == "__main__":
    unittest.main()
