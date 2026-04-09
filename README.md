# QuantFactorBacktest

一个支持多因子研究与回测验证的最小框架，当前默认策略逻辑为：

- 每个交易日计算全市场因子值。
- 对每个因子做横截面 `z-score` 标准化。
- 按权重合成综合评分：`score = w1*f1 + w2*f2 + w3*f3`。
- 选取评分前 `20%` 的股票，等权持仓。
- 每月首个交易日调仓。
- 输出年化收益率、夏普比率、最大回撤、波动率、胜率、换手率。

当前已支持 `Tushare` 作为数据源接入层。
默认通过环境变量 `TUSHARE_TOKEN` 读取 token。
并已支持股票池过滤、交易成本/滑点、本地缓存。

架构说明见 [ARCHITECTURE.md](/E:/Projects/QuantFactorBacktest/docs/ARCHITECTURE.md)。
策略说明见 [STRATEGY.md](/E:/Projects/QuantFactorBacktest/docs/STRATEGY.md)。

## 设计目标

- 因子研究和回测解耦，避免研究逻辑直接耦合到交易引擎。
- 用统一的数据结构串起 `市场数据 -> 因子信号 -> 组合权重 -> 回测结果`。
- 先以测试驱动开发落最小闭环，再逐步扩展数据源、调仓规则、风险模型和绩效归因。

## 分层设计

### 1. `domain`

核心数据对象：

- `MarketData`: 市场价格矩阵。
- `FactorSignal`: 因子输出矩阵。
- `PortfolioWeights`: 组合权重矩阵。

### 1.5 `data`

数据接入层，负责把外部数据源转换为框架内部统一数据结构。

- `TushareDataClient`: 从 `Tushare` 拉取日线和基础指标，并转换为 `MarketData` 或记录列表。
- `TushareConfig`: 管理 `TUSHARE_TOKEN` 和复权配置。

### 1.6 `universe`

股票池过滤层，负责把不可投资标的在研究和回测之前剔除。

- `UniverseFilter`: 根据过滤规则生成可投资股票池。
- `UniverseFilterConfig`: 当前支持最低价格、ST、停牌、上市天数、涨跌停、流动性，以及按日期排除指定股票。

### 2. `factors`

因子定义层，负责从 `MarketData` 计算原始因子值。

- `MomentumFactor`: 基于价格的简单动量。
- `StaticDataFactor`: 用于外部基本面/财务因子接入，适合测试和研究原型。

### 3. `research`

研究编排层，负责多因子合成。

- `CompositeFactorModel`: 先做横截面 `z-score` 标准化，再按权重合成综合评分。
- `ResearchPipeline`: 串联因子计算、因子合成、组合构建和回测执行。

### 4. `portfolio`

组合构建层，负责把综合评分映射为可交易权重。

- `TopNPercentLongOnlyConstructor`: 取评分最高前 `20%` 标的等权持仓，支持按月调仓。

### 5. `backtest`

回测执行层，负责根据权重和价格计算收益曲线。

- `BacktestEngine`: 按当前时点权重持有到下一期，输出区间收益、净值曲线、换手率和绩效指标。
- 支持 `transaction_cost_rate` 和 `slippage_rate`，按调仓换手率扣减收益。

## 任务拆分

### Phase 1: 最小可运行闭环

1. 定义核心领域模型。
2. 实现基础因子接口与内置因子。
3. 实现多因子合成模型。
4. 实现最小组合构建器。
5. 实现日频回测引擎。
6. 写端到端测试验证主流程。

### Phase 2: 研究能力增强

1. 增加数据适配器，接入 CSV/Parquet/数据库。
2. 增加因子预处理：去极值、标准化、中性化、缺失值处理。
3. 增加调仓频率和交易日历。
4. 增加 IC、RankIC、分层回测、换手率等研究指标。

### Phase 3: 回测真实性增强

1. 加入交易成本、滑点、停牌和涨跌停约束。
2. 增加风险暴露约束和行业中性约束。
3. 增加多头、对冲、多空组合支持。
4. 增加参数搜索和实验记录。

## TDD 落地方式

当前代码按下面顺序实现：

1. 先写 `MomentumFactor` 测试。
2. 再写组合构建测试。
3. 再写多因子合成与端到端回测测试。
4. 最后补实现代码直到测试通过。

运行测试：

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -v
```

运行最小示例：

```powershell
$env:PYTHONPATH='src'
python examples/minimal_run.py
```

使用 `Tushare`：

```powershell
pip install .[data]
$env:TUSHARE_TOKEN='your-token'
$env:PYTHONPATH='src'
python examples/tushare_run.py
```

`Tushare` 接入示例代码见 [tushare.py](/E:/Projects/QuantFactorBacktest/src/quant_factor_backtest/data/tushare.py) 和 [tushare_run.py](/E:/Projects/QuantFactorBacktest/examples/tushare_run.py)。

当前支持：

- `fetch_market_data(trade_dates, ts_codes)`：拉取日线收盘价并按复权因子转换为 `MarketData`
- `fetch_market_data_with_universe_metadata(trade_dates, ts_codes)`：在价格之外补齐 `ST/停牌/上市天数/涨跌停/成交额`
- `fetch_daily_basic(trade_date)`：拉取 `pe/pb/total_mv` 等基础字段，便于扩展估值类和规模类因子
- `fetch_factor_signal(trade_dates, field)`：直接把 `daily_basic` 字段转换为 `FactorSignal`
- 本地缓存：相同查询会落到 `cache_dir`，后续优先读本地 JSON，减少重复 API 请求

当前已内置一个可直接进入研究流水线的真实因子适配器：

- `DailyBasicFieldFactor`：基于 `Tushare daily_basic` 生成 `PE/PB/总市值` 等横截面因子

示例 [tushare_run.py](/E:/Projects/QuantFactorBacktest/examples/tushare_run.py) 当前会：

- 从环境变量 `TUSHARE_TOKEN` 读取 token
- 拉取价格数据
- 拉取股票池过滤所需元数据
- 构造 `momentum`、`pe`、`pb`、`size` 四个因子
- 应用股票池过滤
- 按调仓换手率扣减交易成本和滑点
- 做月度调仓回测并输出绩效指标

## 后续建议

如果继续往生产级推进，优先补这几个能力：

1. `DataFrame`/`polars` 适配层。
2. 因子预处理流水线。
3. 交易成本模型和调仓日历。
4. 绩效分析与实验管理。
