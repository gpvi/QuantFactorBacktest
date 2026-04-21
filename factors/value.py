"""
价值因子模块
包含 PE（市盈率）、PB（市净率）等价值因子的计算
"""

from typing import Optional, Dict, Any, List
import pandas as pd
import polars as pl
import numpy as np

from .base import Factor
from models.stock_matrix import StockMatrix


class PEFactor(Factor):
    """
    市盈率（PE）因子
    市盈率 = 股价 / 每股收益
    PE 越低，股票相对越便宜
    """

    factor_type: str = "value"
    factor_name: str = "PE"

    def __init__(
        self,
        name: Optional[str] = None,
        pe_type: str = "pe",
        inverse: bool = False,
        **kwargs,
    ):
        """
        初始化 PE 因子

        Args:
            name: 因子名称
            pe_type: PE 类型，可选：
                - 'pe': 市盈率(总市值/净利润)
                - 'pe_ttm': 市盈率TTM
                - 'pe_lyr': 静态市盈率
            inverse: 是否取倒数（即收益市值比 E/P），默认为 False
                     当 PE 为负值时，取倒数更有意义
            **kwargs: 其他参数
        """
        super().__init__(name=name, **kwargs)
        self.pe_type = pe_type
        self.inverse = inverse

    def calculate(
        self,
        data: StockMatrix,
        pe_column: Optional[str] = None,
        **kwargs,
    ) -> pd.DataFrame:
        """
        计算 PE 因子值

        Args:
            data: 股票矩阵数据
            pe_column: PE 数据列名，如果未指定则根据 pe_type 自动选择
            **kwargs: 额外参数

        Returns:
            PE 因子值的透视表（时间×股票）
        """
        if pe_column is None:
            pe_column = self.pe_type

        if pe_column not in data.indicators:
            available = data.indicators
            raise ValueError(
                f"数据中未找到 PE 列 '{pe_column}'。"
                f"可用的指标列: {available}"
            )

        pe_pivot = data.get_pivot(pe_column)

        if self.inverse:
            result = 1 / pe_pivot.replace([np.inf, -np.inf], np.nan)
        else:
            result = pe_pivot

        self._save_result(
            result,
            metadata={
                "pe_type": self.pe_type,
                "inverse": self.inverse,
                "column": pe_column,
                "n_dates": len(result),
                "n_stocks": len(result.columns),
            },
        )

        return result

    def calculate_using_price_eps(
        self,
        price_data: StockMatrix,
        eps_data: StockMatrix,
        price_column: str = "close",
        eps_column: str = "eps",
    ) -> pd.DataFrame:
        """
        使用股价和每股收益计算 PE
        PE = 股价 / 每股收益

        Args:
            price_data: 股价数据
            eps_data: 每股收益数据
            price_column: 股价列名
            eps_column: 每股收益列名

        Returns:
            PE 因子值的透视表
        """
        price_pivot = price_data.get_pivot(price_column)
        eps_pivot = eps_data.get_pivot(eps_column)

        common_dates = price_pivot.index.intersection(eps_pivot.index)
        common_codes = price_pivot.columns.intersection(eps_pivot.columns)

        price_aligned = price_pivot.loc[common_dates, common_codes]
        eps_aligned = eps_pivot.loc[common_dates, common_codes]

        pe = price_aligned / eps_aligned.replace(0, np.nan)

        if self.inverse:
            result = 1 / pe.replace([np.inf, -np.inf], np.nan)
        else:
            result = pe

        self._save_result(
            result,
            metadata={
                "pe_type": "calculated",
                "inverse": self.inverse,
                "price_column": price_column,
                "eps_column": eps_column,
                "n_dates": len(result),
                "n_stocks": len(result.columns),
            },
        )

        return result

    @staticmethod
    def pe_ttm(
        data: StockMatrix,
        pe_ttm_column: str = "pe_ttm",
        inverse: bool = False,
    ) -> pd.DataFrame:
        """
        静态方法：计算 PE_TTM 因子

        Args:
            data: 股票矩阵数据
            pe_ttm_column: PE_TTM 列名
            inverse: 是否取倒数

        Returns:
            PE_TTM 因子值
        """
        factor = PEFactor(pe_type="pe_ttm", inverse=inverse)
        return factor.calculate(data, pe_column=pe_ttm_column)

    @staticmethod
    def pe_lyr(
        data: StockMatrix,
        pe_lyr_column: str = "pe_lyr",
        inverse: bool = False,
    ) -> pd.DataFrame:
        """
        静态方法：计算静态 PE 因子

        Args:
            data: 股票矩阵数据
            pe_lyr_column: PE_LYR 列名
            inverse: 是否取倒数

        Returns:
            PE_LYR 因子值
        """
        factor = PEFactor(pe_type="pe_lyr", inverse=inverse)
        return factor.calculate(data, pe_column=pe_lyr_column)


