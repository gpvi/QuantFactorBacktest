from quant_factor_backtest.backtest import BacktestEngine
from quant_factor_backtest.domain import MarketData
from quant_factor_backtest.factors import StaticDataFactor
from quant_factor_backtest.portfolio import TopNPercentLongOnlyConstructor
from quant_factor_backtest.research import ResearchPipeline


def main() -> None:
    market_data = MarketData(
        prices={
            "2024-01-01": {"A": 100.0, "B": 100.0, "C": 100.0},
            "2024-01-02": {"A": 108.0, "B": 98.0, "C": 101.0},
            "2024-01-31": {"A": 112.0, "B": 97.0, "C": 103.0},
            "2024-02-01": {"A": 109.0, "B": 103.0, "C": 104.0},
            "2024-02-02": {"A": 108.0, "B": 106.0, "C": 105.0},
        }
    )

    pipeline = ResearchPipeline(
        factors=[
            StaticDataFactor(
                name="f1",
                values={
                    "2024-01-01": {"A": 5.0, "B": 1.0, "C": 3.0},
                    "2024-02-01": {"A": 1.0, "B": 5.0, "C": 3.0},
                },
            ),
            StaticDataFactor(
                name="f2",
                values={
                    "2024-01-01": {"A": 4.0, "B": 2.0, "C": 3.0},
                    "2024-02-01": {"A": 2.0, "B": 4.0, "C": 3.0},
                },
            ),
            StaticDataFactor(
                name="f3",
                values={
                    "2024-01-01": {"A": 3.0, "B": 1.0, "C": 2.0},
                    "2024-02-01": {"A": 1.0, "B": 3.0, "C": 2.0},
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
    print("Composite:", composite.values)
    print("Weights:", weights.weights)
    print("Returns:", result.period_returns)
    print("Equity:", result.equity_curve)
    print("Cumulative Return:", result.cumulative_return)
    print("Turnover:", result.turnover)
    print("Metrics:", result.metrics)


if __name__ == "__main__":
    main()
