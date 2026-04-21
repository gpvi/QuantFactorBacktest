"""
股票矩阵数据结构
用于存储和管理多只股票在时间序列上的多维数据
"""

from typing import List, Optional, Union, Dict, Any
import pandas as pd
import polars as pl
import numpy as np
from datetime import datetime


class StockMatrix:
    """
    股票矩阵类
    用于存储多只股票在多个时间点上的多维数据
    数据结构：时间×股票×指标
    """

    def __init__(
        self,
        data: Union[pd.DataFrame, pl.DataFrame, Dict],
        date_column: str = "trade_date",
        code_column: str = "ts_code",
    ):
        """
        初始化股票矩阵

        Args:
            data: 原始数据，可以是 DataFrame 或字典
            date_column: 日期列名，默认 "trade_date"
            code_column: 股票代码列名，默认 "ts_code"
        """
        self.date_column = date_column
        self.code_column = code_column

        if isinstance(data, pl.DataFrame):
            self._data = data
        elif isinstance(data, pd.DataFrame):
            self._data = self._safe_convert_pandas_to_polars(data)
        elif isinstance(data, dict):
            self._data = pl.DataFrame(data)
        else:
            raise TypeError(f"不支持的数据类型: {type(data)}")

        self._validate_structure()

    def _safe_convert_pandas_to_polars(self, df: pd.DataFrame) -> pl.DataFrame:
        """
        安全地将 pandas DataFrame 转换为 polars DataFrame
        不依赖 pyarrow 库

        Args:
            df: pandas DataFrame

        Returns:
            polars DataFrame
        """
        try:
            return pl.from_pandas(df)
        except ImportError:
            data_dict = {}
            for col in df.columns:
                series = df[col]
                if pd.api.types.is_numeric_dtype(series):
                    data_dict[col] = series.to_numpy()
                elif pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series):
                    data_dict[col] = series.astype(str).tolist()
                elif pd.api.types.is_datetime64_any_dtype(series):
                    data_dict[col] = series.dt.strftime("%Y%m%d").tolist()
                else:
                    data_dict[col] = series.tolist()
            return pl.DataFrame(data_dict)

    def _safe_polars_to_pandas(self, df: pl.DataFrame) -> pd.DataFrame:
        """
        安全地将 polars DataFrame 转换为 pandas DataFrame
        不依赖 pyarrow 库

        Args:
            df: polars DataFrame

        Returns:
            pandas DataFrame
        """
        try:
            return df.to_pandas()
        except (ImportError, ModuleNotFoundError):
            data_dict = {}
            for col in df.columns:
                series = df.get_column(col)
                if series.dtype in [pl.Float64, pl.Float32, pl.Int64, pl.Int32, pl.Int16, pl.Int8, pl.UInt64, pl.UInt32, pl.UInt16, pl.UInt8]:
                    data_dict[col] = series.to_numpy()
                elif series.dtype == pl.Boolean:
                    data_dict[col] = series.to_list()
                elif series.dtype == pl.Date or series.dtype == pl.Datetime:
                    data_dict[col] = series.to_list()
                else:
                    data_dict[col] = series.to_list()
            return pd.DataFrame(data_dict)

    def _validate_structure(self):
        """
        验证数据结构是否包含必要的列
        """
        required_cols = [self.date_column, self.code_column]
        missing_cols = [col for col in required_cols if col not in self._data.columns]
        if missing_cols:
            raise ValueError(f"数据缺少必要的列: {missing_cols}")

    @property
    def data(self) -> pl.DataFrame:
        """
        获取原始数据
        """
        return self._data

    @property
    def dates(self) -> List[datetime]:
        """
        获取所有唯一的日期列表
        """
        return (
            self._data.select(self.date_column)
            .unique()
            .sort(self.date_column)
            .to_series()
            .to_list()
        )

    @property
    def codes(self) -> List[str]:
        """
        获取所有唯一的股票代码列表
        """
        return (
            self._data.select(self.code_column)
            .unique()
            .sort(self.code_column)
            .to_series()
            .to_list()
        )

    @property
    def indicators(self) -> List[str]:
        """
        获取所有指标列名（排除日期和股票代码）
        """
        return [
            col
            for col in self._data.columns
            if col not in [self.date_column, self.code_column]
        ]

    def get_pivot(
        self,
        indicator: str,
        fill_value: Optional[Any] = None,
    ) -> pd.DataFrame:
        """
        获取指定指标的透视表（时间×股票）

        Args:
            indicator: 指标名称
            fill_value: 缺失值填充值

        Returns:
            透视表 DataFrame，索引为日期，列为股票代码
        """
        if indicator not in self.indicators:
            raise ValueError(f"指标不存在: {indicator}")

        pivot = (
            self._data.select([self.date_column, self.code_column, indicator])
            .pivot(
                index=self.date_column,
                columns=self.code_column,
                values=indicator,
            )
            .sort(self.date_column)
        )

        result = self._safe_polars_to_pandas(pivot).set_index(self.date_column)

        if fill_value is not None:
            result = result.fillna(fill_value)

        return result

    def get_matrix(self, indicator: str) -> np.ndarray:
        """
        获取指定指标的矩阵形式（时间×股票）

        Args:
            indicator: 指标名称

        Returns:
            numpy 矩阵，形状为 (时间点数, 股票数)
        """
        pivot = self.get_pivot(indicator)
        return pivot.values

    def filter_by_date(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> "StockMatrix":
        """
        按日期范围过滤数据

        Args:
            start_date: 开始日期 (YYYYMMDD 格式)
            end_date: 结束日期 (YYYYMMDD 格式)

        Returns:
            过滤后的 StockMatrix
        """
        filtered = self._data

        if start_date:
            filtered = filtered.filter(pl.col(self.date_column) >= start_date)
        if end_date:
            filtered = filtered.filter(pl.col(self.date_column) <= end_date)

        return StockMatrix(
            filtered,
            date_column=self.date_column,
            code_column=self.code_column,
        )

    def filter_by_codes(self, codes: List[str]) -> "StockMatrix":
        """
        按股票代码过滤数据

        Args:
            codes: 股票代码列表

        Returns:
            过滤后的 StockMatrix
        """
        filtered = self._data.filter(pl.col(self.code_column).is_in(codes))
        return StockMatrix(
            filtered,
            date_column=self.date_column,
            code_column=self.code_column,
        )

    def add_indicator(
        self,
        name: str,
        values: Union[pd.Series, pl.Series, np.ndarray, Dict],
    ) -> "StockMatrix":
        """
        添加新的指标列

        Args:
            name: 指标名称
            values: 指标值，可以是 Series、数组或字典

        Returns:
            更新后的 StockMatrix
        """
        if isinstance(values, dict):
            values_df = pl.DataFrame(
                {
                    self.date_column: list(values.keys()),
                    self.code_column: [k[1] if isinstance(k, tuple) else None for k in values.keys()],
                    name: list(values.values()),
                }
            )
            updated = self._data.join(
                values_df,
                on=[self.date_column, self.code_column],
                how="left",
            )
        elif isinstance(values, (pd.Series, pl.Series, np.ndarray)):
            if len(values) != len(self._data):
                raise ValueError(
                    f"值长度 ({len(values)}) 与数据长度 ({len(self._data)}) 不匹配"
                )
            updated = self._data.with_columns(pl.Series(name, values))
        else:
            raise TypeError(f"不支持的值类型: {type(values)}")

        return StockMatrix(
            updated,
            date_column=self.date_column,
            code_column=self.code_column,
        )

    def to_pandas(self) -> pd.DataFrame:
        """
        转换为 pandas DataFrame
        """
        return self._safe_polars_to_pandas(self._data)

    def to_polars(self) -> pl.DataFrame:
        """
        转换为 polars DataFrame
        """
        return self._data

    def __len__(self) -> int:
        """
        返回数据行数
        """
        return len(self._data)

    def __repr__(self) -> str:
        """
        字符串表示
        """
        return (
            f"StockMatrix("
            f"日期数={len(self.dates)}, "
            f"股票数={len(self.codes)}, "
            f"指标数={len(self.indicators)})"
        )
