import unittest

from quant_factor_backtest.domain import FactorSignal, MarketData
from quant_factor_backtest.universe import UniverseFilter, UniverseFilterConfig


class UniverseFilterTest(unittest.TestCase):
    def test_apply_filters_excluded_assets_and_low_price_assets(self) -> None:
        market_data = MarketData(
            prices={
                "2024-01-02": {"A": 10.0, "B": 4.0, "C": 8.0},
                "2024-02-01": {"A": 11.0, "B": 6.0, "C": 7.0},
            }
        )
        universe_filter = UniverseFilter(
            config=UniverseFilterConfig(
                min_price=5.0,
                excluded_assets={"2024-02-01": {"C"}},
            )
        )

        context = universe_filter.apply(market_data)

        self.assertEqual(context.market_data.prices["2024-01-02"], {"A": 10.0, "C": 8.0})
        self.assertEqual(context.market_data.prices["2024-02-01"], {"A": 11.0, "B": 6.0})

    def test_apply_to_signal_keeps_only_allowed_assets(self) -> None:
        signal = FactorSignal(
            name="f1",
            values={"2024-01-02": {"A": 1.0, "B": 2.0, "C": 3.0}},
        )
        universe_filter = UniverseFilter(config=UniverseFilterConfig())

        filtered_signal = universe_filter.apply_to_signal(signal, {"2024-01-02": {"A", "C"}})

        self.assertEqual(filtered_signal.values["2024-01-02"], {"A": 1.0, "C": 3.0})

    def test_apply_filters_st_suspension_listing_age_limit_and_liquidity(self) -> None:
        market_data = MarketData(
            prices={
                "2024-01-02": {"A": 10.0, "B": 10.0, "C": 10.0, "D": 10.0, "E": 10.0, "F": 10.0},
            },
            is_st={
                "2024-01-02": {"A": False, "B": True, "C": False, "D": False, "E": False, "F": False},
            },
            is_suspended={
                "2024-01-02": {"A": False, "B": False, "C": True, "D": False, "E": False, "F": False},
            },
            listed_days={
                "2024-01-02": {"A": 200, "B": 200, "C": 200, "D": 30, "E": 200, "F": 200},
            },
            is_limit_up={
                "2024-01-02": {"A": False, "B": False, "C": False, "D": False, "E": True, "F": False},
            },
            is_limit_down={
                "2024-01-02": {"A": False, "B": False, "C": False, "D": False, "E": False, "F": True},
            },
            turnover_amount={
                "2024-01-02": {"A": 2_000_000.0, "B": 2_000_000.0, "C": 2_000_000.0, "D": 2_000_000.0, "E": 2_000_000.0, "F": 100_000.0},
            },
        )
        universe_filter = UniverseFilter(
            config=UniverseFilterConfig(
                exclude_st=True,
                exclude_suspended=True,
                min_listed_days=60,
                exclude_limit_up=True,
                exclude_limit_down=True,
                min_turnover_amount=1_000_000.0,
            )
        )

        context = universe_filter.apply(market_data)

        self.assertEqual(context.market_data.prices["2024-01-02"], {"A": 10.0})


if __name__ == "__main__":
    unittest.main()
