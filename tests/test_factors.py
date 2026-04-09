import unittest

from quant_factor_backtest.domain import MarketData
from quant_factor_backtest.factors import MomentumFactor


class MomentumFactorTest(unittest.TestCase):
    def test_momentum_factor_computes_simple_return(self) -> None:
        market_data = MarketData(
            prices={
                "2024-01-01": {"A": 100.0, "B": 100.0},
                "2024-01-02": {"A": 110.0, "B": 95.0},
            }
        )

        signal = MomentumFactor(lookback=1).compute(market_data)

        self.assertEqual(signal.name, "momentum")
        self.assertAlmostEqual(signal.values["2024-01-02"]["A"], 0.10)
        self.assertAlmostEqual(signal.values["2024-01-02"]["B"], -0.05)


if __name__ == "__main__":
    unittest.main()
