from __future__ import annotations

from dataclasses import dataclass

from ..domain import FactorSignal, MarketData, TimeSeriesMatrix


@dataclass(frozen=True)
class UniverseFilterConfig:
    min_price: float | None = None
    excluded_assets: dict[str, set[str]] | None = None
    exclude_st: bool = False
    exclude_suspended: bool = False
    min_listed_days: int | None = None
    exclude_limit_up: bool = False
    exclude_limit_down: bool = False
    min_turnover_amount: float | None = None


@dataclass(frozen=True)
class FilteredMarketContext:
    market_data: MarketData
    allowed_assets: dict[str, set[str]]


@dataclass(frozen=True)
class UniverseFilter:
    config: UniverseFilterConfig

    def apply(self, market_data: MarketData) -> FilteredMarketContext:
        filtered_prices: TimeSeriesMatrix = {}
        allowed_assets: dict[str, set[str]] = {}
        for date, cross_section in market_data.prices.items():
            excluded = (self.config.excluded_assets or {}).get(date, set())
            filtered_cross_section = {
                asset: price
                for asset, price in cross_section.items()
                if self._is_allowed(market_data, date, asset, price, excluded)
            }
            filtered_prices[date] = filtered_cross_section
            allowed_assets[date] = set(filtered_cross_section)
        return FilteredMarketContext(
            market_data=MarketData(
                prices=filtered_prices,
                is_st=self._filter_metadata(market_data.is_st, allowed_assets),
                is_suspended=self._filter_metadata(market_data.is_suspended, allowed_assets),
                listed_days=self._filter_metadata(market_data.listed_days, allowed_assets),
                is_limit_up=self._filter_metadata(market_data.is_limit_up, allowed_assets),
                is_limit_down=self._filter_metadata(market_data.is_limit_down, allowed_assets),
                turnover_amount=self._filter_metadata(market_data.turnover_amount, allowed_assets),
            ),
            allowed_assets=allowed_assets,
        )

    def apply_to_signal(self, signal: FactorSignal, allowed_assets: dict[str, set[str]]) -> FactorSignal:
        filtered_values: TimeSeriesMatrix = {}
        for date, cross_section in signal.values.items():
            allowed = allowed_assets.get(date, set(cross_section))
            filtered_values[date] = {
                asset: value for asset, value in cross_section.items() if asset in allowed
            }
        return FactorSignal(name=signal.name, values=filtered_values)

    def _is_allowed(
        self,
        market_data: MarketData,
        date: str,
        asset: str,
        price: float,
        excluded: set[str],
    ) -> bool:
        if asset in excluded:
            return False
        if self.config.min_price is not None and price < self.config.min_price:
            return False
        if self.config.exclude_st and self._flag(market_data.is_st, date, asset):
            return False
        if self.config.exclude_suspended and self._flag(market_data.is_suspended, date, asset):
            return False
        if self.config.min_listed_days is not None:
            listed_days = self._value(market_data.listed_days, date, asset)
            if listed_days is not None and listed_days < self.config.min_listed_days:
                return False
        if self.config.exclude_limit_up and self._flag(market_data.is_limit_up, date, asset):
            return False
        if self.config.exclude_limit_down and self._flag(market_data.is_limit_down, date, asset):
            return False
        if self.config.min_turnover_amount is not None:
            turnover_amount = self._value(market_data.turnover_amount, date, asset)
            if turnover_amount is not None and turnover_amount < self.config.min_turnover_amount:
                return False
        return True

    def _flag(
        self,
        values: dict[str, dict[str, bool]] | None,
        date: str,
        asset: str,
    ) -> bool:
        return bool(self._value(values, date, asset))

    def _value(
        self,
        values: dict[str, dict[str, float | int | bool]] | None,
        date: str,
        asset: str,
    ) -> float | int | bool | None:
        if values is None:
            return None
        return values.get(date, {}).get(asset)

    def _filter_metadata(
        self,
        values: dict[str, dict[str, float | int | bool]] | None,
        allowed_assets: dict[str, set[str]],
    ) -> dict[str, dict[str, float | int | bool]] | None:
        if values is None:
            return None
        filtered: dict[str, dict[str, float | int | bool]] = {}
        for date, cross_section in values.items():
            allowed = allowed_assets.get(date, set())
            filtered[date] = {
                asset: value for asset, value in cross_section.items() if asset in allowed
            }
        return filtered
