from __future__ import annotations

from dataclasses import dataclass

Date = str
Asset = str
Scalar = float
CrossSection = dict[Asset, Scalar]
TimeSeriesMatrix = dict[Date, CrossSection]


@dataclass(frozen=True)
class MarketData:
    prices: TimeSeriesMatrix
    is_st: dict[Date, dict[Asset, bool]] | None = None
    is_suspended: dict[Date, dict[Asset, bool]] | None = None
    listed_days: dict[Date, dict[Asset, int]] | None = None
    is_limit_up: dict[Date, dict[Asset, bool]] | None = None
    is_limit_down: dict[Date, dict[Asset, bool]] | None = None
    turnover_amount: TimeSeriesMatrix | None = None

    def dates(self) -> list[Date]:
        return sorted(self.prices.keys())

    def assets(self) -> list[Asset]:
        asset_set: set[Asset] = set()
        for cross_section in self.prices.values():
            asset_set.update(cross_section.keys())
        return sorted(asset_set)


@dataclass(frozen=True)
class FactorSignal:
    name: str
    values: TimeSeriesMatrix


@dataclass(frozen=True)
class PortfolioWeights:
    weights: TimeSeriesMatrix
