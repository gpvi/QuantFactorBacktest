from __future__ import annotations

from pathlib import Path
from typing import Any

from ..cache import CacheBackend, NullCache, SqliteCache
from ..models import RawRecords, RecordsByDate
from .assemble import build_factor_table, build_price_table, build_universe_table
from .convert import factor_table_to_signal, price_table_to_market_data, universe_table_to_market_data
from .fetch import TushareConfig, TushareFetcher
from ...domain import FactorSignal, MarketData


class TushareDataClient:
    def __init__(
        self,
        config: TushareConfig,
        pro_client: Any | None = None,
        cache_backend: CacheBackend | None = None,
    ) -> None:
        self.config = config
        self._fetcher = TushareFetcher(config=config, pro_client=pro_client)
        self._cache = cache_backend or self._default_cache_backend()

    @property
    def _pro(self) -> Any | None:
        return self._fetcher.pro_client

    def fetch_market_data(
        self,
        trade_dates: list[str],
        ts_codes: list[str],
    ) -> MarketData:
        daily_records_by_date = self._load_or_fetch_by_trade_dates(
            endpoint="daily",
            trade_dates=trade_dates,
            ts_codes=ts_codes,
            fields="ts_code,trade_date,close,amount",
        )
        adjustment_records_by_date = self._load_adj_factor_by_trade_dates(
            trade_dates=trade_dates,
            ts_codes=ts_codes,
        )
        price_table = build_price_table(
            trade_dates=trade_dates,
            daily_rows_by_date=daily_records_by_date,
            adj_rows_by_date=adjustment_records_by_date,
            use_adj=bool(self.config.adj),
        )
        return price_table_to_market_data(price_table, trade_dates)

    def fetch_market_data_with_universe_metadata(
        self,
        trade_dates: list[str],
        ts_codes: list[str],
    ) -> MarketData:
        stock_basic_records = self._load_or_fetch(
            endpoint="stock_basic",
            trade_date="all",
            ts_codes=[],
            fields="ts_code,name,list_date",
        )
        daily_records_by_date = self._load_or_fetch_by_trade_dates(
            endpoint="daily",
            trade_dates=trade_dates,
            ts_codes=ts_codes,
            fields="ts_code,trade_date,close,amount",
        )
        adjustment_records_by_date = self._load_adj_factor_by_trade_dates(
            trade_dates=trade_dates,
            ts_codes=ts_codes,
        )
        suspension_records_by_date = self._load_or_fetch_by_trade_dates(
            endpoint="suspend_d",
            trade_dates=trade_dates,
            ts_codes=[],
            fields="ts_code,trade_date,suspend_type",
        )
        limit_records_by_date = self._load_or_fetch_by_trade_dates(
            endpoint="stk_limit",
            trade_dates=trade_dates,
            ts_codes=ts_codes,
            fields="ts_code,trade_date,up_limit,down_limit",
        )
        universe_table = build_universe_table(
            trade_dates=trade_dates,
            daily_rows_by_date=daily_records_by_date,
            adj_rows_by_date=adjustment_records_by_date,
            suspend_rows_by_date=suspension_records_by_date,
            limit_rows_by_date=limit_records_by_date,
            stock_basic_records=stock_basic_records,
            use_adj=bool(self.config.adj),
        )
        return universe_table_to_market_data(universe_table, trade_dates)

    def fetch_daily_basic(
        self,
        trade_date: str,
        fields: str = "ts_code,trade_date,pe,pb,total_mv",
    ) -> RawRecords:
        return self._load_or_fetch(
            endpoint="daily_basic",
            trade_date=trade_date,
            ts_codes=[],
            fields=fields,
        )

    def fetch_factor_signal(
        self,
        trade_dates: list[str],
        field: str,
        factor_name: str | None = None,
    ) -> FactorSignal:
        requested_fields = f"ts_code,trade_date,{field}"
        daily_basic_records_by_date = self._load_or_fetch_by_trade_dates(
            endpoint="daily_basic",
            trade_dates=trade_dates,
            ts_codes=[],
            fields=requested_fields,
        )
        factor_table = build_factor_table(trade_dates, daily_basic_records_by_date, field)
        return factor_table_to_signal(factor_table, trade_dates, factor_name or field)

    def _load_adj_factor_by_trade_dates(self, trade_dates: list[str], ts_codes: list[str]) -> RecordsByDate:
        if not self.config.adj:
            return {}
        return self._load_or_fetch_by_trade_dates(
            endpoint="adj_factor",
            trade_dates=trade_dates,
            ts_codes=ts_codes,
            fields="ts_code,trade_date,adj_factor",
        )

    def _load_or_fetch(
        self,
        endpoint: str,
        trade_date: str,
        ts_codes: list[str],
        fields: str,
    ) -> RawRecords:
        cache_key = self._cache_key(endpoint=endpoint, trade_date=trade_date, ts_codes=ts_codes, fields=fields)
        try:
            return self._cache.get(cache_key)
        except KeyError:
            pass
        fetched_records = self._fetcher.fetch_records(
            endpoint=endpoint,
            trade_date=trade_date,
            ts_codes=ts_codes,
            fields=fields,
        )
        self._cache.set(cache_key, fetched_records)
        return fetched_records

    def _load_or_fetch_by_trade_dates(
        self,
        endpoint: str,
        trade_dates: list[str],
        ts_codes: list[str],
        fields: str,
    ) -> RecordsByDate:
        # Cache is keyed per trade date so one missing day does not force us to
        # refetch the whole window.
        records_by_date: RecordsByDate = {}
        missing_trade_dates: list[str] = []
        for trade_date in trade_dates:
            cache_key = self._cache_key(endpoint=endpoint, trade_date=trade_date, ts_codes=ts_codes, fields=fields)
            try:
                records_by_date[trade_date] = self._cache.get(cache_key)
            except KeyError:
                missing_trade_dates.append(trade_date)
        if missing_trade_dates:
            fetched_records_by_date = self._fetch_records_by_trade_dates(
                endpoint=endpoint,
                trade_dates=missing_trade_dates,
                ts_codes=ts_codes,
                fields=fields,
            )
            for trade_date in missing_trade_dates:
                records_for_date = fetched_records_by_date.get(trade_date, [])
                records_by_date[trade_date] = records_for_date
                cache_key = self._cache_key(endpoint=endpoint, trade_date=trade_date, ts_codes=ts_codes, fields=fields)
                self._cache.set(cache_key, records_for_date)
        return records_by_date

    def _fetch_records_by_trade_dates(
        self,
        endpoint: str,
        trade_dates: list[str],
        ts_codes: list[str],
        fields: str,
    ) -> RecordsByDate:
        if not trade_dates:
            return {}
        sorted_trade_dates = sorted(set(trade_dates))
        if len(sorted_trade_dates) == 1:
            return {
                sorted_trade_dates[0]: self._fetcher.fetch_records(
                    endpoint=endpoint,
                    trade_date=sorted_trade_dates[0],
                    ts_codes=ts_codes,
                    fields=fields,
                )
            }

        requested_trade_dates = set(sorted_trade_dates)
        try:
            fetched_records = self._fetcher.fetch_records_in_range(
                endpoint=endpoint,
                start_date=sorted_trade_dates[0],
                end_date=sorted_trade_dates[-1],
                ts_codes=ts_codes,
                fields=fields,
            )
        except TypeError:
            return {
                trade_date: self._fetcher.fetch_records(
                    endpoint=endpoint,
                    trade_date=trade_date,
                    ts_codes=ts_codes,
                    fields=fields,
                )
                for trade_date in sorted_trade_dates
            }

        records_grouped_by_trade_date: RecordsByDate = {trade_date: [] for trade_date in sorted_trade_dates}
        for fetched_record in fetched_records:
            trade_date = str(fetched_record.get("trade_date", ""))
            if trade_date in requested_trade_dates:
                records_grouped_by_trade_date.setdefault(trade_date, []).append(fetched_record)
        return records_grouped_by_trade_date

    def _default_cache_backend(self) -> CacheBackend:
        if self.config.cache_dir:
            return SqliteCache(db_path=str(Path(self.config.cache_dir) / "cache.sqlite3"))
        return NullCache()

    def _cache_key(
        self,
        endpoint: str,
        trade_date: str,
        ts_codes: list[str],
        fields: str,
    ) -> str:
        code_key = "all" if not ts_codes else "_".join(sorted(ts_codes)).replace(".", "_")
        field_key = fields.replace(",", "_")
        return f"{endpoint}/{trade_date}__{code_key}__{field_key}"