class PBFactor(Factor):
    """
    市净率（PB）因子
    市净率 = 股价 / 每股净资产
    PB 越低，股票相对越便宜
    """

    factor_type: str = "value"
    factor_name: str = "PB"

    def __init__(
        self,
        name: Optional[str] = None,
        inverse: bool = False,
        **kwargs,
    ):
        """
        初始化 PB 因子

        Args:
            name: 因子名称
            inverse: 是否取倒数（即净资产市值比 B/P），默认为 False
            **kwargs: 其他参数
        """
        super().__init__(name=name, **kwargs)
        self.inverse = inverse

    def calculate(
        self,
        data: StockMatrix,
        pb_column: str = "pb",
        **kwargs,
    ) -> pd.DataFrame:
        """
        计算 PB 因子值

        Args:
            data: 股票矩阵数据
            pb_column: PB 数据列名
            **kwargs: 额外参数

        Returns:
            PB 因子值的透视表（时间×股票）
        """
        if pb_column not in data.indicators:
            available = data.indicators
            raise ValueError(
                f"数据中未找到 PB 列 '{pb_column}'。"
                f"可用的指标列: {available}"
            )

        pb_pivot = data.get_pivot(pb_column)

        if self.inverse:
            result = 1 / pb_pivot.replace([np.inf, -np.inf], np.nan)
        else:
            result = pb_pivot

        self._save_result(
            result,
            metadata={
                "inverse": self.inverse,
                "column": pb_column,
                "n_dates": len(result),
                "n_stocks": len(result.columns),
            },
        )

        return result

    def calculate_using_price_navps(
        self,
        price_data: StockMatrix,
        navps_data: StockMatrix,
        price_column: str = "close",
        navps_column: str = "navps",
    ) -> pd.DataFrame:
        """
        使用股价和每股净资产计算 PB
        PB = 股价 / 每股净资产

        Args:
            price_data: 股价数据
            navps_data: 每股净资产数据
            price_column: 股价列名
            navps_column: 每股净资产列名

        Returns:
            PB 因子值的透视表
        """
        price_pivot = price_data.get_pivot(price_column)
        navps_pivot = navps_data.get_pivot(navps_column)

        common_dates = price_pivot.index.intersection(navps_pivot.index)
        common_codes = price_pivot.columns.intersection(navps_pivot.columns)

        price_aligned = price_pivot.loc[common_dates, common_codes]
        navps_aligned = navps_pivot.loc[common_dates, common_codes]

        pb = price_aligned / navps_aligned.replace(0, np.nan)

        if self.inverse:
            result = 1 / pb.replace([np.inf, -np.inf], np.nan)
        else:
            result = pb

        self._save_result(
            result,
            metadata={
                "inverse": self.inverse,
                "price_column": price_column,
                "navps_column": navps_column,
                "n_dates": len(result),
                "n_stocks": len(result.columns),
            },
        )

        return result


class ValueFactorComposite(Factor):
    """
    价值因子组合
    结合 PE、PB 等多个价值因子构建综合价值因子
    """

    factor_type: str = "value"
    factor_name: str = "ValueComposite"

    def __init__(
        self,
        name: Optional[str] = None,
        method: str = "equal_weight",
        **kwargs,
    ):
        """
        初始化价值因子组合

        Args:
            name: 因子名称
            method: 组合方法，可选：
                - 'equal_weight': 等权重
                - 'zscore': Z-score 标准化后等权重
                - 'rank': 排名平均
            **kwargs: 其他参数
        """
        super().__init__(name=name, **kwargs)
        self.method = method

    def calculate(
        self,
        factors_data: Dict[str, pd.DataFrame],
        weights: Optional[Dict[str, float]] = None,
        **kwargs,
    ) -> pd.DataFrame:
        """
        计算综合价值因子

        Args:
            factors_data: 因子数据字典，格式为 {因子名: DataFrame}
            weights: 各因子权重字典，格式为 {因子名: 权重}
                     如未指定则使用等权重
            **kwargs: 额外参数

        Returns:
            综合价值因子的透视表
        """
        if not factors_data:
            raise ValueError("因子数据不能为空")

        if weights is None:
            n_factors = len(factors_data)
            weights = {name: 1.0 / n_factors for name in factors_data.keys()}

        factor_names = list(factors_data.keys())
        first_factor = factors_data[factor_names[0]]
        common_index = first_factor.index
        common_columns = first_factor.columns

        for name in factor_names[1:]:
            common_index = common_index.intersection(factors_data[name].index)
            common_columns = common_columns.intersection(factors_data[name].columns)

        aligned_factors = {}
        for name, data in factors_data.items():
            aligned_factors[name] = data.loc[common_index, common_columns]

        if self.method == "equal_weight":
            composite = sum(
                aligned_factors[name] * weights[name] for name in factor_names
            )
        elif self.method == "zscore":
            standardized_factors = {}
            for name, data in aligned_factors.items():
                mean = data.stack().mean()
                std = data.stack().std()
                standardized_factors[name] = (data - mean) / std

            composite = sum(
                standardized_factors[name] * weights[name] for name in factor_names
            )
        elif self.method == "rank":
            ranked_factors = {}
            for name, data in aligned_factors.items():
                ranked_factors[name] = data.rank(axis=1)

            composite = sum(
                ranked_factors[name] * weights[name] for name in factor_names
            )
        else:
            raise ValueError(f"不支持的组合方法: {self.method}")

        self._save_result(
            composite,
            metadata={
                "method": self.method,
                "factors": factor_names,
                "weights": weights,
                "n_dates": len(composite),
                "n_stocks": len(composite.columns),
            },
        )

        return composite
