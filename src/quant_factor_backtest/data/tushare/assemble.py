from __future__ import annotations

from datetime import datetime
from typing import Any

import polars as pl

from ...constants.tushare import (
    COLUMN_ADJ_FACTOR,
    COLUMN_AMOUNT,
    COLUMN_CLOSE,
    COLUMN_DOWN_LIMIT,
    COLUMN_IS_LIMIT_DOWN,
    COLUMN_IS_LIMIT_UP,
    COLUMN_IS_ST,
    COLUMN_IS_SUSPENDED,
    COLUMN_LIST_DATE,
    COLUMN_LISTED_DAYS,
    COLUMN_NAME,
    COLUMN_PRICE,
    COLUMN_TRADE_DATE,
    COLUMN_TS_CODE,
    COLUMN_UP_LIMIT,
    COLUMN_VALUE,
)
from ..models import RecordsByDate


def build_price_table(
    trade_dates: list[str],
    daily_rows_by_date: RecordsByDate,
    adj_rows_by_date: RecordsByDate | None = None,
    *,
    use_adj: bool,
) -> pl.DataFrame:
    daily_price_rows = [
        {
            COLUMN_TRADE_DATE: trade_date,
            COLUMN_TS_CODE: str(row[COLUMN_TS_CODE]),
            COLUMN_CLOSE: float(row[COLUMN_CLOSE]),
        }
        for trade_date in trade_dates
        for row in daily_rows_by_date.get(trade_date, [])
    ]
    if not daily_price_rows:
        return pl.DataFrame(
            schema={
                COLUMN_TRADE_DATE: pl.Utf8,
                COLUMN_TS_CODE: pl.Utf8,
                COLUMN_CLOSE: pl.Float64,
                COLUMN_PRICE: pl.Float64,
            }
        )

    daily_price_table = pl.DataFrame(daily_price_rows)
    if use_adj and adj_rows_by_date:
        adjustment_rows = [
            {
                COLUMN_TRADE_DATE: trade_date,
                COLUMN_TS_CODE: str(row[COLUMN_TS_CODE]),
                COLUMN_ADJ_FACTOR: float(row[COLUMN_ADJ_FACTOR]),
            }
            for trade_date in trade_dates
            for row in adj_rows_by_date.get(trade_date, [])
        ]
        if adjustment_rows:
            adjustment_table = pl.DataFrame(adjustment_rows)
            return daily_price_table.join(
                adjustment_table,
                on=[COLUMN_TRADE_DATE, COLUMN_TS_CODE],
                how="left",
            ).with_columns(
                # When no adjustment factor exists for a row we keep the raw close
                # so sparse adj_factor data does not drop otherwise valid prices.
                pl.when(pl.col(COLUMN_ADJ_FACTOR).is_not_null())
                .then(pl.col(COLUMN_CLOSE) * pl.col(COLUMN_ADJ_FACTOR))
                .otherwise(pl.col(COLUMN_CLOSE))
                .alias(COLUMN_PRICE)
            )
    return daily_price_table.with_columns(pl.col(COLUMN_CLOSE).alias(COLUMN_PRICE))


