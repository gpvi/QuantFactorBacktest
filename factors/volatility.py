"""
波动率因子模块
包含历史波动率、滚动波动率、ATR（真实波动幅度）等波动率因子的计算
"""

from typing import Optional, Dict, Any, List, Union, Tuple
import pandas as pd
import polars as pl
import numpy as np

from .base import Factor
from models.stock_matrix import StockMatrix


class VolatilityFactor(Factor):
    """
    波动率因子基类
    提供各种波动率计算的通用方法
    """

    factor_type: str = "volatility"
    factor_name: str = "Volatility"

    def __init__(
        self,
        name: Optional[str] = None,
        window: int = 20,
        annualized: bool = True,
        **kwargs,
    ):
        """
        初始化波动率因子

        Args:
            name: 因子名称
            window: 计算窗口（交易日数），默认 20 个交易日（约 1 个月）
            annualized: 是否年化，默认 True
            **kwargs: 其他参数
        """
        super().__init__(name=name, **kwargs)
        self.window = window
        self.annualized = annualized
        self._annualization_factor = np.sqrt(252)

    @staticmethod
    def calculate_returns(
        prices: Union[pd.DataFrame, np.ndarray],
        method: str = "log",
    ) -> Union[pd.DataFrame, np.ndarray]:
        """
        计算收益率

        Args:
            prices: 价格数据
            method: 计算方法，'log' 为对数收益率，'simple' 为简单收益率

        Returns:
            收益率数据
        """
        if isinstance(prices, pd.DataFrame):
            if method == "log":
                returns = np.log(prices / prices.shift(1))
            else:
                returns = prices.pct_change()
            return returns
        elif isinstance(prices, np.ndarray):
            if method == "log":
                returns = np.log(prices[1:] / prices[:-1])
            else:
                returns = (prices[1:] - prices[:-1]) / prices[:-1]
            return returns
        else:
            raise TypeError(f"不支持的数据类型: {type(prices)}")

    def calculate_historical_volatility(
        self,
        prices: Union[pd.DataFrame, np.ndarray],
        window: Optional[int] = None,
        method: str = "log",
    ) -> Union[pd.DataFrame, np.ndarray]:
        """
        计算历史波动率
        历史波动率 = 收益率的滚动标准差 × 年化因子

        Args:
            prices: 价格数据
            window: 计算窗口，如未指定则使用初始化时的窗口
            method: 收益率计算方法，'log' 或 'simple'

        Returns:
            历史波动率数据
        """
        if window is None:
            window = self.window

        returns = self.calculate_returns(prices, method)

        if isinstance(returns, pd.DataFrame):
            volatility = returns.rolling(window=window).std(ddof=1)
            if self.annualized:
                volatility = volatility * self._annualization_factor
            return volatility
        elif isinstance(returns, np.ndarray):
            volatility = np.full_like(returns, np.nan)
            for i in range(window, len(returns)):
                volatility[i] = np.nanstd(returns[i - window + 1 : i + 1], ddof=1)
            if self.annualized:
                volatility = volatility * self._annualization_factor
            return volatility
        else:
            raise TypeError(f"不支持的数据类型: {type(returns)}")

    def calculate(
        self,
        data: StockMatrix,
        price_column: str = "close",
        **kwargs,
    ) -> pd.DataFrame:
        """
        计算波动率因子值（使用收盘价）

        Args:
            data: 股票矩阵数据
            price_column: 价格列名，默认 'close'
            **kwargs: 额外参数

        Returns:
            波动率因子值的透视表（时间×股票）
        """
        if price_column not in data.indicators:
            available = data.indicators
            raise ValueError(
                f"数据中未找到价格列 '{price_column}'。"
                f"可用的指标列: {available}"
            )

        price_pivot = data.get_pivot(price_column)

        volatility = self.calculate_historical_volatility(price_pivot)

        self._save_result(
            volatility,
            metadata={
                "window": self.window,
                "annualized": self.annualized,
                "price_column": price_column,
                "n_dates": len(volatility),
                "n_stocks": len(volatility.columns),
            },
        )

        return volatility


class RollingVolatilityFactor(VolatilityFactor):
    """
    滚动波动率因子
    计算不同窗口的滚动波动率
    """

    factor_type: str = "volatility"
    factor_name: str = "RollingVolatility"

    def __init__(
        self,
        name: Optional[str] = None,
        windows: List[int] = None,
        annualized: bool = True,
        **kwargs,
    ):
        """
        初始化滚动波动率因子

        Args:
            name: 因子名称
            windows: 窗口列表，默认 [5, 10, 20, 60]
            annualized: 是否年化
            **kwargs: 其他参数
        """
        if windows is None:
            windows = [5, 10, 20, 60]
        super().__init__(name=name, window=windows[0], annualized=annualized, **kwargs)
        self.windows = windows

    def calculate(
        self,
        data: StockMatrix,
        price_column: str = "close",
        method: str = "log",
        **kwargs,
    ) -> Dict[int, pd.DataFrame]:
        """
        计算多窗口滚动波动率

        Args:
            data: 股票矩阵数据
            price_column: 价格列名
            method: 收益率计算方法
            **kwargs: 额外参数

        Returns:
            字典，键为窗口大小，值为对应波动率的 DataFrame
        """
        if price_column not in data.indicators:
            available = data.indicators
            raise ValueError(
                f"数据中未找到价格列 '{price_column}'。"
                f"可用的指标列: {available}"
            )

        price_pivot = data.get_pivot(price_column)
        returns = self.calculate_returns(price_pivot, method)

        results = {}
        for window in self.windows:
            volatility = returns.rolling(window=window).std(ddof=1)
            if self.annualized:
                volatility = volatility * self._annualization_factor
            results[window] = volatility

        self._save_result(
            results,
            metadata={
                "windows": self.windows,
                "annualized": self.annualized,
                "method": method,
                "price_column": price_column,
            },
        )

        return results


