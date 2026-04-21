"""
CSV 保存模块
支持单文件保存和按股票分别保存
"""

from pathlib import Path
from typing import Dict, List, Optional, Union
import pandas as pd
import polars as pl


def save_to_csv(df: Union[pd.DataFrame, pl.DataFrame], file_path: Union[str, Path], index: bool = False) -> Path:
    """
    将 DataFrame 保存到 CSV 文件

    Args:
        df: 要保存的数据（pandas 或 polars DataFrame）
        file_path: 文件路径
        index: 是否保存索引

    Returns:
        保存的文件路径
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(df, pd.DataFrame):
        df.to_csv(file_path, index=index)
    elif isinstance(df, pl.DataFrame):
        df.write_csv(file_path)
    else:
        raise TypeError(f"不支持的数据类型: {type(df)}")

    return file_path


def save_to_csv_by_stock(
    df: Union[pd.DataFrame, pl.DataFrame],
    output_dir: Union[str, Path],
    code_column: str = "ts_code",
    date_column: str = "trade_date",
    file_prefix: str = "daily",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Path]:
    """
    按股票代码分别保存到 CSV 文件，每只股票一个文件

    文件命名格式: {code}_{date_range}.csv
    例如: 000001.SZ_20180701_20180718.csv

    Args:
        df: 包含多只股票数据的 DataFrame
        output_dir: 输出目录
        code_column: 股票代码列名，默认 'ts_code'
        date_column: 日期列名，默认 'trade_date'
        file_prefix: 文件名前缀，默认 'daily'
        start_date: 开始日期（用于文件名），如未指定则从数据中推断
        end_date: 结束日期（用于文件名），如未指定则从数据中推断

    Returns:
        字典，键为股票代码，值为保存的文件路径
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if isinstance(df, pl.DataFrame):
        df_pd = df.to_pandas()
    else:
        df_pd = df

    if code_column not in df_pd.columns:
        raise ValueError(f"数据中未找到股票代码列: {code_column}")

    if date_column not in df_pd.columns:
        raise ValueError(f"数据中未找到日期列: {date_column}")

    unique_codes = df_pd[code_column].unique()

    if start_date is None or end_date is None:
        sorted_dates = sorted(df_pd[date_column].astype(str).unique())
        if start_date is None:
            start_date = sorted_dates[0]
        if end_date is None:
            end_date = sorted_dates[-1]

    saved_files = {}

    for code in unique_codes:
        stock_df = df_pd[df_pd[code_column] == code].sort_values(by=date_column)

        safe_code = code.replace(".", "_")
        file_name = f"{safe_code}_{start_date}_{end_date}.csv"
        file_path = output_dir / file_name

        stock_df.to_csv(file_path, index=False)
        saved_files[code] = file_path

    return saved_files


def save_stock_matrix_by_stock(
    df: Union[pd.DataFrame, pl.DataFrame],
    output_dir: Union[str, Path],
    code_column: str = "ts_code",
    date_column: str = "trade_date",
    data_type: str = "daily",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Path]:
    """
    保存股票矩阵数据，每只股票一个文件

    Args:
        df: 包含多只股票数据的 DataFrame
        output_dir: 输出目录
        code_column: 股票代码列名
        date_column: 日期列名
        data_type: 数据类型，如 'daily'、'finance'、'valuation' 等
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        字典，键为股票代码，值为保存的文件路径
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if isinstance(df, pl.DataFrame):
        df_pd = df.to_pandas()
    else:
        df_pd = df

    if code_column not in df_pd.columns:
        raise ValueError(f"数据中未找到股票代码列: {code_column}")

    if date_column not in df_pd.columns:
        raise ValueError(f"数据中未找到日期列: {date_column}")

    unique_codes = df_pd[code_column].unique()

    if start_date is None or end_date is None:
        sorted_dates = sorted(df_pd[date_column].astype(str).unique())
        if start_date is None:
            start_date = sorted_dates[0]
        if end_date is None:
            end_date = sorted_dates[-1]

    saved_files = {}

    for code in unique_codes:
        stock_df = df_pd[df_pd[code_column] == code].sort_values(by=date_column)

        safe_code = code.replace(".", "_")
        file_name = f"{data_type}_{safe_code}_{start_date}_{end_date}.csv"
        file_path = output_dir / file_name

        stock_df.to_csv(file_path, index=False)
        saved_files[code] = file_path

    return saved_files


def save_valuation_data(
    df: Union[pd.DataFrame, pl.DataFrame],
    output_dir: Union[str, Path],
    code_column: str = "ts_code",
    date_column: str = "trade_date",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Path]:
    """
    保存估值数据（PE、PB 等），每只股票一个文件

    Args:
        df: 包含估值数据的 DataFrame
        output_dir: 输出目录
        code_column: 股票代码列名
        date_column: 日期列名
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        字典，键为股票代码，值为保存的文件路径
    """
    return save_stock_matrix_by_stock(
        df=df,
        output_dir=output_dir,
        code_column=code_column,
        date_column=date_column,
        data_type="valuation",
        start_date=start_date,
        end_date=end_date,
    )


def save_financial_data(
    df: Union[pd.DataFrame, pl.DataFrame],
    output_dir: Union[str, Path],
    code_column: str = "ts_code",
    date_column: str = "end_date",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Path]:
    """
    保存财务数据，每只股票一个文件

    Args:
        df: 包含财务数据的 DataFrame
        output_dir: 输出目录
        code_column: 股票代码列名
        date_column: 日期列名（财务数据通常用 end_date）
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        字典，键为股票代码，值为保存的文件路径
    """
    return save_stock_matrix_by_stock(
        df=df,
        output_dir=output_dir,
        code_column=code_column,
        date_column=date_column,
        data_type="finance",
        start_date=start_date,
        end_date=end_date,
    )
