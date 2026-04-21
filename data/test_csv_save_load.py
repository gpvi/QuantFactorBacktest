"""
测试 CSV 保存和加载功能
测试按股票分别保存和加载的功能
"""

from pathlib import Path
import sys
import pandas as pd
import polars as pl
import numpy as np
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from save_to_csv import (
    save_to_csv,
    save_to_csv_by_stock,
    save_valuation_data,
    save_stock_matrix_by_stock,
)
from load_data import (
    load_daily,
    load_daily_by_stock,
    load_daily_by_stocks,
    load_valuation_data,
    list_available_stocks,
)


def generate_sample_data(n_dates: int = 30, n_stocks: int = 3) -> pd.DataFrame:
    """
    生成模拟数据用于测试

    生成日线行情数据和估值数据
    """
    np.random.seed(42)

    stock_codes = ["000001.SZ", "600000.SH", "000858.SZ"][:n_stocks]

    start_dt = datetime(2026, 1, 1)
    dates = []
    for i in range(n_dates):
        dt = start_dt + timedelta(days=i)
        if dt.weekday() < 5:
            dates.append(dt.strftime("%Y%m%d"))

    records = []

    for trade_date in dates:
        for ts_code in stock_codes:
            base_price = np.random.uniform(10, 100)
            open_price = base_price
            close_price = base_price * (1 + np.random.normal(0, 0.02))
            high_price = max(open_price, close_price) * (1 + np.random.uniform(0, 0.01))
            low_price = min(open_price, close_price) * (1 - np.random.uniform(0, 0.01))
            volume = np.random.randint(1000000, 10000000)

            pe = np.random.uniform(5, 50)
            pb = np.random.uniform(0.5, 10)

            records.append(
                {
                    "ts_code": ts_code,
                    "trade_date": trade_date,
                    "open": round(open_price, 2),
                    "high": round(high_price, 2),
                    "low": round(low_price, 2),
                    "close": round(close_price, 2),
                    "volume": volume,
                    "pe": round(pe, 2),
                    "pe_ttm": round(pe * np.random.uniform(0.9, 1.1), 2),
                    "pb": round(pb, 2),
                    "total_mv": round(np.random.uniform(100, 5000), 2),
                }
            )

    return pd.DataFrame(records)


def test_save_to_csv_by_stock():
    """
    测试按股票分别保存功能
    """
    print("=" * 60)
    print("测试 1: save_to_csv_by_stock - 按股票分别保存")
    print("=" * 60)

    df = generate_sample_data(n_dates=30, n_stocks=3)
    print(f"\n原始数据形状: {df.shape}")
    print(f"包含的股票: {df['ts_code'].unique().tolist()}")

    test_dir = Path(__file__).parent / "csv_test"
    test_dir.mkdir(parents=True, exist_ok=True)

    saved_files = save_to_csv_by_stock(
        df=df,
        output_dir=test_dir,
        code_column="ts_code",
        date_column="trade_date",
        start_date="20260101",
        end_date="20260201",
    )

    print(f"\n已保存的文件:")
    for code, file_path in saved_files.items():
        print(f"  {code}: {file_path.name}")
        df_stock = pd.read_csv(file_path)
        print(f"    数据行数: {len(df_stock)}")

    return saved_files, test_dir


def test_load_daily_by_stock(saved_files: dict, test_dir: Path):
    """
    测试按股票加载功能
    """
    print("\n" + "=" * 60)
    print("测试 2: load_daily_by_stock - 按股票加载")
    print("=" * 60)

    for code in saved_files.keys():
        try:
            df = load_daily_by_stock(
                code=code,
                start_date="20260101",
                end_date="20260201",
                data_dir=test_dir,
            )
            print(f"\n{code}:")
            print(f"  数据形状: {df.shape}")
            print(f"  列名: {df.columns}")
            print(f"  前3行:")
            print(df.head(3))
        except Exception as e:
            print(f"\n{code}: 加载失败 - {e}")


def test_load_daily_by_stocks(saved_files: dict, test_dir: Path):
    """
    测试加载多只股票并合并
    """
    print("\n" + "=" * 60)
    print("测试 3: load_daily_by_stocks - 加载多只股票并合并")
    print("=" * 60)

    codes = list(saved_files.keys())

    try:
        df = load_daily_by_stocks(
            codes=codes,
            start_date="20260101",
            end_date="20260201",
            data_dir=test_dir,
        )
        print(f"\n合并后数据形状: {df.shape}")
        print(f"包含的股票代码: {df['ts_code'].unique().to_list()}")
        print(f"\n按股票分组统计:")
        for code in codes:
            count = len(df.filter(pl.col("ts_code") == code))
            print(f"  {code}: {count} 行")
    except Exception as e:
        print(f"\n加载失败: {e}")


