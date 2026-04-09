"""Multi-factor research and backtest framework."""

from .backtest.engine import BacktestEngine
from .data.tushare import TushareConfig, TushareDataClient
from .domain import FactorSignal, MarketData, PortfolioWeights
from .factors.builtin import DailyBasicFieldFactor
from .portfolio.construction import TopNPercentLongOnlyConstructor
from .research.pipeline import ResearchPipeline
from .universe.filters import UniverseFilter, UniverseFilterConfig

__all__ = [
    "BacktestEngine",
    "DailyBasicFieldFactor",
    "FactorSignal",
    "MarketData",
    "PortfolioWeights",
    "ResearchPipeline",
    "TushareConfig",
    "TushareDataClient",
    "TopNPercentLongOnlyConstructor",
    "UniverseFilter",
    "UniverseFilterConfig",
]
