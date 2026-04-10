# QuantFactorBacktest Developer Wiki

## 1. 这份文档给谁看

这份 Wiki 面向刚接手项目的新开发者。

目标不是解释某一个策略公式，而是帮助你尽快回答下面这些问题：

- 这个项目是干什么的
- 我应该先看哪些代码
- 数据是怎么流动的
- 想加一个功能时应该改哪里
- 怎么写出和当前项目风格一致的代码与文档

如果你只想安装和运行项目，请先看 [README.md](../README.md)。

## 2. 建议阅读顺序

新开发者最省时间的阅读顺序如下：

1. [README.md](../README.md)
   先确认项目能装起来、测起来、跑起来。

2. [ARCHITECTURE.md](ARCHITECTURE.md)
   先建立模块分层和整体边界感。

3. [DATA_FLOW.md](DATA_FLOW.md)
   再理解函数级数据流，尤其是 `Tushare -> polars -> MarketData` 这条链。

4. [STRATEGY.md](STRATEGY.md)
   最后再看策略逻辑和指标口径。

5. 核心代码入口
   推荐顺序：
   - [domain.py](../src/quant_factor_backtest/domain.py)
   - [pipeline.py](../src/quant_factor_backtest/research/pipeline.py)
   - [construction.py](../src/quant_factor_backtest/portfolio/construction.py)
   - [engine.py](../src/quant_factor_backtest/backtest/engine.py)
   - [client.py](../src/quant_factor_backtest/data/tushare/client.py)

## 3. 项目当前最重要的认识

### 3.1 这是一个研究框架，不是完整交易系统

当前项目更偏：

- 因子研究
- 组合构建
- 回测验证

而不是：

- 实盘交易接入
- 撮合级执行模拟
- 多账户生产调度

所以很多设计都优先考虑：

- 清晰
- 可测试
- 可扩展

而不是一步到位做重。

### 3.2 当前主数据形态是“底层表格化，上层领域对象化”

这是理解项目的关键。

现在项目底层已经部分迁移到：

- `polars.DataFrame`
- SQLite 缓存

但研究和回测主链路仍主要使用领域对象：

- `MarketData`
- `FactorSignal`
- `PortfolioWeights`

所以你会看到一些适配边界：

- `raw records -> polars table`
- `polars table -> MarketData`
- `MarketData -> polars table -> MarketData`

这不是错误，而是当前架构过渡阶段的现实。

### 3.3 当前最值得继续优化的是研究主链路

数据层和股票池过滤已经比较清楚了。

接下来最有价值的演进方向通常不是继续加更多 helper，而是：

- 把 `research/pipeline.py` 的标准化与合成继续迁到列式实现
- 再看 `portfolio` 和 `backtest`

## 4. 代码地图

### 4.1 领域层

- [domain.py](../src/quant_factor_backtest/domain.py)

这里定义了项目内部最重要的共享对象：

- `MarketData`
- `FactorSignal`
- `PortfolioWeights`

很多代码改动都要先问自己一句：

“这个变化是领域层变化，还是只是某个实现层变化？”

### 4.2 数据层

路径：

- [cache.py](../src/quant_factor_backtest/data/cache.py)
- [fetch.py](../src/quant_factor_backtest/data/tushare/fetch.py)
- [client.py](../src/quant_factor_backtest/data/tushare/client.py)
- [assemble.py](../src/quant_factor_backtest/data/tushare/assemble.py)
- [convert.py](../src/quant_factor_backtest/data/tushare/convert.py)

理解方式：

- `fetch.py`
  负责和外部 API 通信
- `client.py`
  负责缓存与编排
- `assemble.py`
  负责组装 `polars` 中间表
- `convert.py`
  负责把表转成领域对象

如果你要新增一个 Tushare 字段，通常要先判断它属于哪一步。

### 4.3 股票池过滤

- [filters.py](../src/quant_factor_backtest/universe/filters.py)

这里的核心点不是规则多，而是：

- 当前过滤发生在因子合成之前
- 过滤逻辑已经使用 `polars`
- 过滤结果最后仍要回到 `MarketData`

### 4.4 因子与研究

- [builtin.py](../src/quant_factor_backtest/factors/builtin.py)
- [pipeline.py](../src/quant_factor_backtest/research/pipeline.py)

这里决定：

- 因子怎么定义
- 多因子怎么合成
- 研究流程怎么编排

### 4.5 组合与回测

- [construction.py](../src/quant_factor_backtest/portfolio/construction.py)
- [engine.py](../src/quant_factor_backtest/backtest/engine.py)

这里决定：

- 评分怎么变成权重
- 权重怎么变成收益与指标

## 5. 常见开发任务应该改哪里

### 5.1 新增一个 Tushare 原始字段

常见落点：

