from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from ..constants.tushare import (
    COLUMN_ASSET,
    COLUMN_IS_LIMIT_DOWN,
    COLUMN_IS_LIMIT_UP,
    COLUMN_IS_ST,
    COLUMN_IS_SUSPENDED,
    COLUMN_LISTED_DAYS,
    COLUMN_PRICE,
    COLUMN_TRADE_DATE,
    COLUMN_TURNOVER_AMOUNT,
)
from ..data.tushare.convert import filtered_market_data_from_frame, market_data_to_table
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
        # Universe filtering is expressed in polars so every rule is applied to the
        # same tabular view before we convert back to the domain object.
        market_table = market_data_to_table(market_data)
        filter_expressions: list[pl.Expr] = []
        if self.config.min_price is not None:
            filter_expressions.append(pl.col(COLUMN_PRICE) >= self.config.min_price)
        if self.config.exclude_st:
            filter_expressions.append(~pl.col(COLUMN_IS_ST))
        if self.config.exclude_suspended:
            filter_expressions.append(~pl.col(COLUMN_IS_SUSPENDED))
        if self.config.min_listed_days is not None:
            filter_expressions.append(pl.col(COLUMN_LISTED_DAYS) >= self.config.min_listed_days)
        if self.config.exclude_limit_up:
            filter_expressions.append(~pl.col(COLUMN_IS_LIMIT_UP))
        if self.config.exclude_limit_down:
            filter_expressions.append(~pl.col(COLUMN_IS_LIMIT_DOWN))
        if self.config.min_turnover_amount is not None:
            filter_expressions.append(pl.col(COLUMN_TURNOVER_AMOUNT) >= self.config.min_turnover_amount)

        filtered_table = market_table
        for filter_expression in filter_expressions:
            filtered_table = filtered_table.filter(filter_expression)

        manually_excluded_assets = self.config.excluded_assets or {}
        if manually_excluded_assets:
            excluded_asset_rows = [
                {COLUMN_TRADE_DATE: date, COLUMN_ASSET: asset}
                for date, assets in manually_excluded_assets.items()
                for asset in assets
            ]
            if excluded_asset_rows:
                excluded_asset_table = pl.DataFrame(excluded_asset_rows)
                filtered_table = filtered_table.join(
                    excluded_asset_table,
                    on=[COLUMN_TRADE_DATE, COLUMN_ASSET],
                    how="anti",
                )

        allowed_assets: dict[str, set[str]] = {}
        for row in filtered_table.select(COLUMN_TRADE_DATE, COLUMN_ASSET).to_dicts():
            trade_date = str(row[COLUMN_TRADE_DATE])
            allowed_assets.setdefault(trade_date, set()).add(str(row[COLUMN_ASSET]))
        for trade_date in market_data.prices:
            allowed_assets.setdefault(trade_date, set())

        # The research layer still consumes MarketData, so the filtered table is
        # adapted back into the existing domain structure here.
        filtered_market_data = filtered_market_data_from_frame(
            filtered_table,
            list(market_data.prices.keys()),
            include_is_st=market_data.is_st is not None,
            include_is_suspended=market_data.is_suspended is not None,
            include_listed_days=market_data.listed_days is not None,
            include_is_limit_up=market_data.is_limit_up is not None,
            include_is_limit_down=market_data.is_limit_down is not None,
            include_turnover_amount=market_data.turnover_amount is not None,
        )
        return FilteredMarketContext(
            market_data=filtered_market_data,
            allowed_assets=allowed_assets,
        )

    def apply_to_signal(self, signal: FactorSignal, allowed_assets: dict[str, set[str]]) -> FactorSignal:
        filtered_values: TimeSeriesMatrix = {}
        for trade_date, cross_section in signal.values.items():
            allowed_assets_on_date = allowed_assets.get(trade_date, set(cross_section))
            filtered_values[trade_date] = {
                asset: value for asset, value in cross_section.items() if asset in allowed_assets_on_date
            }
        return FactorSignal(name=signal.name, values=filtered_values)
