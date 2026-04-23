"""
策略模块
包含策略基类、信号矩阵模型、单因子策略、多因子合成策略和均线交叉策略
"""

from .base import Strategy
from .signal_matrix import SignalMatrix
from .single_factor import (
    MomentumStrategy,
    LowVolatilityStrategy,
)
from .multi_factor import MultiFactorCompositeStrategy
from .ma_crossover import MACrossoverStrategy

__all__ = [
    "Strategy",
    "SignalMatrix",
    "MomentumStrategy",
    "LowVolatilityStrategy",
    "MultiFactorCompositeStrategy",
    "MACrossoverStrategy",
]