class ATRFactor(VolatilityFactor):
    """
    真实波动幅度（ATR）因子
    ATR 是衡量市场波动性的指标，考虑了跳空缺口

    真实波幅 TR = max(High - Low, abs(High - Close_prev), abs(Low - Close_prev))
    ATR = TR 的移动平均
    """

    factor_type: str = "volatility"
    factor_name: str = "ATR"

    def __init__(
        self,
        name: Optional[str] = None,
        window: int = 14,
        method: str = "ma",
        **kwargs,
    ):
        """
        初始化 ATR 因子

        Args:
            name: 因子名称
            window: 计算窗口，默认 14 个交易日
            method: 平均方法，'ma' 为简单移动平均，'ema' 为指数移动平均
            **kwargs: 其他参数
        """
        super().__init__(name=name, window=window, annualized=False, **kwargs)
        self.method = method

    @staticmethod
    def calculate_tr(
        high: Union[pd.DataFrame, np.ndarray],
        low: Union[pd.DataFrame, np.ndarray],
        close: Union[pd.DataFrame, np.ndarray],
    ) -> Union[pd.DataFrame, np.ndarray]:
        """
        计算真实波幅（True Range）

        TR = max(High - Low, abs(High - Close_prev), abs(Low - Close_prev))

        Args:
            high: 最高价数据
            low: 最低价数据
            close: 收盘价数据

        Returns:
            真实波幅数据
        """
        if isinstance(high, pd.DataFrame):
            close_prev = close.shift(1)
            tr1 = high - low
            tr2 = (high - close_prev).abs()
            tr3 = (low - close_prev).abs()
            tr = pd.DataFrame(
                np.maximum(np.maximum(tr1.values, tr2.values), tr3.values),
                index=high.index,
                columns=high.columns,
            )
            return tr
        elif isinstance(high, np.ndarray):
            close_prev = np.roll(close, 1, axis=0)
            close_prev[0] = np.nan
            tr1 = high - low
            tr2 = np.abs(high - close_prev)
            tr3 = np.abs(low - close_prev)
            tr = np.maximum(np.maximum(tr1, tr2), tr3)
            return tr
        else:
            raise TypeError(f"不支持的数据类型: {type(high)}")

    def calculate_atr(
        self,
        tr: Union[pd.DataFrame, np.ndarray],
        window: Optional[int] = None,
        method: Optional[str] = None,
    ) -> Union[pd.DataFrame, np.ndarray]:
        """
        计算平均真实波幅（ATR）

        Args:
            tr: 真实波幅数据
            window: 计算窗口
            method: 平均方法

        Returns:
            ATR 数据
        """
        if window is None:
            window = self.window
        if method is None:
            method = self.method

        if isinstance(tr, pd.DataFrame):
            if method == "ma":
                atr = tr.rolling(window=window).mean()
            elif method == "ema":
                atr = tr.ewm(span=window, adjust=False).mean()
            else:
                raise ValueError(f"不支持的平均方法: {method}")
            return atr
        elif isinstance(tr, np.ndarray):
            atr = np.full_like(tr, np.nan)
            if method == "ma":
                for i in range(window, len(tr)):
                    atr[i] = np.nanmean(tr[i - window + 1 : i + 1])
            elif method == "ema":
                alpha = 2 / (window + 1)
                for i in range(window, len(tr)):
                    if i == window:
                        atr[i] = np.nanmean(tr[i - window + 1 : i + 1])
                    else:
                        atr[i] = alpha * tr[i] + (1 - alpha) * atr[i - 1]
            else:
                raise ValueError(f"不支持的平均方法: {method}")
            return atr
        else:
            raise TypeError(f"不支持的数据类型: {type(tr)}")

    def calculate(
        self,
        data: StockMatrix,
        high_column: str = "high",
        low_column: str = "low",
        close_column: str = "close",
        **kwargs,
    ) -> pd.DataFrame:
        """
        计算 ATR 因子值

        Args:
            data: 股票矩阵数据
            high_column: 最高价列名
            low_column: 最低价列名
            close_column: 收盘价列名
            **kwargs: 额外参数

        Returns:
            ATR 因子值的透视表（时间×股票）
        """
        required_cols = [high_column, low_column, close_column]
        for col in required_cols:
            if col not in data.indicators:
                available = data.indicators
                raise ValueError(
                    f"数据中未找到列 '{col}'。"
                    f"可用的指标列: {available}"
                )

        high_pivot = data.get_pivot(high_column)
        low_pivot = data.get_pivot(low_column)
        close_pivot = data.get_pivot(close_column)

        tr = self.calculate_tr(high_pivot, low_pivot, close_pivot)

        atr = self.calculate_atr(tr)

        self._save_result(
            atr,
            metadata={
                "window": self.window,
                "method": self.method,
                "high_column": high_column,
                "low_column": low_column,
                "close_column": close_column,
                "n_dates": len(atr),
                "n_stocks": len(atr.columns),
            },
        )

        return atr


