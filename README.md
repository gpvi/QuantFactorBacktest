# QuantFactorBacktest

一个用于多因子研究与回测验证的最小框架。

当前项目已支持：

- `Tushare` 数据接入
- 基于 `polars` 的数据处理与股票池过滤
- 基于 SQLite 的本地缓存
- 多因子合成
- 月度调仓
- 交易成本和滑点

项目结构、架构设计和策略解读请查看 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) 和 [docs/STRATEGY.md](docs/STRATEGY.md)。
如果需要按函数粒度查看数据如何流动，请看 [docs/DATA_FLOW.md](docs/DATA_FLOW.md)。
如果你是第一次参与开发，请先看 [docs/WIKI.md](docs/WIKI.md)。

## 安装

基础安装：

```powershell
pip install -e .
```

如果要使用 `Tushare` 数据源：

```powershell
pip install -e .[data]
```

当前 `data` 依赖包含：

- `tushare`
- `polars`

默认缓存行为：

- 当启用 `cache_dir` 时，`Tushare` 数据会缓存到 `cache_dir/cache.sqlite3`
- 默认路径是 [`.cache/tushare/cache.sqlite3`](.cache/tushare/cache.sqlite3)
- 不再使用旧的按接口拆分 JSON 目录缓存

缓存目录结构：

```text
.cache/
  tushare/
    cache.sqlite3
```

## 环境变量

使用 `Tushare` 前需要设置 token：

```powershell
$env:TUSHARE_TOKEN='your-token'
```

## 运行测试

```powershell
$env:PYTHONPATH='src'
python -m pytest
```

或：

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -v
```

## 运行示例

最小示例：

```powershell
$env:PYTHONPATH='src'
python examples/minimal_run.py
```

`Tushare` 示例：

```powershell
$env:TUSHARE_TOKEN='your-token'
$env:PYTHONPATH='src'
python examples/tushare_run.py
```

示例代码见：

- [examples/minimal_run.py](examples/minimal_run.py)
- [examples/tushare_run.py](examples/tushare_run.py)

## 常用入口

数据层：

- [src/quant_factor_backtest/data/cache.py](src/quant_factor_backtest/data/cache.py)
- [src/quant_factor_backtest/data/tushare/client.py](src/quant_factor_backtest/data/tushare/client.py)
- [src/quant_factor_backtest/data/tushare/fetch.py](src/quant_factor_backtest/data/tushare/fetch.py)
- [src/quant_factor_backtest/data/tushare/assemble.py](src/quant_factor_backtest/data/tushare/assemble.py)
- [src/quant_factor_backtest/data/tushare/convert.py](src/quant_factor_backtest/data/tushare/convert.py)

研究主链路：

- [src/quant_factor_backtest/research/pipeline.py](src/quant_factor_backtest/research/pipeline.py)

回测引擎：

- [src/quant_factor_backtest/backtest/engine.py](src/quant_factor_backtest/backtest/engine.py)

## 文档

- 开发 Wiki：[docs/WIKI.md](docs/WIKI.md)
- 架构说明：[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- 数据流说明：[docs/DATA_FLOW.md](docs/DATA_FLOW.md)
- 策略说明：[docs/STRATEGY.md](docs/STRATEGY.md)
