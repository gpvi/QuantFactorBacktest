from __future__ import annotations

from datetime import datetime
from typing import Any

import polars as pl

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
            "trade_date": trade_date,
            "ts_code": str(row["ts_code"]),
            "close": float(row["close"]),
        }
        for trade_date in trade_dates
        for row in daily_rows_by_date.get(trade_date, [])
    ]
    if not daily_price_rows:
        return pl.DataFrame(
            schema={
                "trade_date": pl.Utf8,
                "ts_code": pl.Utf8,
                "close": pl.Float64,
                "price": pl.Float64,
            }
        )

    daily_price_table = pl.DataFrame(daily_price_rows)
    if use_adj and adj_rows_by_date:
        adjustment_rows = [
            {
                "trade_date": trade_date,
                "ts_code": str(row["ts_code"]),
                "adj_factor": float(row["adj_factor"]),
            }
            for trade_date in trade_dates
            for row in adj_rows_by_date.get(trade_date, [])
        ]
        if adjustment_rows:
            adjustment_table = pl.DataFrame(adjustment_rows)
            return daily_price_table.join(
                adjustment_table,
                on=["trade_date", "ts_code"],
                how="left",
            ).with_columns(
                # When no adjustment factor exists for a row we keep the raw close
                # so sparse adj_factor data does not drop otherwise valid prices.
                pl.when(pl.col("adj_factor").is_not_null())
                .then(pl.col("close") * pl.col("adj_factor"))
                .otherwise(pl.col("close"))
                .alias("price")
            )
    return daily_price_table.with_columns(pl.col("close").alias("price"))


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
                "trade_date": pl.Utf8,
                "ts_code": pl.Utf8,
                "price": pl.Float64,
                "amount": pl.Float64,
                "is_st": pl.Boolean,
                "is_suspended": pl.Boolean,
                "listed_days": pl.Int64,
                "is_limit_up": pl.Boolean,
                "is_limit_down": pl.Boolean,
            }
        )

    daily_turnover_table = pl.DataFrame(
        [
            {
                "trade_date": trade_date,
                "ts_code": str(row["ts_code"]),
                "amount": float(row.get("amount", 0.0)),
            }
            for trade_date in trade_dates
            for row in daily_rows_by_date.get(trade_date, [])
        ]
    )
    universe_table = price_table.join(daily_turnover_table, on=["trade_date", "ts_code"], how="left")

    stock_basic_table = pl.DataFrame(
        [
            {
                "ts_code": str(record["ts_code"]),
                "name": str(record.get("name", "")),
                "list_date": str(record.get("list_date", "")),
            }
            for record in stock_basic_records
        ]
    )
    if stock_basic_table.height > 0:
        universe_table = universe_table.join(stock_basic_table, on="ts_code", how="left")
    else:
        universe_table = universe_table.with_columns(pl.lit("").alias("name"), pl.lit("").alias("list_date"))

    suspension_rows = [
        {
            "trade_date": trade_date,
            "ts_code": str(row["ts_code"]),
            "is_suspended": True,
        }
        for trade_date in trade_dates
        for row in suspend_rows_by_date.get(trade_date, [])
    ]
    if suspension_rows:
        suspension_table = pl.DataFrame(suspension_rows)
        universe_table = universe_table.join(
            suspension_table,
            on=["trade_date", "ts_code"],
            how="left",
        )
    else:
        universe_table = universe_table.with_columns(pl.lit(None).alias("is_suspended"))

    limit_rows = [
        {
            "trade_date": trade_date,
            "ts_code": str(row["ts_code"]),
            "up_limit": float(row.get("up_limit", 0.0)),
            "down_limit": float(row.get("down_limit", 0.0)),
        }
        for trade_date in trade_dates
        for row in limit_rows_by_date.get(trade_date, [])
    ]
    if limit_rows:
        limit_table = pl.DataFrame(limit_rows)
        universe_table = universe_table.join(
            limit_table,
            on=["trade_date", "ts_code"],
            how="left",
        )
    else:
        universe_table = universe_table.with_columns(pl.lit(0.0).alias("up_limit"), pl.lit(0.0).alias("down_limit"))

    # Nulls are normalized before deriving boolean flags so every downstream rule
    # can treat "missing metadata" as an explicit default.
    return universe_table.with_columns(
        pl.col("amount").fill_null(0.0),
        pl.col("name").fill_null(""),
        pl.col("list_date").fill_null(""),
        pl.col("is_suspended").fill_null(False),
        pl.col("up_limit").fill_null(0.0),
        pl.col("down_limit").fill_null(0.0),
    ).with_columns(
        pl.col("name").str.to_uppercase().str.contains("ST").alias("is_st"),
        pl.struct(["trade_date", "list_date"]).map_elements(
            lambda value: _days_since_listing(str(value["trade_date"]), str(value["list_date"])),
            return_dtype=pl.Int64,
        ).alias("listed_days"),
        ((pl.col("up_limit") != 0.0) & (pl.col("close") >= pl.col("up_limit"))).alias("is_limit_up"),
        ((pl.col("down_limit") != 0.0) & (pl.col("close") <= pl.col("down_limit"))).alias("is_limit_down"),
    )


def build_factor_table(trade_dates: list[str], records_by_date: RecordsByDate, field: str) -> pl.DataFrame:
    factor_rows = [
        {
            "trade_date": trade_date,
            "ts_code": str(record["ts_code"]),
            "value": float(record[field]),
        }
        for trade_date in trade_dates
        for record in records_by_date.get(trade_date, [])
        if record.get(field) is not None
    ]
    if not factor_rows:
        return pl.DataFrame(schema={"trade_date": pl.Utf8, "ts_code": pl.Utf8, "value": pl.Float64})
    return pl.DataFrame(factor_rows)


def _days_since_listing(trade_date: str, list_date: str) -> int:
    if not list_date:
        return 0
    trade_day = datetime.strptime(trade_date, "%Y%m%d")
    listed_day = datetime.strptime(list_date, "%Y%m%d")
    return (trade_day - listed_day).days
