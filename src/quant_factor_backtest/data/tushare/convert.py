from __future__ import annotations

import polars as pl

from ...constants.tushare import (
    COLUMN_AMOUNT,
    COLUMN_ASSET,
    COLUMN_IS_LIMIT_DOWN,
    COLUMN_IS_LIMIT_UP,
    COLUMN_IS_ST,
    COLUMN_IS_SUSPENDED,
    COLUMN_LISTED_DAYS,
    COLUMN_PRICE,
    COLUMN_TRADE_DATE,
    COLUMN_TS_CODE,
    COLUMN_TURNOVER_AMOUNT,
    COLUMN_VALUE,
)
from ...domain import FactorSignal, MarketData, TimeSeriesMatrix


def price_table_to_market_data(price_table: pl.DataFrame, trade_dates: list[str]) -> MarketData:
    return MarketData(prices=_frame_to_float_matrix(price_table, trade_dates, COLUMN_PRICE))


def universe_table_to_market_data(universe_table: pl.DataFrame, trade_dates: list[str]) -> MarketData:
    return MarketData(
        prices=_frame_to_float_matrix(universe_table, trade_dates, COLUMN_PRICE),
        is_st=_frame_to_bool_matrix(universe_table, trade_dates, COLUMN_IS_ST),
        is_suspended=_frame_to_bool_matrix(universe_table, trade_dates, COLUMN_IS_SUSPENDED),
        listed_days=_frame_to_int_matrix(universe_table, trade_dates, COLUMN_LISTED_DAYS),
        is_limit_up=_frame_to_bool_matrix(universe_table, trade_dates, COLUMN_IS_LIMIT_UP),
        is_limit_down=_frame_to_bool_matrix(universe_table, trade_dates, COLUMN_IS_LIMIT_DOWN),
        turnover_amount=_frame_to_float_matrix(universe_table, trade_dates, COLUMN_AMOUNT),
    )


def factor_table_to_signal(factor_table: pl.DataFrame, trade_dates: list[str], factor_name: str) -> FactorSignal:
    return FactorSignal(name=factor_name, values=_frame_to_float_matrix(factor_table, trade_dates, COLUMN_VALUE))


def market_data_to_table(market_data: MarketData) -> pl.DataFrame:
    # UniverseFilter still works on a tabular view, so this adapter flattens the
    # domain object back into one row per trade_date / asset.
    table_rows: list[dict[str, object]] = []
    for trade_date, cross_section in market_data.prices.items():
        for asset, price in cross_section.items():
            table_rows.append(
                {
                    COLUMN_TRADE_DATE: trade_date,
                    COLUMN_ASSET: asset,
                    COLUMN_PRICE: float(price),
                    COLUMN_IS_ST: bool(market_data.is_st.get(trade_date, {}).get(asset, False)) if market_data.is_st else False,
                    COLUMN_IS_SUSPENDED: bool(market_data.is_suspended.get(trade_date, {}).get(asset, False))
                    if market_data.is_suspended
                    else False,
                    COLUMN_LISTED_DAYS: int(market_data.listed_days.get(trade_date, {}).get(asset, 0))
                    if market_data.listed_days
                    else 0,
                    COLUMN_IS_LIMIT_UP: bool(market_data.is_limit_up.get(trade_date, {}).get(asset, False))
                    if market_data.is_limit_up
                    else False,
                    COLUMN_IS_LIMIT_DOWN: bool(market_data.is_limit_down.get(trade_date, {}).get(asset, False))
                    if market_data.is_limit_down
                    else False,
                    COLUMN_TURNOVER_AMOUNT: float(market_data.turnover_amount.get(trade_date, {}).get(asset, 0.0))
                    if market_data.turnover_amount
                    else 0.0,
                }
            )
    return pl.DataFrame(table_rows)


def filtered_market_data_from_frame(
    filtered_table: pl.DataFrame,
    trade_dates: list[str],
    *,
    include_is_st: bool,
    include_is_suspended: bool,
    include_listed_days: bool,
    include_is_limit_up: bool,
    include_is_limit_down: bool,
    include_turnover_amount: bool,
) -> MarketData:
    return MarketData(
        prices=_frame_to_float_matrix(filtered_table, trade_dates, COLUMN_PRICE),
        is_st=_frame_to_bool_matrix(filtered_table, trade_dates, COLUMN_IS_ST) if include_is_st else None,
        is_suspended=_frame_to_bool_matrix(filtered_table, trade_dates, COLUMN_IS_SUSPENDED)
        if include_is_suspended
        else None,
        listed_days=_frame_to_int_matrix(filtered_table, trade_dates, COLUMN_LISTED_DAYS) if include_listed_days else None,
        is_limit_up=_frame_to_bool_matrix(filtered_table, trade_dates, COLUMN_IS_LIMIT_UP)
        if include_is_limit_up
        else None,
        is_limit_down=_frame_to_bool_matrix(filtered_table, trade_dates, COLUMN_IS_LIMIT_DOWN)
        if include_is_limit_down
        else None,
        turnover_amount=_frame_to_float_matrix(filtered_table, trade_dates, COLUMN_TURNOVER_AMOUNT)
        if include_turnover_amount
        else None,
    )


def _frame_to_bool_matrix(
    data_table: pl.DataFrame,
    trade_dates: list[str],
    value_column: str,
) -> dict[str, dict[str, bool]]:
    bool_matrix = {trade_date: {} for trade_date in trade_dates}
    asset_column = _resolve_asset_column(data_table)
    for row in data_table.select(COLUMN_TRADE_DATE, asset_column, value_column).to_dicts():
        bool_matrix[str(row[COLUMN_TRADE_DATE])][str(row[asset_column])] = bool(row[value_column])
    return bool_matrix


def _frame_to_int_matrix(
    data_table: pl.DataFrame,
    trade_dates: list[str],
    value_column: str,
) -> dict[str, dict[str, int]]:
    int_matrix = {trade_date: {} for trade_date in trade_dates}
    asset_column = _resolve_asset_column(data_table)
    for row in data_table.select(COLUMN_TRADE_DATE, asset_column, value_column).to_dicts():
        int_matrix[str(row[COLUMN_TRADE_DATE])][str(row[asset_column])] = int(row[value_column])
    return int_matrix


def _frame_to_float_matrix(data_table: pl.DataFrame, trade_dates: list[str], value_column: str) -> TimeSeriesMatrix:
    float_matrix: TimeSeriesMatrix = {trade_date: {} for trade_date in trade_dates}
    asset_column = _resolve_asset_column(data_table)
    for row in data_table.select(COLUMN_TRADE_DATE, asset_column, value_column).to_dicts():
        float_matrix[str(row[COLUMN_TRADE_DATE])][str(row[asset_column])] = float(row[value_column])
    return float_matrix


def _resolve_asset_column(data_table: pl.DataFrame) -> str:
    return COLUMN_ASSET if COLUMN_ASSET in data_table.columns else COLUMN_TS_CODE
