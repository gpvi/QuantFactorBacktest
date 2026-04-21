"""
CSV 数据加载模块
支持从单文件和多文件（每只股票一个文件）加载数据
"""

from pathlib import Path
from typing import List, Optional, Dict, Union, Tuple
import pandas as pd
import polars as pl
import re

DATA_DIR = Path(__file__).parent / "csv"


def load_daily(
    file_name: str = None,
    codes: list[str] = None,
    start_date: str = None,
    end_date: str = None,
    data_dir: Path = None,
) -> pl.DataFrame:
    """
    加载日线数据（向后兼容旧的单文件方式）

    Args:
        file_name: 单一文件名
        codes: 股票代码列表
        start_date: 开始日期
        end_date: 结束日期
        data_dir: 数据目录

    Returns:
        polars DataFrame
    """
    if data_dir is None:
        data_dir = DATA_DIR

    if file_name:
        path = data_dir / file_name
        return pl.read_csv(path, try_parse_dates=True)
    elif codes and start_date and end_date:
        return load_daily_by_stocks(
            codes=codes,
            start_date=start_date,
            end_date=end_date,
            data_dir=data_dir,
        )
    else:
        raise ValueError("需要 file_name 或 codes+start_date+end_date")


def load_daily_by_stock(
    code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    data_dir: Path = None,
) -> pl.DataFrame:
    """
    加载单只股票的日线数据

    文件命名格式: {code}_{start_date}_{end_date}.csv
    例如: 000001_SZ_20180701_20180718.csv

    Args:
        code: 股票代码（如 '000001.SZ' 或 '000001_SZ'）
        start_date: 开始日期（用于匹配文件名）
        end_date: 结束日期（用于匹配文件名）
        data_dir: 数据目录

    Returns:
        polars DataFrame
    """
    if data_dir is None:
        data_dir = DATA_DIR

    safe_code = code.replace(".", "_")

    if start_date and end_date:
        file_name = f"{safe_code}_{start_date}_{end_date}.csv"
        path = data_dir / file_name
        if path.exists():
            df = pl.read_csv(path, try_parse_dates=True)
            return df
        else:
            raise FileNotFoundError(f"文件不存在: {path}")
    else:
        pattern = rf"^{re.escape(safe_code)}_\d{{8}}_\d{{8}}\.csv$"
        matching_files = [f for f in data_dir.glob("*.csv") if re.match(pattern, f.name)]

        if not matching_files:
            raise FileNotFoundError(f"未找到股票 {code} 的数据文件")

        all_dfs = []
        for file_path in matching_files:
            df = pl.read_csv(file_path, try_parse_dates=True)
            all_dfs.append(df)

        if len(all_dfs) == 1:
            return all_dfs[0]
        else:
            return pl.concat(all_dfs).unique().sort("trade_date")


def load_daily_by_stocks(
    codes: List[str],
    start_date: str,
    end_date: str,
    data_dir: Path = None,
) -> pl.DataFrame:
    """
    加载多只股票的日线数据并合并

    Args:
        codes: 股票代码列表
        start_date: 开始日期
        end_date: 结束日期
        data_dir: 数据目录

    Returns:
        合并后的 polars DataFrame
    """
    if data_dir is None:
        data_dir = DATA_DIR

    all_dfs = []
    for code in codes:
        try:
            df = load_daily_by_stock(
                code=code,
                start_date=start_date,
                end_date=end_date,
                data_dir=data_dir,
            )
            all_dfs.append(df)
        except FileNotFoundError as e:
            print(f"警告: {e}")
            continue

    if not all_dfs:
        raise FileNotFoundError("未找到任何股票的数据文件")

    return pl.concat(all_dfs)


