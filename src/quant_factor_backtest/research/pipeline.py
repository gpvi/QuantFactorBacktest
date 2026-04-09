from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

from ..backtest.engine import BacktestEngine, BacktestResult
from ..domain import FactorSignal, MarketData, PortfolioWeights, TimeSeriesMatrix
from ..factors.base import Factor
from ..portfolio.construction import TopNPercentLongOnlyConstructor
from ..universe.filters import UniverseFilter


def _zscore_normalize(cross_section: dict[str, float]) -> dict[str, float]:
    total = len(cross_section)
    if total == 0:
        return {}
    values = list(cross_section.values())
    mean = sum(values) / total
    variance = sum((value - mean) ** 2 for value in values) / total
    std = sqrt(variance)
    if std == 0:
        return {asset: 0.0 for asset in cross_section}
    return {asset: (value - mean) / std for asset, value in cross_section.items()}


@dataclass(frozen=True)
class CompositeFactorModel:
    factor_weights: dict[str, float]

    def combine(self, signals: list[FactorSignal]) -> FactorSignal:
        signals_by_name = {signal.name: signal for signal in signals}
        common_dates = None
        for factor_name in self.factor_weights:
            signal = signals_by_name[factor_name]
            signal_dates = set(signal.values.keys())
            common_dates = signal_dates if common_dates is None else common_dates & signal_dates
        combined: TimeSeriesMatrix = {}
        for date in sorted(common_dates or []):
            per_factor = []
            for factor_name, weight in self.factor_weights.items():
                normalized = _zscore_normalize(signals_by_name[factor_name].values[date])
                per_factor.append((weight, normalized))
            assets = set()
            for _, normalized in per_factor:
                assets.update(normalized.keys())
            combined[date] = {
                asset: sum(weight * normalized.get(asset, 0.0) for weight, normalized in per_factor)
                for asset in assets
            }
        return FactorSignal(name="composite", values=combined)


@dataclass(frozen=True)
class ResearchPipeline:
    factors: list[Factor]
    factor_weights: dict[str, float]
    portfolio_constructor: TopNPercentLongOnlyConstructor
    backtest_engine: BacktestEngine
    universe_filter: UniverseFilter | None = None

    def run(self, market_data: MarketData) -> tuple[FactorSignal, PortfolioWeights, BacktestResult]:
        filtered_market_data = market_data
        allowed_assets = None
        if self.universe_filter is not None:
            filtered_context = self.universe_filter.apply(market_data)
            filtered_market_data = filtered_context.market_data
            allowed_assets = filtered_context.allowed_assets
        raw_signals = [factor.compute(filtered_market_data) for factor in self.factors]
        if self.universe_filter is not None and allowed_assets is not None:
            raw_signals = [self.universe_filter.apply_to_signal(signal, allowed_assets) for signal in raw_signals]
        composite = CompositeFactorModel(self.factor_weights).combine(raw_signals)
        weights = self.portfolio_constructor.build(composite)
        result = self.backtest_engine.run(filtered_market_data, weights)
        return composite, weights, result
