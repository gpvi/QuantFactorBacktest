from __future__ import annotations

from dataclasses import dataclass
from math import ceil

from ..domain import FactorSignal, PortfolioWeights, TimeSeriesMatrix


@dataclass(frozen=True)
class TopNPercentLongOnlyConstructor:
    top_percent: float = 0.2
    rebalance_frequency: str = "daily"

    def build(self, signal: FactorSignal) -> PortfolioWeights:
        weights: TimeSeriesMatrix = {}
        rebalance_dates = self._rebalance_dates(sorted(signal.values.keys()))
        for date in rebalance_dates:
            cross_section = signal.values[date]
            top_n = max(1, ceil(len(cross_section) * self.top_percent))
            selected = sorted(
                cross_section.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:top_n]
            if not selected:
                weights[date] = {}
                continue
            equal_weight = 1.0 / len(selected)
            weights[date] = {asset: equal_weight for asset, _ in selected}
        return PortfolioWeights(weights=weights)

    def _rebalance_dates(self, dates: list[str]) -> list[str]:
        if self.rebalance_frequency == "daily":
            return dates
        if self.rebalance_frequency != "monthly":
            raise ValueError(f"Unsupported rebalance_frequency: {self.rebalance_frequency}")
        selected: list[str] = []
        seen_months: set[str] = set()
        for date in dates:
            month_key = date[:7]
            if month_key not in seen_months:
                seen_months.add(month_key)
                selected.append(date)
        return selected
