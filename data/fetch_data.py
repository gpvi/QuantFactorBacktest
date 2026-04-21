# 通过 tushare 获取数据
from os import getenv
from typing import Any, List
import pandas as pd
import tushare as ts


class TushareDataFetcher:
    def __init__(self):
        self.token = getenv("TUSHARE_TOKEN")
        if not self.token:
            raise ValueError("TUSHARE_TOKEN 环境变量未设置")

        ts.set_token(self.token)
        self.pro = ts.pro_api()

    def fetch_daily_by_query(
        self,
        ts_codes: List[str],
        start_date: str,
        end_date: str,
    ) -> Any:
        """批量获取多只股票日线数据"""
        dfs = [
            self.pro.query(
                "daily",
                ts_code=code,
                start_date=start_date,
                end_date=end_date,
            )
            for code in ts_codes
        ]
        return pd.concat(dfs, ignore_index=True)

    def fetch_daily_by_trade_date(self, trade_date: str) -> Any:
        """
        方式3: 按交易日获取全市场日线
        例如: trade_date='20180810'
        """
        return self.pro.daily(trade_date=trade_date)

    def fetch_daily_basic(
        self,
        ts_codes: List[str],
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """
        获取每日指标数据（包含 PE、PB、市值等估值指标）
        """
        all_dfs = []
        for code in ts_codes:
            df = self.pro.daily_basic(
                ts_code=code,
                start_date=start_date,
                end_date=end_date,
            )
            if df is not None and not df.empty:
                all_dfs.append(df)
        return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()