def build_universe_table(
    trade_dates: list[str],
    daily_rows_by_date: RecordsByDate,
    adj_rows_by_date: RecordsByDate | None,
    suspend_rows_by_date: RecordsByDate,
    limit_rows_by_date: RecordsByDate,
    stock_basic_records: list[dict[str, Any]],
    *,
    use_adj: bool,
) -> pl.DataFrame:
    price_table = build_price_table(
        trade_dates=trade_dates,
        daily_rows_by_date=daily_rows_by_date,
        adj_rows_by_date=adj_rows_by_date,
        use_adj=use_adj,
    )
    if price_table.height == 0:
        return pl.DataFrame(
            schema={
                COLUMN_TRADE_DATE: pl.Utf8,
                COLUMN_TS_CODE: pl.Utf8,
                COLUMN_PRICE: pl.Float64,
                COLUMN_AMOUNT: pl.Float64,
                COLUMN_IS_ST: pl.Boolean,
                COLUMN_IS_SUSPENDED: pl.Boolean,
                COLUMN_LISTED_DAYS: pl.Int64,
                COLUMN_IS_LIMIT_UP: pl.Boolean,
                COLUMN_IS_LIMIT_DOWN: pl.Boolean,
            }
        )

    daily_turnover_table = pl.DataFrame(
        [
            {
                COLUMN_TRADE_DATE: trade_date,
                COLUMN_TS_CODE: str(row[COLUMN_TS_CODE]),
                COLUMN_AMOUNT: float(row.get(COLUMN_AMOUNT, 0.0)),
            }
            for trade_date in trade_dates
            for row in daily_rows_by_date.get(trade_date, [])
        ]
    )
    universe_table = price_table.join(
        daily_turnover_table,
        on=[COLUMN_TRADE_DATE, COLUMN_TS_CODE],
        how="left",
    )

    stock_basic_table = pl.DataFrame(
        [
            {
                COLUMN_TS_CODE: str(record[COLUMN_TS_CODE]),
                COLUMN_NAME: str(record.get(COLUMN_NAME, "")),
                COLUMN_LIST_DATE: str(record.get(COLUMN_LIST_DATE, "")),
            }
            for record in stock_basic_records
        ]
    )
    if stock_basic_table.height > 0:
        universe_table = universe_table.join(stock_basic_table, on=COLUMN_TS_CODE, how="left")
    else:
        universe_table = universe_table.with_columns(
            pl.lit("").alias(COLUMN_NAME),
            pl.lit("").alias(COLUMN_LIST_DATE),
        )

    suspension_rows = [
        {
            COLUMN_TRADE_DATE: trade_date,
            COLUMN_TS_CODE: str(row[COLUMN_TS_CODE]),
            COLUMN_IS_SUSPENDED: True,
        }
        for trade_date in trade_dates
        for row in suspend_rows_by_date.get(trade_date, [])
    ]
    if suspension_rows:
        suspension_table = pl.DataFrame(suspension_rows)
        universe_table = universe_table.join(
            suspension_table,
            on=[COLUMN_TRADE_DATE, COLUMN_TS_CODE],
            how="left",
        )
    else:
        universe_table = universe_table.with_columns(pl.lit(None).alias(COLUMN_IS_SUSPENDED))

    limit_rows = [
        {
            COLUMN_TRADE_DATE: trade_date,
            COLUMN_TS_CODE: str(row[COLUMN_TS_CODE]),
            COLUMN_UP_LIMIT: float(row.get(COLUMN_UP_LIMIT, 0.0)),
            COLUMN_DOWN_LIMIT: float(row.get(COLUMN_DOWN_LIMIT, 0.0)),
        }
        for trade_date in trade_dates
        for row in limit_rows_by_date.get(trade_date, [])
    ]
    if limit_rows:
        limit_table = pl.DataFrame(limit_rows)
        universe_table = universe_table.join(
            limit_table,
            on=[COLUMN_TRADE_DATE, COLUMN_TS_CODE],
            how="left",
        )
    else:
        universe_table = universe_table.with_columns(
            pl.lit(0.0).alias(COLUMN_UP_LIMIT),
            pl.lit(0.0).alias(COLUMN_DOWN_LIMIT),
        )

    # Nulls are normalized before deriving boolean flags so every downstream rule
    # can treat "missing metadata" as an explicit default.
    return universe_table.with_columns(
        pl.col(COLUMN_AMOUNT).fill_null(0.0),
        pl.col(COLUMN_NAME).fill_null(""),
        pl.col(COLUMN_LIST_DATE).fill_null(""),
        pl.col(COLUMN_IS_SUSPENDED).fill_null(False),
        pl.col(COLUMN_UP_LIMIT).fill_null(0.0),
        pl.col(COLUMN_DOWN_LIMIT).fill_null(0.0),
    ).with_columns(
        pl.col(COLUMN_NAME).str.to_uppercase().str.contains("ST").alias(COLUMN_IS_ST),
        pl.struct([COLUMN_TRADE_DATE, COLUMN_LIST_DATE]).map_elements(
            lambda value: _days_since_listing(str(value[COLUMN_TRADE_DATE]), str(value[COLUMN_LIST_DATE])),
            return_dtype=pl.Int64,
        ).alias(COLUMN_LISTED_DAYS),
        ((pl.col(COLUMN_UP_LIMIT) != 0.0) & (pl.col(COLUMN_CLOSE) >= pl.col(COLUMN_UP_LIMIT))).alias(COLUMN_IS_LIMIT_UP),
        ((pl.col(COLUMN_DOWN_LIMIT) != 0.0) & (pl.col(COLUMN_CLOSE) <= pl.col(COLUMN_DOWN_LIMIT))).alias(COLUMN_IS_LIMIT_DOWN),
    )


def build_factor_table(trade_dates: list[str], records_by_date: RecordsByDate, field: str) -> pl.DataFrame:
    factor_rows = [
        {
            COLUMN_TRADE_DATE: trade_date,
            COLUMN_TS_CODE: str(record[COLUMN_TS_CODE]),
            COLUMN_VALUE: float(record[field]),
        }
        for trade_date in trade_dates
        for record in records_by_date.get(trade_date, [])
        if record.get(field) is not None
    ]
    if not factor_rows:
        return pl.DataFrame(
            schema={COLUMN_TRADE_DATE: pl.Utf8, COLUMN_TS_CODE: pl.Utf8, COLUMN_VALUE: pl.Float64}
        )
    return pl.DataFrame(factor_rows)


def _days_since_listing(trade_date: str, list_date: str) -> int:
    if not list_date:
        return 0
    trade_day = datetime.strptime(trade_date, "%Y%m%d")
    listed_day = datetime.strptime(list_date, "%Y%m%d")
    return (trade_day - listed_day).days
