from quant_factor_backtest import (
    BacktestEngine,
    DailyBasicFieldFactor,
    ResearchPipeline,
    TushareConfig,
    TushareDataClient,
    UniverseFilter,
    UniverseFilterConfig,
)
from quant_factor_backtest.factors import MomentumFactor
from quant_factor_backtest.portfolio import TopNPercentLongOnlyConstructor


def main() -> None:
    config = TushareConfig.from_env(env_var="TUSHARE_TOKEN")
    client = TushareDataClient(config=config)
    trade_dates = ["20240102", "20240103", "20240104", "20240201", "20240202"]

    market_data = client.fetch_market_data_with_universe_metadata(
        trade_dates=trade_dates,
        ts_codes=["000001.SZ", "000002.SZ", "000333.SZ", "600000.SH", "600519.SH"],
    )

    pipeline = ResearchPipeline(
        factors=[
            MomentumFactor(name="momentum", lookback=1),
            DailyBasicFieldFactor(name="pe", field="pe", trade_dates=trade_dates, data_client=client),
            DailyBasicFieldFactor(name="pb", field="pb", trade_dates=trade_dates, data_client=client),
            DailyBasicFieldFactor(name="size", field="total_mv", trade_dates=trade_dates, data_client=client),
        ],
        factor_weights={"momentum": 1.0, "pe": -1.0, "pb": -1.0, "size": -0.5},
        portfolio_constructor=TopNPercentLongOnlyConstructor(
            top_percent=0.2,
            rebalance_frequency="monthly",
        ),
        backtest_engine=BacktestEngine(
            initial_capital=1.0,
            transaction_cost_rate=0.001,
            slippage_rate=0.0005,
        ),
        universe_filter=UniverseFilter(
            config=UniverseFilterConfig(
                min_price=5.0,
                exclude_st=True,
                exclude_suspended=True,
                min_listed_days=60,
                exclude_limit_up=True,
                exclude_limit_down=True,
                min_turnover_amount=1_000_000.0,
            )
        ),
    )

    composite, weights, result = pipeline.run(market_data)
    print("Composite dates:", list(composite.values.keys()))
    print("Rebalance weights:", weights.weights)
    print("Metrics:", result.metrics)


if __name__ == "__main__":
    main()