def test_save_valuation_data():
    """
    测试保存估值数据
    """
    print("\n" + "=" * 60)
    print("测试 4: save_valuation_data - 保存估值数据")
    print("=" * 60)

    df = generate_sample_data(n_dates=20, n_stocks=2)

    valuation_df = df[["ts_code", "trade_date", "pe", "pe_ttm", "pb", "total_mv"]].copy()

    test_dir = Path(__file__).parent / "csv_test"
    saved_files = save_valuation_data(
        df=valuation_df,
        output_dir=test_dir,
        code_column="ts_code",
        date_column="trade_date",
        start_date="20260101",
        end_date="20260201",
    )

    print(f"\n已保存的估值数据文件:")
    for code, file_path in saved_files.items():
        print(f"  {code}: {file_path.name}")


def test_list_available_stocks(test_dir: Path):
    """
    测试列出可用股票
    """
    print("\n" + "=" * 60)
    print("测试 5: list_available_stocks - 列出可用股票")
    print("=" * 60)

    try:
        available_stocks = list_available_stocks(
            data_dir=test_dir,
            data_type="daily",
        )

        if available_stocks:
            print("\n可用的日线股票数据:")
            for code, date_ranges in available_stocks.items():
                print(f"  {code}:")
                for start, end in date_ranges:
                    print(f"    {start} 至 {end}")
        else:
            print("\n未找到日线数据文件")

    except Exception as e:
        print(f"\n出错: {e}")


def test_backward_compatibility(test_dir: Path):
    """
    测试向后兼容性 - 旧的单文件保存和加载方式
    """
    print("\n" + "=" * 60)
    print("测试 6: 向后兼容性 - 单文件保存和加载")
    print("=" * 60)

    df = generate_sample_data(n_dates=10, n_stocks=2)

    single_file = test_dir / "combined_test.csv"
    saved_path = save_to_csv(df, single_file)
    print(f"\n合并文件已保存: {saved_path.name}")

    try:
        loaded_df = load_daily(file_name="combined_test.csv", data_dir=test_dir)
        print(f"加载成功，数据形状: {loaded_df.shape}")
    except Exception as e:
        print(f"加载失败: {e}")


def test_architecture_design():
    """
    测试架构设计：验证 fetch 和 save 的独立性
    """
    print("\n" + "=" * 60)
    print("测试 7: 架构设计验证 - fetch 和 save 的独立性")
    print("=" * 60)

    print("\n检查模块依赖关系:")

    try:
        import inspect
        import fetch_data
        import save_to_csv

        fetch_source = inspect.getsourcefile(fetch_data)
        save_source = inspect.getsourcefile(save_to_csv)

        print(f"  fetch_data.py: {fetch_source}")
        print(f"  save_to_csv.py: {save_source}")

        with open(fetch_source, 'r', encoding='utf-8') as f:
            fetch_content = f.read()

        with open(save_source, 'r', encoding='utf-8') as f:
            save_content = f.read()

        fetch_imports_save = 'save_to_csv' in fetch_content or 'import save' in fetch_content
        save_imports_fetch = 'fetch_data' in save_content or 'from fetch' in save_content

        print(f"\n依赖关系检查:")
        print(f"  fetch_data 导入 save_to_csv: {'❌ 是' if fetch_imports_save else '✓ 否'}")
        print(f"  save_to_csv 导入 fetch_data: {'✓ 是（这是正确的，save 依赖 fetch）' if save_imports_fetch else '否'}")

        if not fetch_imports_save and save_imports_fetch:
            print("\n✓ 架构设计正确：单向依赖关系")
            print("  - fetch_data.py: 纯数据获取（独立，无 save 依赖）")
            print("  - save_to_csv.py: 数据保存 + 组合操作（依赖 fetch）")
            print("  - 依赖方向: save_to_csv → fetch_data（单向，正确）")
        elif fetch_imports_save:
            print("\n❌ 架构设计存在问题：fetch_data 依赖了 save_to_csv")
            print("  应该只有 save_to_csv 依赖 fetch_data，而不是反向依赖")
        else:
            print("\n⚠️  架构设计：save_to_csv 没有依赖 fetch_data")
            print("  如果 save_to_csv 中包含 fetch_and_save 组合操作，应该导入 fetch_data")

    except Exception as e:
        print(f"  架构检查出错: {e}")


def main():
    """
    主测试函数
    """
    print("=" * 60)
    print("CSV 保存和加载功能测试")
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    saved_files, test_dir = test_save_to_csv_by_stock()

    if saved_files:
        test_load_daily_by_stock(saved_files, test_dir)
        test_load_daily_by_stocks(saved_files, test_dir)

    test_save_valuation_data()
    test_list_available_stocks(test_dir)
    test_backward_compatibility(test_dir)
    test_architecture_design()

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
