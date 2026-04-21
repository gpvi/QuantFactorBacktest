# 通过 tushare 获取数据
from os import getenv, makedirs
from pathlib import Path
from typing import Any, List, Dict
import pandas as pd
import tushare as ts
from save_to_csv import save_to_csv, save_to_csv_by_stock


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

    def fetch_and_save_by_stock(
        self,
        ts_codes: List[str],
        start_date: str,
        end_date: str,
        output_dir: Path,
        data_type: str = "daily",
    ) -> Dict[str, Path]:
        """
        获取数据并按股票分别保存到 CSV 文件

        Args:
            ts_codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            output_dir: 输出目录
            data_type: 数据类型，可选 'daily'（行情）或 'daily_basic'（估值指标）

        Returns:
            字典，键为股票代码，值为保存的文件路径
        """
        if data_type == "daily":
            df = self.fetch_daily_by_query(ts_codes, start_date, end_date)
        elif data_type == "daily_basic":
            df = self.fetch_daily_basic(ts_codes, start_date, end_date)
        else:
            raise ValueError(f"不支持的数据类型: {data_type}")

        if df.empty:
            return {}

        saved_files = save_to_csv_by_stock(
            df=df,
            output_dir=output_dir,
            code_column="ts_code",
            date_column="trade_date",
            start_date=start_date,
            end_date=end_date,
        )

        return saved_files


if __name__ == "__main__":
    fetcher = TushareDataFetcher()
    csv_dir = Path(__file__).parent / "csv"
    makedirs(csv_dir, exist_ok=True)

    ts_codes = ["000001.SZ", "600000.SH"]
    start_date = "20180701"
    end_date = "20180718"

    print("=" * 60)
    print("获取日线行情数据并按股票分别保存")
    print("=" * 60)

    saved_files = fetcher.fetch_and_save_by_stock(
        ts_codes=ts_codes,
        start_date=start_date,
        end_date=end_date,
        output_dir=csv_dir,
        data_type="daily",
    )

    print(f"\n已保存的文件:")
    for code, file_path in saved_files.items():
        print(f"  {code}: {file_path}")

    print("\n" + "=" * 60)
    print("获取估值指标数据（PE、PB 等）并按股票分别保存")
    print("=" * 60)

    try:
        valuation_files = fetcher.fetch_and_save_by_stock(
            ts_codes=ts_codes,
            start_date=start_date,
            end_date=end_date,
            output_dir=csv_dir,
            data_type="daily_basic",
        )

        print(f"\n已保存的估值数据文件:")
        for code, file_path in valuation_files.items():
            print(f"  {code}: {file_path}")
    except Exception as e:
        print(f"获取估值数据时出错（可能需要更高积分权限）: {e}")

    print("\n" + "=" * 60)
    print("示例：使用旧方式保存为单一文件（向后兼容）")
    print("=" * 60)

    df_query = fetcher.fetch_daily_by_query(
        ts_codes=ts_codes,
        start_date=start_date,
        end_date=end_date,
    )

    codes = "_".join(c.replace(".", "_") for c in ts_codes)
    single_file = csv_dir / f"combined_{codes}_{start_date}_{end_date}.csv"
    save_to_csv(df_query, single_file)
    print(f"\n合并文件已保存: {single_file}")
