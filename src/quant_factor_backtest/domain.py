from __future__ import annotations

from dataclasses import dataclass

# 交易日字符串，比如 "20240102"。
TradeDate = str
# 资产代码，比如 "000001.SZ"。
AssetCode = str
# 通用数值，比如价格、权重、因子值。
NumericValue = float

# 单个交易日上的资产横截面数值映射。
AssetValueMap = dict[AssetCode, NumericValue]
# 按交易日组织的二维数值矩阵。
DateAssetValueMatrix = dict[TradeDate, AssetValueMap]

# 兼容旧命名，避免一次性影响所有上层模块。
Date = TradeDate
Asset = AssetCode
Scalar = NumericValue
CrossSection = AssetValueMap
TimeSeriesMatrix = DateAssetValueMatrix


@dataclass(frozen=True)
class MarketData:
    prices: DateAssetValueMatrix
    is_st: dict[TradeDate, dict[AssetCode, bool]] | None = None
    is_suspended: dict[TradeDate, dict[AssetCode, bool]] | None = None
    listed_days: dict[TradeDate, dict[AssetCode, int]] | None = None
    is_limit_up: dict[TradeDate, dict[AssetCode, bool]] | None = None
    is_limit_down: dict[TradeDate, dict[AssetCode, bool]] | None = None
    turnover_amount: DateAssetValueMatrix | None = None

    def dates(self) -> list[TradeDate]:
        return sorted(self.prices.keys())

    def assets(self) -> list[AssetCode]:
        asset_codes: set[AssetCode] = set()
        for daily_prices in self.prices.values():
            asset_codes.update(daily_prices.keys())
        return sorted(asset_codes)


@dataclass(frozen=True)
class FactorSignal:
    name: str
    values: DateAssetValueMatrix


@dataclass(frozen=True)
class PortfolioWeights:
    weights: DateAssetValueMatrix