- [constants/tushare.py](../src/quant_factor_backtest/constants/tushare.py)
- [fetch.py](../src/quant_factor_backtest/data/tushare/fetch.py)
- [assemble.py](../src/quant_factor_backtest/data/tushare/assemble.py)
- [convert.py](../src/quant_factor_backtest/data/tushare/convert.py)

判断顺序：

1. 是不是要新增字段常量
2. 是不是要加入默认 fields
3. 是不是要进入中间表
4. 是不是要进入 `MarketData` 或 `FactorSignal`

### 5.2 新增一个股票池过滤条件

常见落点：

- [filters.py](../src/quant_factor_backtest/universe/filters.py)
- [domain.py](../src/quant_factor_backtest/domain.py)
- 如需新元数据，还可能涉及 [assemble.py](../src/quant_factor_backtest/data/tushare/assemble.py)

先判断：

- 这个条件依赖现有元数据吗
- 如果不依赖，是否需要先扩展数据层

### 5.3 新增一个因子

常见落点：

- [base.py](../src/quant_factor_backtest/factors/base.py)
- [builtin.py](../src/quant_factor_backtest/factors/builtin.py)
- 如需新数据，还会回到数据层

建议：

- 先写测试
- 再决定因子是直接吃 `MarketData`，还是通过 `data_client` 取原始字段

### 5.4 修改回测指标口径

常见落点：

- [engine.py](../src/quant_factor_backtest/backtest/engine.py)
- [constants/backtest.py](../src/quant_factor_backtest/constants/backtest.py)
- [STRATEGY.md](STRATEGY.md)

如果你改了指标逻辑，文档和测试通常应该一起改。

## 6. 开发工作流建议

### 6.1 先让测试表达预期

当前项目的节奏更适合：

1. 先补或修改测试
2. 再改实现
3. 最后看文档是否需要同步

这能减少“感觉改对了，但不知道有没有悄悄破坏旧行为”的风险。

### 6.2 优先保持边界清晰

改代码时优先守住下面这几个边界：

- 数据源细节不要泄漏到研究层
- 策略说明不要塞进实现细节文档
- 单个模块不要同时承担 fetch / cache / assemble / convert 多个职责

### 6.3 小步提交

如果一个改动同时涉及：

- 数据字段
- 领域对象
- 因子逻辑
- 文档说明

尽量把它拆成几个可理解的小步，而不是一次性大改所有文件。

## 7. 代码书写规范

### 7.1 命名优先表达语义，不优先追求短

优先这种：

- `daily_records_by_date`
- `adjustment_records_by_date`
- `records_grouped_by_trade_date`

而不是这种：

- `df2`
- `x`
- `tmp`

### 7.2 注释解释“为什么”，不要解释显而易见的“做什么”

好的注释应该解释：

- 为什么要做这一步适配
- 为什么这里要保留旧行为
- 为什么这个默认值有意义

而不是把代码直译一遍。

### 7.3 高频协议字段优先提成常量

例如：

- endpoint 名
- API 参数名
- 表字段名
- 指标 key

但不要为了“统一”把所有局部 `0.0` 都强行抽成常量。

### 7.4 代码即文档

如果命名已经足够清楚，优先改命名；
只有在命名仍无法表达意图时，再补注释。

## 8. 文档书写规范

### 8.1 先分清文档类型

- `README.md`
  面向安装和使用
- `ARCHITECTURE.md`
  面向模块设计和边界
- `DATA_FLOW.md`
  面向函数级调用链
- `STRATEGY.md`
  面向策略逻辑和指标公式
- `WIKI.md`
  面向新开发者上手与协作

不要把不同目的的内容混写到同一份文档里。

### 8.2 文档更新要跟代码变更同步

下面几类改动通常应该同步更新文档：

- 目录结构变化
- 核心数据流变化
- 指标口径变化
- 默认参数变化
- 对外使用方式变化

### 8.3 优先写“帮助别人少读源码”的文档

好的项目文档不是把代码再说一遍，而是提前回答读者最容易卡住的问题。

## 9. 推荐命令

安装：

```powershell
pip install -e .
pip install -e .[data]
```

运行测试：

```powershell
$env:PYTHONPATH='src'
python -m pytest
```

运行示例：

```powershell
$env:PYTHONPATH='src'
python examples/minimal_run.py
```

```powershell
$env:TUSHARE_TOKEN='your-token'
$env:PYTHONPATH='src'
python examples/tushare_run.py
```

## 10. 新开发者第一周最值得做的事

如果你刚接手项目，我建议按这个顺序熟悉：

1. 跑通测试
2. 跑通最小示例
3. 阅读 `domain -> pipeline -> engine`
4. 阅读 `client -> assemble -> convert`
5. 随手修一个很小的文档或命名问题
6. 再开始动功能

这样会比一上来直接改数据层或策略逻辑稳很多。
