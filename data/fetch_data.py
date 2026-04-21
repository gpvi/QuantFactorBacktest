# 通过 tushare 获取数据
from os import getenv, makedirs
from pathlib import Path
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


def save_to_db():
    # 连接数据库并保存数据的逻辑
    pass


def save_to_csv(df, file_path):
    df.to_csv(file_path, index=False)


if __name__ == "__main__":
    fetcher = TushareDataFetcher()
    csv_dir = Path(__file__).parent / "csv"
    makedirs(csv_dir, exist_ok=True)

    # 1) pro.query('daily', ...) 批量查询
    df_query = fetcher.fetch_daily_by_query(
        ts_codes=["000001.SZ", "600000.SH"],
        start_date="20180701",
        end_date="20180718",
    )

    # 2) 按交易日获取全市场
    # df_trade_date = fetcher.fetch_daily_by_trade_date(trade_date="20180810")

    # 保存到 csv 文件夹
    save_to_csv(df_query, csv_dir / "daily_query.csv")
    # save_to_csv(df_trade_date, csv_dir / "daily_trade_date.csv")
