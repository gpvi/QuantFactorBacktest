from __future__ import annotations

from typing import Protocol

from ..domain import FactorSignal, MarketData


class Factor(Protocol):
    name: str

    def compute(self, market_data: MarketData) -> FactorSignal:
        ...
