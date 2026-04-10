from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from ..models import RawRecords
from ...constants.tushare import (
    DEFAULT_ADJUSTMENT_MODE,
    DEFAULT_CACHE_DIRECTORY,
    DEFAULT_TOKEN_ENV_VAR,
    ENDPOINT_STOCK_BASIC,
    PARAM_END_DATE,
    PARAM_EXCHANGE,
    PARAM_FIELDS,
    PARAM_LIST_STATUS,
    PARAM_START_DATE,
    PARAM_TRADE_DATE,
    PARAM_TS_CODE,
    STOCK_BASIC_LIST_STATUS_LISTED,
    TRADE_DATE_PARAM_ENDPOINTS,
    TS_CODE_PARAM_ENDPOINTS,
)


@dataclass(frozen=True)
class TushareConfig:
    token: str
    adj: str | None = DEFAULT_ADJUSTMENT_MODE
    cache_dir: str | None = DEFAULT_CACHE_DIRECTORY

    @classmethod
    def from_env(
        cls,
        env_var: str = DEFAULT_TOKEN_ENV_VAR,
        adj: str | None = DEFAULT_ADJUSTMENT_MODE,
    ) -> "TushareConfig":
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
        params: dict[str, Any] = {PARAM_FIELDS: fields}
        if endpoint in TRADE_DATE_PARAM_ENDPOINTS:
            params[PARAM_TRADE_DATE] = trade_date
        if endpoint in TS_CODE_PARAM_ENDPOINTS and ts_codes:
            params[PARAM_TS_CODE] = ",".join(ts_codes)
        if endpoint == ENDPOINT_STOCK_BASIC:
            params[PARAM_EXCHANGE] = ""
            params[PARAM_LIST_STATUS] = STOCK_BASIC_LIST_STATUS_LISTED
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
        params: dict[str, Any] = {PARAM_FIELDS: fields}
        if endpoint in TRADE_DATE_PARAM_ENDPOINTS:
            params[PARAM_START_DATE] = start_date
            params[PARAM_END_DATE] = end_date
        if endpoint in TS_CODE_PARAM_ENDPOINTS and ts_codes:
            params[PARAM_TS_CODE] = ",".join(ts_codes)
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
