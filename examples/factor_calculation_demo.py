"""
因子计算模块使用示例
展示如何使用 StockMatrix 和各种因子类进行因子计算
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.stock_matrix import StockMatrix
from factors.base import Factor
from factors.value import (
    PEFactor,
    PBFactor,
    ValueFactorComposite,
)
from factors.volatility import (
    VolatilityFactor,
    RollingVolatilityFactor,
    ATRFactor,
    IntraDayVolatilityFactor,
    VolatilityChangeFactor,
)


def generate_sample_data(
    n_dates: int = 60,
    n_stocks: int = 5,
    start_date: str = "20260101",
) -> pd.DataFrame:
    """
    生成模拟数据用于演示

    Args:
        n_dates: 日期数量
        n_stocks: 股票数量
        start_date: 开始日期

    Returns:
        包含 OHLCV、PE、PB 等数据的 DataFrame
    """
    np.random.seed(42)

    stock_codes = [f"00000{i+1}.SZ" for i in range(n_stocks)]

    start_dt = datetime.strptime(start_date, "%Y%m%d")
    dates = []
    for i in range(n_dates):
        dt = start_dt + timedelta(days=i)
        if dt.weekday() < 5:
            dates.append(dt.strftime("%Y%m%d"))

    records = []
    base_prices = np.random.uniform(10, 100, n_stocks)

    for date_idx, trade_date in enumerate(dates):
        for stock_idx, ts_code in enumerate(stock_codes):
            base_price = base_prices[stock_idx]
            price_change = np.random.normal(0, 0.02)
            close = base_price * (1 + price_change) ** (date_idx + 1)

            open_price = close * (1 + np.random.uniform(-0.01, 0.01))
            high = max(open_price, close) * (1 + np.random.uniform(0, 0.02))
            low = min(open_price, close) * (1 - np.random.uniform(0, 0.02))
            volume = np.random.randint(1000000, 10000000)

            pe = np.random.uniform(5, 50)
            pb = np.random.uniform(0.5, 10)
            pe_ttm = pe * np.random.uniform(0.9, 1.1)

            records.append(
                {
                    "trade_date": trade_date,
                    "ts_code": ts_code,
                    "open": round(open_price, 2),
                    "high": round(high, 2),
                    "low": round(low, 2),
                    "close": round(close, 2),
                    "volume": volume,
                    "pe": round(pe, 2),
                    "pe_ttm": round(pe_ttm, 2),
                    "pb": round(pb, 2),
                }
            )

    return pd.DataFrame(records)


def demo_stock_matrix():
    """
    演示 StockMatrix 的基本用法
    """
    print("=" * 60)
    print("1. StockMatrix 基本用法演示")
    print("=" * 60)

    df = generate_sample_data()
    print(f"\n原始数据形状: {df.shape}")
    print(f"原始数据列: {df.columns.tolist()}")

    matrix = StockMatrix(df)
    print(f"\nStockMatrix: {matrix}")
    print(f"日期数量: {len(matrix.dates)}")
    print(f"股票数量: {len(matrix.codes)}")
    print(f"指标列表: {matrix.indicators}")

    close_pivot = matrix.get_pivot("close")
    print(f"\n收盘价透视表形状: {close_pivot.shape}")
    print("收盘价透视表前5行:")
    print(close_pivot.head())

    close_matrix = matrix.get_matrix("close")
    print(f"\n收盘价矩阵形状: {close_matrix.shape}")

    filtered = matrix.filter_by_date(start_date="20260201", end_date="20260228")
    print(f"\n按日期过滤后: {filtered}")

    filtered_by_code = matrix.filter_by_codes(["000001.SZ", "000002.SZ"])
    print(f"按股票代码过滤后: {filtered_by_code}")


def demo_value_factors():
    """
    演示价值因子（PE、PB）的计算
    """
    print("\n" + "=" * 60)
    print("2. 价值因子（PE、PB）计算演示")
    print("=" * 60)

    df = generate_sample_data()
    matrix = StockMatrix(df)

    print("\n--- PE 因子 ---")
    pe_factor = PEFactor(pe_type="pe", inverse=False)
    pe_values = pe_factor.calculate(matrix)
    print(f"PE 因子值形状: {pe_values.shape}")
    print("PE 因子值前5行:")
    print(pe_values.head())
    print(f"\nPE 因子元数据: {pe_factor.metadata}")

    print("\n--- PE_TTM 因子（取倒数 E/P）---")
    pe_ttm_factor = PEFactor(pe_type="pe_ttm", inverse=True)
    ep_values = pe_ttm_factor.calculate(matrix)
    print(f"E/P 因子值形状: {ep_values.shape}")
    print("E/P 因子值前5行:")
    print(ep_values.head())

    print("\n--- PB 因子 ---")
    pb_factor = PBFactor(inverse=False)
    pb_values = pb_factor.calculate(matrix)
    print(f"PB 因子值形状: {pb_values.shape}")
    print("PB 因子值前5行:")
    print(pb_values.head())

    print("\n--- 综合价值因子 ---")
    composite_factor = ValueFactorComposite(method="zscore")
    composite_value = composite_factor.calculate(
        factors_data={"PE": pe_values, "PB": pb_values},
        weights={"PE": 0.5, "PB": 0.5},
    )
    print(f"综合价值因子形状: {composite_value.shape}")
    print("综合价值因子前5行:")
    print(composite_value.head())


def demo_volatility_factors():
    """
    演示波动率因子的计算
    """
    print("\n" + "=" * 60)
    print("3. 波动率因子计算演示")
    print("=" * 60)

    df = generate_sample_data(n_dates=100)
    matrix = StockMatrix(df)

    print("\n--- 历史波动率（20日窗口，年化）---")
    vol_factor = VolatilityFactor(window=20, annualized=True)
    vol_values = vol_factor.calculate(matrix, price_column="close")
    print(f"波动率形状: {vol_values.shape}")
    print("波动率前10行:")
    print(vol_values.head(10))
    print(f"\n波动率元数据: {vol_factor.metadata}")

    print("\n--- 多窗口滚动波动率 ---")
    rolling_vol_factor = RollingVolatilityFactor(windows=[5, 10, 20, 60])
    rolling_vol_values = rolling_vol_factor.calculate(matrix)
    for window, values in rolling_vol_values.items():
        print(f"{window}日波动率形状: {values.shape}")
        print(f"  最近5个日期的平均波动率:")
        print(values.tail().mean())

    print("\n--- ATR（真实波动幅度）---")
    atr_factor = ATRFactor(window=14, method="ma")
    atr_values = atr_factor.calculate(
        matrix,
        high_column="high",
        low_column="low",
        close_column="close",
    )
    print(f"ATR 形状: {atr_values.shape}")
    print("ATR 前10行:")
    print(atr_values.head(10))

    print("\n--- 日内波动率 ---")
    intraday_vol_factor = IntraDayVolatilityFactor(method="range")
    intraday_vol_values = intraday_vol_factor.calculate(
        matrix,
        open_column="open",
        high_column="high",
        low_column="low",
        close_column="close",
    )
    print(f"日内波动率形状: {intraday_vol_values.shape}")
    print("日内波动率前5行:")
    print(intraday_vol_values.head())

    print("\n--- 波动率变化（短期/长期）---")
    vol_change_factor = VolatilityChangeFactor(short_window=5, long_window=20)
    vol_change_values = vol_change_factor.calculate(matrix, method="ratio")
    print(f"波动率变化形状: {vol_change_values.shape}")
    print("波动率变化前10行:")
    print(vol_change_values.head(10))


def demo_factor_preprocessing():
    """
    演示因子预处理（去极值、标准化）
    """
    print("\n" + "=" * 60)
    print("4. 因子预处理演示")
    print("=" * 60)

    df = generate_sample_data()
    matrix = StockMatrix(df)

    pe_factor = PEFactor()
    pe_values = pe_factor.calculate(matrix)

    print("\n--- 原始 PE 因子 ---")
    print(f"原始 PE 统计:\n{pe_values.stack().describe()}")

    print("\n--- 去极值（缩尾处理 1%-99%）---")
    pe_winsorized = pe_factor.winsorize(pe_values, lower=0.01, upper=0.99)
    print(f"去极值后 PE 统计:\n{pe_winsorized.stack().describe()}")

    print("\n--- 标准化（Z-score）---")
    pe_standardized = pe_factor.standardize(pe_winsorized)
    print(f"标准化后 PE 统计:\n{pe_standardized.stack().describe()}")


def main():
    """
    主函数
    """
    print("=" * 60)
    print("因子计算模块使用示例")
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    demo_stock_matrix()
    demo_value_factors()
    demo_volatility_factors()
    demo_factor_preprocessing()

    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
