from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from ..models import RawRecords


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


@dataclass
class TushareFetcher:
    config: TushareConfig
    pro_client: Any | None = None

    def fetch_records(
        self,
        endpoint: str,
        trade_date: str,
        ts_codes: list[str],
        fields: str,
    ) -> RawRecords:
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
        return self.frame_to_records(frame)

    def fetch_records_in_range(
        self,
        endpoint: str,
        start_date: str,
        end_date: str,
        ts_codes: list[str],
        fields: str,
    ) -> RawRecords:
        pro = self._pro_api()
        params: dict[str, Any] = {"fields": fields}
        if endpoint in {"daily", "adj_factor", "daily_basic", "suspend_d", "stk_limit"}:
            params["start_date"] = start_date
            params["end_date"] = end_date
        if endpoint in {"daily", "adj_factor", "stk_limit"} and ts_codes:
            params["ts_code"] = ",".join(ts_codes)
        frame = getattr(pro, endpoint)(**params)
        return self.frame_to_records(frame)

    def _pro_api(self) -> Any:
        if self.pro_client is not None:
            return self.pro_client
        try:
            import tushare as ts
        except ImportError as exc:
            raise ImportError("tushare is required for TushareDataClient. Install with `pip install .[data]`.") from exc
        ts.set_token(self.config.token)
        self.pro_client = ts.pro_api()
        return self.pro_client

    @staticmethod
    def frame_to_records(frame: Any) -> RawRecords:
        if hasattr(frame, "to_dict"):
            return list(frame.to_dict("records"))
        if isinstance(frame, list):
            return frame
        raise TypeError("Unsupported Tushare frame type; expected DataFrame-like object or list of dicts.")
