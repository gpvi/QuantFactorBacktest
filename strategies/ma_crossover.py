"""
均线交叉策略模块
基于短期均线和长期均线交叉的经典技术分析策略
"""

from typing import Optional, Union
import pandas as pd
import numpy as np

from .base import Strategy
from .signal_matrix import SignalMatrix, SignalType
from models.stock_matrix import StockMatrix


class MACrossoverStrategy(Strategy):
    """
    均线交叉策略
    短期均线上穿长期均线时产生买入信号（金叉），下穿时产生卖出信号（死叉）

    核心逻辑：
    1. 计算短期均线和长期均线
    2. 检测金叉和死叉信号
    3. 金叉时买入，死叉时卖出
    """

    strategy_type: str = "ma_crossover"
    strategy_name: str = "MACrossoverStrategy"

    def __init__(
        self,
        name: Optional[str] = None,
        short_window: int = 5,
        long_window: int = 20,
        ma_type: str = "sma",
        **kwargs,
    ):
        """
        初始化均线交叉策略

        Args:
            name: 策略名称
            short_window: 短期均线窗口（交易日数），默认 5
            long_window: 长期均线窗口（交易日数），默认 20
            ma_type: 均线类型，'sma' 为简单均线，'ema' 为指数均线
            **kwargs: 其他参数
        """
        super().__init__(name=name, **kwargs)
        if short_window >= long_window:
            raise ValueError(f"短期窗口 ({short_window}) 必须小于长期窗口 ({long_window})")
        self.short_window = short_window
        self.long_window = long_window
        self.ma_type = ma_type

    def calculate_ma(
        self,
        prices: Union[pd.DataFrame, np.ndarray],
        window: int,
    ) -> Union[pd.DataFrame, np.ndarray]:
        """
        计算移动平均线

        Args:
            prices: 价格数据
            window: 均线窗口

        Returns:
            均线数据
        """
        if isinstance(prices, pd.DataFrame):
            if self.ma_type == "sma":
                return prices.rolling(window=window).mean()
            elif self.ma_type == "ema":
                return prices.ewm(span=window, adjust=False).mean()
            else:
                raise ValueError(f"不支持的均线类型: {self.ma_type}")
        elif isinstance(prices, np.ndarray):
            if self.ma_type == "sma":
                ma = np.full_like(prices, np.nan)
                for i in range(window - 1, len(prices)):
                    ma[i] = np.mean(prices[i - window + 1 : i + 1])
                return ma
            elif self.ma_type == "ema":
                ma = np.full_like(prices, np.nan)
                ma[0] = prices[0]
                alpha = 2.0 / (window + 1)
                for i in range(1, len(prices)):
                    ma[i] = alpha * prices[i] + (1 - alpha) * ma[i - 1]
                return ma
            else:
                raise ValueError(f"不支持的均线类型: {self.ma_type}")
        else:
            raise TypeError(f"不支持的数据类型: {type(prices)}")

    def _detect_crossovers(
        self,
        short_ma: pd.DataFrame,
        long_ma: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        检测均线交叉信号

        Args:
            short_ma: 短期均线 DataFrame
            long_ma: 长期均线 DataFrame

        Returns:
            信号 DataFrame，1 表示金叉（买入），-1 表示死叉（卖出），NaN 表示无信号
        """
        diff = short_ma - long_ma
        prev_diff = diff.shift(1)

        signals = pd.DataFrame(np.nan, index=short_ma.index, columns=short_ma.columns)

        golden_cross = (diff > 0) & (prev_diff <= 0)
        death_cross = (diff < 0) & (prev_diff >= 0)

        signals[golden_cross] = SignalType.BUY.value
        signals[death_cross] = SignalType.SELL.value

        return signals

    def generate_signals(
        self,
        data: StockMatrix,
        price_column: str = "close",
        **kwargs,
    ) -> SignalMatrix:
        """
        生成均线交叉策略交易信号

        Args:
            data: 股票矩阵数据
            price_column: 价格列名，默认 'close'
            **kwargs: 额外参数

        Returns:
            信号矩阵对象
        """
        if price_column not in data.indicators:
            available = data.indicators
            raise ValueError(
                f"数据中未找到价格列 '{price_column}'。"
                f"可用的指标列: {available}"
            )

        price_pivot = data.get_pivot(price_column)

        short_ma = self.calculate_ma(price_pivot, self.short_window)
        long_ma = self.calculate_ma(price_pivot, self.long_window)

        signals = self._detect_crossovers(short_ma, long_ma)

        signal_data = []
        for date in signals.index:
            for code in signals.columns:
                signal_value = signals.loc[date, code]
                if not pd.isna(signal_value):
                    signal_data.append({
                        data.date_column: date,
                        data.code_column: code,
                        "signal": signal_value,
                    })

        if len(signal_data) == 0:
            raise ValueError("未能生成任何有效信号，请检查数据或参数")

        signal_matrix = SignalMatrix(
            pd.DataFrame(signal_data),
            date_column=data.date_column,
            code_column=data.code_column,
            signal_column="signal",
        )

        self._save_signals(
            signal_matrix,
            metadata={
                "short_window": self.short_window,
                "long_window": self.long_window,
                "ma_type": self.ma_type,
                "price_column": price_column,
                "n_dates": len(signals),
                "n_stocks": len(signals.columns),
            },
        )

        return signal_matrix
