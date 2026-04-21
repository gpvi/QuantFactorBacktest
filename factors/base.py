"""
因子基类
定义因子计算的基本接口和通用方法
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, Union
import pandas as pd
import polars as pl
import numpy as np

from models.stock_matrix import StockMatrix


class Factor(ABC):
    """
    因子基类
    所有具体因子都应该继承此类并实现 calculate 方法
    """

    factor_type: str = "base"
    factor_name: str = "BaseFactor"

    def __init__(self, name: Optional[str] = None, **kwargs):
        """
        初始化因子

        Args:
            name: 因子名称，默认使用类名
            **kwargs: 其他参数
        """
        self.name = name or self.factor_name
        self._params = kwargs
        self._result: Optional[Union[pd.DataFrame, pl.DataFrame, StockMatrix]] = None
        self._metadata: Dict[str, Any] = {}

    @abstractmethod
    def calculate(self, data: StockMatrix, **kwargs) -> Any:
        """
        抽象方法：计算因子值
        所有子类必须实现此方法

        Args:
            data: 股票矩阵数据
            **kwargs: 额外参数

        Returns:
            因子计算结果
        """
        pass

    def __call__(self, data: StockMatrix, **kwargs) -> Any:
        """
        使因子对象可调用

        Args:
            data: 股票矩阵数据
            **kwargs: 额外参数

        Returns:
            因子计算结果
        """
        return self.calculate(data, **kwargs)

    @property
    def result(self) -> Optional[Any]:
        """
        获取计算结果
        """
        return self._result

    @property
    def metadata(self) -> Dict[str, Any]:
        """
        获取元数据
        """
        return self._metadata

    def _save_result(self, result: Any, metadata: Optional[Dict[str, Any]] = None):
        """
        保存计算结果和元数据

        Args:
            result: 计算结果
            metadata: 元数据
        """
        self._result = result
        if metadata:
            self._metadata.update(metadata)

    def get_params(self) -> Dict[str, Any]:
        """
        获取因子参数

        Returns:
            参数字典
        """
        return self._params.copy()

    def set_params(self, **params):
        """
        设置因子参数

        Args:
            **params: 参数字典
        """
        self._params.update(params)

    def to_dataframe(self) -> pd.DataFrame:
        """
        将结果转换为 DataFrame

        Returns:
            pandas DataFrame
        """
        if self._result is None:
            raise ValueError("因子尚未计算，请先调用 calculate 方法")

        if isinstance(self._result, pd.DataFrame):
            return self._result
        elif isinstance(self._result, pl.DataFrame):
            return self._result.to_pandas()
        elif isinstance(self._result, StockMatrix):
            return self._result.to_pandas()
        elif isinstance(self._result, np.ndarray):
            return pd.DataFrame(self._result)
        else:
            raise TypeError(f"不支持的结果类型: {type(self._result)}")

    def winsorize(
        self,
        data: Union[pd.DataFrame, np.ndarray],
        lower: float = 0.01,
        upper: float = 0.99,
    ) -> Union[pd.DataFrame, np.ndarray]:
        """
        缩尾处理（去极值）

        Args:
            data: 数据
            lower: 下分位数，默认 0.01
            upper: 上分位数，默认 0.99

        Returns:
            缩尾处理后的数据
        """
        if isinstance(data, pd.DataFrame):
            lower_bound = data.quantile(lower)
            upper_bound = data.quantile(upper)
            return data.clip(lower=lower_bound, upper=upper_bound, axis=1)
        elif isinstance(data, np.ndarray):
            lower_bound = np.nanquantile(data, lower)
            upper_bound = np.nanquantile(data, upper)
            return np.clip(data, lower_bound, upper_bound)
        else:
            raise TypeError(f"不支持的数据类型: {type(data)}")

    def standardize(
        self,
        data: Union[pd.DataFrame, np.ndarray],
    ) -> Union[pd.DataFrame, np.ndarray]:
        """
        标准化处理（Z-score）

        Args:
            data: 数据

        Returns:
            标准化后的数据
        """
        if isinstance(data, pd.DataFrame):
            mean = data.mean(axis=1)
            std = data.std(axis=1)
            return data.sub(mean, axis=0).div(std, axis=0)
        elif isinstance(data, np.ndarray):
            mean = np.nanmean(data, axis=1, keepdims=True)
            std = np.nanstd(data, axis=1, keepdims=True)
            return (data - mean) / std
        else:
            raise TypeError(f"不支持的数据类型: {type(data)}")

    def neutralize(
        self,
        data: Union[pd.DataFrame, np.ndarray],
        neutralize_data: Union[pd.DataFrame, np.ndarray],
    ) -> Union[pd.DataFrame, np.ndarray]:
        """
        中性化处理

        Args:
            data: 因子数据
            neutralize_data: 用于中性化的数据（如市值、行业等）

        Returns:
            中性化后的数据
        """
        try:
            from sklearn.linear_model import LinearRegression
        except ImportError:
            raise ImportError("中性化需要 scikit-learn 库，请安装: pip install scikit-learn")

        if isinstance(data, pd.DataFrame):
            result = data.copy()
            for col in data.columns:
                y = data[col].dropna()
                if len(y) > 0:
                    X = neutralize_data.loc[y.index]
                    model = LinearRegression()
                    model.fit(X, y)
                    residual = y - model.predict(X)
                    result.loc[residual.index, col] = residual
            return result
        elif isinstance(data, np.ndarray):
            result = data.copy()
            for i in range(data.shape[1]):
                y = data[:, i]
                valid_mask = ~np.isnan(y)
                if np.sum(valid_mask) > 0:
                    y_valid = y[valid_mask]
                    X_valid = neutralize_data[valid_mask]
                    model = LinearRegression()
                    model.fit(X_valid, y_valid)
                    residual = y_valid - model.predict(X_valid)
                    result[valid_mask, i] = residual
            return result
        else:
            raise TypeError(f"不支持的数据类型: {type(data)}")

    def __repr__(self) -> str:
        """
        字符串表示
        """
        return f"{self.__class__.__name__}(name='{self.name}')"
