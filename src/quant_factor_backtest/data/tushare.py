from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass
import json
from datetime import datetime
from typing import Any

from ..domain import FactorSignal, MarketData, TimeSeriesMatrix


@dataclass(frozen=True)
class TushareConfig:
    token: str
    adj: str | None = "qfq"
    cache_dir: str | None = ".cache/tushare"

    @classmethod
    def from_env(cls, env_var: str = "TUSHARE_TOKEN", adj: str | None = "qfq") -> "TushareConfig":
        token = os.getenv(env_var)
        if not token:
            raise ValueError(f"Missing Tushare token in environment variable: {env_var}")
        return cls(token=token, adj=adj)


class TushareDataClient:
    def __init__(self, config: TushareConfig, pro_client: Any | None = None) -> None:
        self.config = config
        self._pro = pro_client

    def fetch_market_data(
        self,
        trade_dates: list[str],
        ts_codes: list[str],
    ) -> MarketData:
        prices: TimeSeriesMatrix = {}
        for trade_date in trade_dates:
            daily_rows = self._load_or_fetch(
                endpoint="daily",
                trade_date=trade_date,
                ts_codes=ts_codes,
                fields="ts_code,trade_date,close,amount",
            )
            if self.config.adj:
                adj_rows = self._load_or_fetch(
                    endpoint="adj_factor",
                    trade_date=trade_date,
                    ts_codes=ts_codes,
                    fields="ts_code,trade_date,adj_factor",
                )
                adj_map = {row["ts_code"]: float(row["adj_factor"]) for row in adj_rows}
            else:
                adj_map = {}
            cross_section: dict[str, float] = {}
            for row in daily_rows:
                asset = str(row["ts_code"])
                close = float(row["close"])
                if self.config.adj and asset in adj_map:
                    cross_section[asset] = close * adj_map[asset]
                else:
                    cross_section[asset] = close
            prices[trade_date] = cross_section
        return MarketData(prices=prices)

    def fetch_market_data_with_universe_metadata(
        self,
        trade_dates: list[str],
        ts_codes: list[str],
    ) -> MarketData:
        base_market_data = self.fetch_market_data(trade_dates=trade_dates, ts_codes=ts_codes)
        stock_basic_records = self._load_or_fetch(
            endpoint="stock_basic",
            trade_date="all",
            ts_codes=[],
            fields="ts_code,name,list_date",
        )
        stock_basic_map = {
            str(record["ts_code"]): {
                "name": str(record.get("name", "")),
                "list_date": str(record.get("list_date", "")),
            }
            for record in stock_basic_records
        }
        is_st: dict[str, dict[str, bool]] = {}
        is_suspended: dict[str, dict[str, bool]] = {}
        listed_days: dict[str, dict[str, int]] = {}
        is_limit_up: dict[str, dict[str, bool]] = {}
        is_limit_down: dict[str, dict[str, bool]] = {}
        turnover_amount: TimeSeriesMatrix = {}
        for trade_date in trade_dates:
            daily_rows = self._load_or_fetch(
                endpoint="daily",
                trade_date=trade_date,
                ts_codes=ts_codes,
                fields="ts_code,trade_date,close,amount",
            )
            daily_map = {str(row["ts_code"]): row for row in daily_rows}
            suspend_rows = self._load_or_fetch(
                endpoint="suspend_d",
                trade_date=trade_date,
                ts_codes=[],
                fields="ts_code,trade_date,suspend_type",
            )
            suspended_assets = {str(row["ts_code"]) for row in suspend_rows}
            limit_rows = self._load_or_fetch(
                endpoint="stk_limit",
                trade_date=trade_date,
                ts_codes=ts_codes,
                fields="ts_code,trade_date,up_limit,down_limit",
            )
            limit_map = {str(row["ts_code"]): row for row in limit_rows}
            is_st[trade_date] = {}
            is_suspended[trade_date] = {}
            listed_days[trade_date] = {}
            is_limit_up[trade_date] = {}
            is_limit_down[trade_date] = {}
            turnover_amount[trade_date] = {}
            for asset in base_market_data.prices.get(trade_date, {}):
                basic = stock_basic_map.get(asset, {})
                name = basic.get("name", "")
                list_date = basic.get("list_date", "")
                close = float(daily_map.get(asset, {}).get("close", 0.0))
                amount = float(daily_map.get(asset, {}).get("amount", 0.0))
                limit_row = limit_map.get(asset, {})
                up_limit = float(limit_row.get("up_limit", 0.0)) if limit_row else 0.0
                down_limit = float(limit_row.get("down_limit", 0.0)) if limit_row else 0.0
                is_st[trade_date][asset] = "ST" in name.upper()
                is_suspended[trade_date][asset] = asset in suspended_assets
                listed_days[trade_date][asset] = self._days_since_listing(trade_date, list_date)
                is_limit_up[trade_date][asset] = bool(up_limit) and close >= up_limit
                is_limit_down[trade_date][asset] = bool(down_limit) and close <= down_limit
                turnover_amount[trade_date][asset] = amount
        return MarketData(
            prices=base_market_data.prices,
            is_st=is_st,
            is_suspended=is_suspended,
            listed_days=listed_days,
            is_limit_up=is_limit_up,
            is_limit_down=is_limit_down,
            turnover_amount=turnover_amount,
        )

    def fetch_daily_basic(
        self,
        trade_date: str,
        fields: str = "ts_code,trade_date,pe,pb,total_mv",
    ) -> list[dict[str, Any]]:
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
        values: TimeSeriesMatrix = {}
        requested_fields = f"ts_code,trade_date,{field}"
        for trade_date in trade_dates:
            records = self.fetch_daily_basic(trade_date=trade_date, fields=requested_fields)
            values[trade_date] = {
                str(record["ts_code"]): float(record[field])
                for record in records
                if record.get(field) is not None
            }
        return FactorSignal(name=factor_name or field, values=values)

    def _pro_api(self) -> Any:
        if self._pro is not None:
            return self._pro
        try:
            import tushare as ts
        except ImportError as exc:
            raise ImportError("tushare is required for TushareDataClient. Install with `pip install .[data]`.") from exc
        ts.set_token(self.config.token)
        self._pro = ts.pro_api()
        return self._pro

    def _frame_to_records(self, frame: Any) -> list[dict[str, Any]]:
        if hasattr(frame, "to_dict"):
            return list(frame.to_dict("records"))
        if isinstance(frame, list):
            return frame
        raise TypeError("Unsupported Tushare frame type; expected DataFrame-like object or list of dicts.")

    def _load_or_fetch(
        self,
        endpoint: str,
        trade_date: str,
        ts_codes: list[str],
        fields: str,
    ) -> list[dict[str, Any]]:
        cache_path = self._cache_path(endpoint=endpoint, trade_date=trade_date, ts_codes=ts_codes, fields=fields)
        if cache_path is not None and cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8"))
        records = self._fetch_records(endpoint=endpoint, trade_date=trade_date, ts_codes=ts_codes, fields=fields)
        if cache_path is not None:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(records, ensure_ascii=True), encoding="utf-8")
        return records

    def _fetch_records(
        self,
        endpoint: str,
        trade_date: str,
        ts_codes: list[str],
        fields: str,
    ) -> list[dict[str, Any]]:
        pro = self._pro_api()
        params: dict[str, Any] = {"fields": fields}
        if endpoint in {"daily", "adj_factor", "daily_basic", "suspend_d", "stk_limit"}:
            params["trade_date"] = trade_date
        if endpoint in {"daily", "adj_factor", "stk_limit"} and ts_codes:
            params["ts_code"] = ",".join(ts_codes)
        if endpoint == "stock_basic":
            params["exchange"] = ""
            params["list_status"] = "L"
        frame = getattr(pro, endpoint)(**params)
        return self._frame_to_records(frame)

    def _cache_path(
        self,
        endpoint: str,
        trade_date: str,
        ts_codes: list[str],
        fields: str,
    ) -> Path | None:
        if not self.config.cache_dir:
            return None
        code_key = "all" if not ts_codes else "_".join(sorted(ts_codes)).replace(".", "_")
        field_key = fields.replace(",", "_")
        return Path(self.config.cache_dir) / endpoint / f"{trade_date}__{code_key}__{field_key}.json"

    def _days_since_listing(self, trade_date: str, list_date: str) -> int:
        if not list_date:
            return 0
        trade_day = datetime.strptime(trade_date, "%Y%m%d")
        listed_day = datetime.strptime(list_date, "%Y%m%d")
        return (trade_day - listed_day).days
