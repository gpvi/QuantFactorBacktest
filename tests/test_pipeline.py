import unittest

from quant_factor_backtest.backtest import BacktestEngine
from quant_factor_backtest.domain import MarketData
from quant_factor_backtest.factors import MomentumFactor, StaticDataFactor
from quant_factor_backtest.portfolio import TopNPercentLongOnlyConstructor
from quant_factor_backtest.research.pipeline import CompositeFactorModel, ResearchPipeline
from quant_factor_backtest.universe import UniverseFilter, UniverseFilterConfig


class CompositeFactorModelTest(unittest.TestCase):
    def test_composite_factor_uses_weighted_zscore_normalization(self) -> None:
        signal = CompositeFactorModel({"momentum": 0.6, "value": 0.4}).combine(
            [
                StaticDataFactor(
                    name="momentum",
                    values={"2024-01-02": {"A": 3.0, "B": 1.0, "C": 2.0}},
                ).compute(MarketData(prices={})),
                StaticDataFactor(
                    name="value",
                    values={"2024-01-02": {"A": 1.0, "B": 3.0, "C": 2.0}},
                ).compute(MarketData(prices={})),
            ]
        )

        self.assertAlmostEqual(signal.values["2024-01-02"]["A"], 0.2449489742, places=8)
        self.assertAlmostEqual(signal.values["2024-01-02"]["B"], -0.2449489742, places=8)
        self.assertAlmostEqual(signal.values["2024-01-02"]["C"], 0.0, places=8)


class ResearchPipelineTest(unittest.TestCase):
    def test_pipeline_runs_end_to_end_with_monthly_rebalance_and_metrics(self) -> None:
        market_data = MarketData(
            prices={
                "2024-01-02": {"A": 100.0, "B": 100.0, "C": 100.0, "D": 100.0, "E": 100.0},
                "2024-01-03": {"A": 102.0, "B": 99.0, "C": 101.0, "D": 100.0, "E": 98.0},
                "2024-01-31": {"A": 103.0, "B": 98.0, "C": 102.0, "D": 99.0, "E": 97.0},
                "2024-02-01": {"A": 101.0, "B": 104.0, "C": 100.0, "D": 98.0, "E": 97.0},
                "2024-02-02": {"A": 100.0, "B": 106.0, "C": 99.0, "D": 97.0, "E": 96.0},
            }
        )
        pipeline = ResearchPipeline(
            factors=[
                StaticDataFactor(
                    name="f1",
                    values={
                        "2024-01-02": {"A": 5.0, "B": 1.0, "C": 2.0, "D": 3.0, "E": 4.0},
                        "2024-01-31": {"A": 5.0, "B": 1.0, "C": 2.0, "D": 3.0, "E": 4.0},
                        "2024-02-01": {"A": 1.0, "B": 5.0, "C": 2.0, "D": 3.0, "E": 4.0},
                    },
                ),
                StaticDataFactor(
                    name="f2",
                    values={
                        "2024-01-02": {"A": 5.0, "B": 1.0, "C": 2.0, "D": 3.0, "E": 4.0},
                        "2024-01-31": {"A": 5.0, "B": 1.0, "C": 2.0, "D": 3.0, "E": 4.0},
                        "2024-02-01": {"A": 1.0, "B": 5.0, "C": 2.0, "D": 3.0, "E": 4.0},
                    },
                ),
                StaticDataFactor(
                    name="f3",
                    values={
                        "2024-01-02": {"A": 5.0, "B": 1.0, "C": 2.0, "D": 3.0, "E": 4.0},
                        "2024-01-31": {"A": 5.0, "B": 1.0, "C": 2.0, "D": 3.0, "E": 4.0},
                        "2024-02-01": {"A": 1.0, "B": 5.0, "C": 2.0, "D": 3.0, "E": 4.0},
                    },
                ),
            ],
            factor_weights={"f1": 1.0, "f2": 2.0, "f3": 3.0},
            portfolio_constructor=TopNPercentLongOnlyConstructor(
                top_percent=0.2,
                rebalance_frequency="monthly",
            ),
            backtest_engine=BacktestEngine(initial_capital=1.0),
        )

        composite, weights, result = pipeline.run(market_data)

        self.assertEqual(weights.weights["2024-01-02"], {"A": 1.0})
        self.assertEqual(weights.weights["2024-02-01"], {"B": 1.0})
        self.assertGreater(composite.values["2024-01-02"]["A"], composite.values["2024-01-02"]["B"])
        self.assertAlmostEqual(result.period_returns["2024-01-03"], 0.02)
        self.assertAlmostEqual(result.period_returns["2024-01-31"], 0.009803921568627416)
        self.assertAlmostEqual(result.period_returns["2024-02-01"], -0.01941747572815533)
        self.assertAlmostEqual(result.period_returns["2024-02-02"], 0.019230769230769162)
        self.assertAlmostEqual(result.turnover["2024-01-02"], 1.0)
        self.assertAlmostEqual(result.turnover["2024-02-01"], 1.0)
        self.assertAlmostEqual(result.metrics["win_rate"], 0.75)
        self.assertAlmostEqual(result.metrics["max_drawdown"], -0.01941747572815533)
        self.assertIn("annualized_return", result.metrics)
        self.assertIn("annualized_volatility", result.metrics)
        self.assertIn("sharpe_ratio", result.metrics)
        self.assertIn("turnover_rate", result.metrics)

    def test_pipeline_applies_universe_filter_before_construction(self) -> None:
        market_data = MarketData(
            prices={
                "2024-01-02": {"A": 10.0, "B": 3.0, "C": 8.0, "D": 9.0, "E": 7.0},
                "2024-01-03": {"A": 10.5, "B": 3.1, "C": 8.2, "D": 9.1, "E": 7.2},
            }
        )
        pipeline = ResearchPipeline(
            factors=[
                StaticDataFactor(
                    name="f1",
                    values={"2024-01-02": {"A": 1.0, "B": 9.0, "C": 2.0, "D": 3.0, "E": 4.0}},
                ),
                StaticDataFactor(
                    name="f2",
                    values={"2024-01-02": {"A": 1.0, "B": 9.0, "C": 2.0, "D": 3.0, "E": 4.0}},
                ),
                StaticDataFactor(
                    name="f3",
                    values={"2024-01-02": {"A": 1.0, "B": 9.0, "C": 2.0, "D": 3.0, "E": 4.0}},
                ),
            ],
            factor_weights={"f1": 1.0, "f2": 1.0, "f3": 1.0},
            portfolio_constructor=TopNPercentLongOnlyConstructor(top_percent=0.2),
            backtest_engine=BacktestEngine(initial_capital=1.0),
            universe_filter=UniverseFilter(
                config=UniverseFilterConfig(min_price=5.0)
            ),
        )

        composite, weights, _ = pipeline.run(market_data)

        self.assertNotIn("B", composite.values["2024-01-02"])
        self.assertEqual(weights.weights["2024-01-02"], {"E": 1.0})


if __name__ == "__main__":
    unittest.main()