class IntraDayVolatilityFactor(VolatilityFactor):
    """
    日内波动率因子
    衡量日内价格波动程度
    """

    factor_type: str = "volatility"
    factor_name: str = "IntraDayVolatility"

    def __init__(
        self,
        name: Optional[str] = None,
        method: str = "range",
        **kwargs,
    ):
        """
        初始化日内波动率因子

        Args:
            name: 因子名称
            method: 计算方法：
                - 'range': (High - Low) / Close
                - 'parkinson': 使用 Parkinson 波动率估计
                - 'garman_klass': 使用 Garman-Klass 波动率估计
            **kwargs: 其他参数
        """
        super().__init__(name=name, window=1, annualized=False, **kwargs)
        self.method = method

    def calculate(
        self,
        data: StockMatrix,
        open_column: str = "open",
        high_column: str = "high",
        low_column: str = "low",
        close_column: str = "close",
        **kwargs,
    ) -> pd.DataFrame:
        """
        计算日内波动率

        Args:
            data: 股票矩阵数据
            open_column: 开盘价列名
            high_column: 最高价列名
            low_column: 最低价列名
            close_column: 收盘价列名
            **kwargs: 额外参数

        Returns:
            日内波动率因子值的透视表
        """
        open_pivot = data.get_pivot(open_column)
        high_pivot = data.get_pivot(high_column)
        low_pivot = data.get_pivot(low_column)
        close_pivot = data.get_pivot(close_column)

        if self.method == "range":
            volatility = (high_pivot - low_pivot) / close_pivot
        elif self.method == "parkinson":
            volatility = np.sqrt(
                (1 / (4 * np.log(2)))
                * np.square(np.log(high_pivot / low_pivot))
            )
        elif self.method == "garman_klass":
            term1 = 0.5 * np.square(np.log(high_pivot / low_pivot))
            term2 = (2 * np.log(2) - 1) * np.square(np.log(close_pivot / open_pivot))
            volatility = np.sqrt(term1 - term2)
        else:
            raise ValueError(f"不支持的计算方法: {self.method}")

        self._save_result(
            volatility,
            metadata={
                "method": self.method,
                "n_dates": len(volatility),
                "n_stocks": len(volatility.columns),
            },
        )

        return volatility


class VolatilityChangeFactor(VolatilityFactor):
    """
    波动率变化因子
    衡量波动率的变化（如波动率扩张/收缩）
    """

    factor_type: str = "volatility"
    factor_name: str = "VolatilityChange"

    def __init__(
        self,
        name: Optional[str] = None,
        short_window: int = 5,
        long_window: int = 20,
        **kwargs,
    ):
        """
        初始化波动率变化因子

        Args:
            name: 因子名称
            short_window: 短期窗口
            long_window: 长期窗口
            **kwargs: 其他参数
        """
        super().__init__(name=name, window=short_window, **kwargs)
        self.short_window = short_window
        self.long_window = long_window

    def calculate(
        self,
        data: StockMatrix,
        price_column: str = "close",
        method: str = "ratio",
        **kwargs,
    ) -> pd.DataFrame:
        """
        计算波动率变化

        Args:
            data: 股票矩阵数据
            price_column: 价格列名
            method: 计算方法：
                - 'ratio': 短期波动率 / 长期波动率
                - 'diff': 短期波动率 - 长期波动率
            **kwargs: 额外参数

        Returns:
            波动率变化因子值的透视表
        """
        if price_column not in data.indicators:
            available = data.indicators
            raise ValueError(
                f"数据中未找到价格列 '{price_column}'。"
                f"可用的指标列: {available}"
            )

        price_pivot = data.get_pivot(price_column)
        returns = self.calculate_returns(price_pivot)

        short_vol = returns.rolling(window=self.short_window).std(ddof=1)
        long_vol = returns.rolling(window=self.long_window).std(ddof=1)

        if self.annualized:
            short_vol = short_vol * self._annualization_factor
            long_vol = long_vol * self._annualization_factor

        if method == "ratio":
            vol_change = short_vol / long_vol.replace(0, np.nan)
        elif method == "diff":
            vol_change = short_vol - long_vol
        else:
            raise ValueError(f"不支持的计算方法: {method}")

        self._save_result(
            vol_change,
            metadata={
                "short_window": self.short_window,
                "long_window": self.long_window,
                "method": method,
                "annualized": self.annualized,
                "price_column": price_column,
            },
        )

        return vol_change
