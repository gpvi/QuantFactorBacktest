import unittest

from quant_factor_backtest.backtest import BacktestEngine
from quant_factor_backtest.domain import MarketData, PortfolioWeights


class BacktestEngineCostTest(unittest.TestCase):
    def test_backtest_deducts_transaction_cost_and_slippage(self) -> None:
        market_data = MarketData(
            prices={
                "2024-01-02": {"A": 100.0},
                "2024-01-03": {"A": 110.0},
            }
        )
        weights = PortfolioWeights(weights={"2024-01-02": {"A": 1.0}})
        engine = BacktestEngine(
            initial_capital=1.0,
            transaction_cost_rate=0.01,
            slippage_rate=0.02,
        )

        result = engine.run(market_data, weights)

        self.assertAlmostEqual(result.turnover["2024-01-02"], 1.0)
        self.assertAlmostEqual(result.period_returns["2024-01-03"], 0.07)
        self.assertAlmostEqual(result.cumulative_return, 0.07)


if __name__ == "__main__":
    unittest.main()