def load_valuation_data(
    codes: List[str],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    data_dir: Path = None,
) -> pl.DataFrame:
    """
    加载估值数据（PE、PB 等）

    文件命名格式: valuation_{code}_{start_date}_{end_date}.csv

    Args:
        codes: 股票代码列表
        start_date: 开始日期
        end_date: 结束日期
        data_dir: 数据目录

    Returns:
        合并后的 polars DataFrame
    """
    if data_dir is None:
        data_dir = DATA_DIR

    all_dfs = []
    for code in codes:
        safe_code = code.replace(".", "_")

        if start_date and end_date:
            file_name = f"valuation_{safe_code}_{start_date}_{end_date}.csv"
            path = data_dir / file_name
            if path.exists():
                df = pl.read_csv(path, try_parse_dates=True)
                all_dfs.append(df)
            else:
                print(f"警告: 文件不存在 {path}")
        else:
            pattern = rf"^valuation_{re.escape(safe_code)}_\d{{8}}_\d{{8}}\.csv$"
            matching_files = [f for f in data_dir.glob("*.csv") if re.match(pattern, f.name)]
            for file_path in matching_files:
                df = pl.read_csv(file_path, try_parse_dates=True)
                all_dfs.append(df)

    if not all_dfs:
        raise FileNotFoundError("未找到任何估值数据文件")

    return pl.concat(all_dfs).unique()


def load_financial_data(
    codes: List[str],
    data_dir: Path = None,
) -> pl.DataFrame:
    """
    加载财务数据

    文件命名格式: finance_{code}_{start_date}_{end_date}.csv

    Args:
        codes: 股票代码列表
        data_dir: 数据目录

    Returns:
        合并后的 polars DataFrame
    """
    if data_dir is None:
        data_dir = DATA_DIR

    all_dfs = []
    for code in codes:
        safe_code = code.replace(".", "_")
        pattern = rf"^finance_{re.escape(safe_code)}_\d{{8}}_\d{{8}}\.csv$"
        matching_files = [f for f in data_dir.glob("*.csv") if re.match(pattern, f.name)]

        for file_path in matching_files:
            df = pl.read_csv(file_path, try_parse_dates=True)
            all_dfs.append(df)

    if not all_dfs:
        raise FileNotFoundError("未找到任何财务数据文件")

    return pl.concat(all_dfs).unique()


def list_available_stocks(
    data_dir: Path = None,
    data_type: str = "daily",
) -> Dict[str, List[Tuple[str, str]]]:
    """
    列出数据目录中可用的股票及其日期范围

    Args:
        data_dir: 数据目录
        data_type: 数据类型，'daily'、'valuation' 或 'finance'

    Returns:
        字典，键为股票代码，值为 (start_date, end_date) 元组列表
    """
    if data_dir is None:
        data_dir = DATA_DIR

    stock_info = {}

    if data_type == "daily":
        pattern = r"^(\d{6}_[A-Z]{2})_(\d{8})_(\d{8})\.csv$"
    elif data_type == "valuation":
        pattern = r"^valuation_(\d{6}_[A-Z]{2})_(\d{8})_(\d{8})\.csv$"
    elif data_type == "finance":
        pattern = r"^finance_(\d{6}_[A-Z]{2})_(\d{8})_(\d{8})\.csv$"
    else:
        raise ValueError(f"不支持的数据类型: {data_type}")

    for file_path in data_dir.glob("*.csv"):
        match = re.match(pattern, file_path.name)
        if match:
            safe_code = match.group(1)
            start_date = match.group(2)
            end_date = match.group(3)

            code = safe_code.replace("_", ".")
            if code not in stock_info:
                stock_info[code] = []
            stock_info[code].append((start_date, end_date))

    return stock_info


if __name__ == "__main__":
    print("=" * 60)
    print("数据加载模块测试")
    print("=" * 60)

    print("\n--- 列出可用的股票 ---")
    try:
        available_stocks = list_available_stocks(data_type="daily")
        if available_stocks:
            for code, date_ranges in available_stocks.items():
                print(f"  {code}:")
                for start, end in date_ranges:
                    print(f"    {start} 至 {end}")
        else:
            print("  未找到数据文件")
    except Exception as e:
        print(f"  出错: {e}")

    print("\n--- 测试加载单只股票数据 ---")
    try:
        df = load_daily_by_stock(
            code="000001.SZ",
            start_date="20180701",
            end_date="20180718",
        )
        print(f"  数据形状: {df.shape}")
        print(f"  前5行:")
        print(df.head())
    except Exception as e:
        print(f"  出错: {e}")

    print("\n--- 测试加载多只股票数据 ---")
    try:
        df = load_daily_by_stocks(
            codes=["000001.SZ", "600000.SH"],
            start_date="20180701",
            end_date="20180718",
        )
        print(f"  合并后数据形状: {df.shape}")
        print(f"  包含的股票代码: {df['ts_code'].unique().to_list()}")
    except Exception as e:
        print(f"  出错: {e}")
