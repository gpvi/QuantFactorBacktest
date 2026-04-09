import unittest

from quant_factor_backtest.domain import FactorSignal
from quant_factor_backtest.portfolio import TopNPercentLongOnlyConstructor


class PortfolioConstructorTest(unittest.TestCase):
    def test_top_percent_constructor_selects_highest_scored_assets(self) -> None:
        signal = FactorSignal(
            name="composite",
            values={"2024-01-02": {"A": 0.2, "B": 0.9, "C": 0.5, "D": 0.1, "E": 0.4}},
        )

        weights = TopNPercentLongOnlyConstructor(top_percent=0.2).build(signal)

        self.assertEqual(weights.weights["2024-01-02"], {"B": 1.0})

    def test_monthly_rebalance_only_generates_weights_on_first_trading_day_of_month(self) -> None:
        signal = FactorSignal(
            name="composite",
            values={
                "2024-01-02": {"A": 0.9, "B": 0.1, "C": 0.2, "D": 0.3, "E": 0.4},
                "2024-01-15": {"A": 0.1, "B": 0.9, "C": 0.2, "D": 0.3, "E": 0.4},
                "2024-02-01": {"A": 0.1, "B": 0.9, "C": 0.2, "D": 0.3, "E": 0.4},
            },
        )

        weights = TopNPercentLongOnlyConstructor(
            top_percent=0.2,
            rebalance_frequency="monthly",
        ).build(signal)

        self.assertEqual(sorted(weights.weights.keys()), ["2024-01-02", "2024-02-01"])
        self.assertEqual(weights.weights["2024-01-02"], {"A": 1.0})
        self.assertEqual(weights.weights["2024-02-01"], {"B": 1.0})


if __name__ == "__main__":
    unittest.main()
