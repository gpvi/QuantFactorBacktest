from __future__ import annotations

from dataclasses import dataclass

from ..domain import FactorSignal, MarketData, TimeSeriesMatrix


@dataclass(frozen=True)
class MomentumFactor:
    name: str = "momentum"
    lookback: int = 1

    def compute(self, market_data: MarketData) -> FactorSignal:
        dates = market_data.dates()
        result: TimeSeriesMatrix = {}
        for idx in range(self.lookback, len(dates)):
            current_date = dates[idx]
            prev_date = dates[idx - self.lookback]
            current_prices = market_data.prices[current_date]
            prev_prices = market_data.prices[prev_date]
            cross_section = {
                asset: (current_prices[asset] / prev_prices[asset]) - 1.0
                for asset in current_prices.keys()
                if asset in prev_prices and prev_prices[asset] != 0
            }
            result[current_date] = cross_section
        return FactorSignal(name=self.name, values=result)


@dataclass(frozen=True)
class StaticDataFactor:
    name: str
    values: TimeSeriesMatrix

    def compute(self, market_data: MarketData) -> FactorSignal:
        return FactorSignal(name=self.name, values=self.values)


@dataclass(frozen=True)
class DailyBasicFieldFactor:
    name: str
    field: str
    trade_dates: list[str]
    data_client: object

    def compute(self, market_data: MarketData | None) -> FactorSignal:
        return self.data_client.fetch_factor_signal(
            trade_dates=self.trade_dates,
            field=self.field,
            factor_name=self.name,
        )
