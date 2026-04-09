# QuantFactorBacktest Architecture

## 1. 文档目标

这份文档用于解释当前框架的：

- 整体架构分层
- 核心数据流
- 关键模块职责
- 当前已经做过的优化点
- 设计重点与取舍
- 后续优先优化方向

它不是用户入门文档，而是面向后续开发、维护和扩展的工程说明。
如果要看策略逻辑、指标公式和优缺点分析，见 [STRATEGY.md](/E:/Projects/QuantFactorBacktest/docs/STRATEGY.md)。

## 2. 当前框架定位

当前项目是一个多因子研究 + 回测验证原型框架，目标不是一步做到生产级，而是先建立一条清晰、可测试、可扩展的研究主链路：

`数据接入 -> 股票池过滤 -> 因子计算 -> 因子标准化 -> 多因子合成 -> 组合构建 -> 回测执行 -> 绩效评估`

当前已经支持：

- `Tushare` 数据接入
- 基于环境变量读取 `TUSHARE_TOKEN`
- 本地缓存，减少重复 API 调用
- 股票池过滤
- 多因子横截面 `z-score`
- 因子加权合成
- 前 `20%` 选股
- 等权持仓
- 月度调仓
- 交易成本和滑点
- 常用绩效指标
- 基于 `unittest` 的测试驱动开发

## 3. 总体分层

### 3.1 `domain`

路径：[domain.py](/E:/Projects/QuantFactorBacktest/src/quant_factor_backtest/domain.py)

这一层定义框架内部的核心对象，是所有模块之间的统一语言。

当前核心对象：

- `MarketData`
  包含价格矩阵，以及可选的交易状态/股票池元数据：
  `is_st`、`is_suspended`、`listed_days`、`is_limit_up`、`is_limit_down`、`turnover_amount`
- `FactorSignal`
  表示因子输出的时间序列横截面矩阵
- `PortfolioWeights`
  表示目标组合权重

设计重点：

- 上层模块不直接依赖 `Tushare` 原始返回结构
- 数据源差异先在接入层消化，再转成统一领域对象
- 后续接 CSV、Parquet、数据库时，研究和回测层可以保持不变

### 3.2 `data`

路径：[tushare.py](/E:/Projects/QuantFactorBacktest/src/quant_factor_backtest/data/tushare.py)

这一层负责外部数据源接入和转换。

当前实现：

- `TushareConfig`
  管理 token、复权方式、缓存目录
- `TushareDataClient`
  负责：
  拉取价格
  拉取 `daily_basic`
  生成因子信号
  生成股票池过滤所需元数据
  做本地 JSON 缓存

设计重点：

- `Tushare` 依赖只留在数据层
- 对上层暴露的是 `MarketData` 和 `FactorSignal`
- API 结果可缓存，避免研究迭代时被限额和延迟拖慢

### 3.3 `universe`

路径：[filters.py](/E:/Projects/QuantFactorBacktest/src/quant_factor_backtest/universe/filters.py)

这一层负责股票池过滤。

当前支持：

- 最低价格过滤
- 手工排除指定股票
- `ST` 过滤
- 停牌过滤
- 上市天数过滤
- 涨停过滤
- 跌停过滤
- 最低成交额过滤

设计重点：

- 股票池过滤独立于因子层
- 先过滤可投资标的，再进行因子合成和组合构建
- 避免“先打分再过滤”导致横截面统计失真

### 3.4 `factors`

路径：[builtin.py](/E:/Projects/QuantFactorBacktest/src/quant_factor_backtest/factors/builtin.py)

这一层负责具体因子定义。

当前实现：

- `MomentumFactor`
  基于价格序列计算简单动量
- `StaticDataFactor`
  用于测试和手工注入因子值
- `DailyBasicFieldFactor`
  把 `Tushare daily_basic` 字段直接转换成真实因子

设计重点：

- 因子通过统一 `compute()` 接口接入
- 研究流水线不关心因子来自价格、财务字段还是外部处理结果
- 便于后续增加估值、质量、成长、波动率、行业哑变量等因子

### 3.5 `research`

路径：[pipeline.py](/E:/Projects/QuantFactorBacktest/src/quant_factor_backtest/research/pipeline.py)

这一层负责研究编排，是主链路核心。

当前流程：

1. 接收 `MarketData`
2. 执行股票池过滤
3. 计算每个因子
4. 对每个因子做横截面 `z-score`
5. 按权重加权合成综合评分
6. 交给组合构建层生成目标权重
7. 交给回测引擎执行

核心类：

- `CompositeFactorModel`
- `ResearchPipeline`

设计重点：

- 把研究流程集中在一处，避免业务逻辑散落
- 保持“研究层”只负责研究，不直接承担数据抓取或交易执行细节
- 过滤、因子、组合、回测四块通过明确接口串联

### 3.6 `portfolio`

路径：[construction.py](/E:/Projects/QuantFactorBacktest/src/quant_factor_backtest/portfolio/construction.py)

这一层负责把综合评分映射成目标组合。

当前实现：

- `TopNPercentLongOnlyConstructor`
  取评分前 `20%` 股票
  等权持仓
  支持 `daily` 和 `monthly` 调仓

设计重点：

- 组合构建逻辑独立于因子和回测
- 后续可以在这一层扩展：
  分层持仓
  多空组合
  行业中性
  风险预算
  约束优化

### 3.7 `backtest`

路径：[engine.py](/E:/Projects/QuantFactorBacktest/src/quant_factor_backtest/backtest/engine.py)

这一层负责根据权重和价格执行回测并输出结果。

当前实现：

- 按当前时点权重持有到下一时点
- 支持换手率计算
- 支持交易成本与滑点
- 输出绩效指标：
  年化收益率
  年化波动率
  夏普比率
  最大回撤
  胜率
  换手率

设计重点：

- 先实现简单、可验证的回测引擎
- 交易成本和滑点先通过换手率统一扣减
- 为后续加入更真实的执行约束保留空间

## 4. 核心数据流

当前主链路如下：

1. `TushareDataClient` 拉取价格和股票池元数据
2. 转为 `MarketData`
3. `UniverseFilter` 过滤不可投资标的
4. 各 `Factor` 生成 `FactorSignal`
5. `CompositeFactorModel` 做 `z-score + weighted sum`
6. `TopNPercentLongOnlyConstructor` 生成 `PortfolioWeights`
7. `BacktestEngine` 执行回测
8. 输出 `BacktestResult`

这个数据流的核心原则是：

- 数据源适配和研究逻辑分离
- 股票池过滤和因子计算分离
- 因子研究和组合构建分离
- 组合构建和回测执行分离

## 5. 当前已经做过的优化点

### 5.1 用统一领域对象隔离外部数据源

优化点：

- 没有让 `Tushare` 的 DataFrame 和字段结构直接渗透到整个框架

价值：

- 降低耦合
- 更容易接入第二数据源
- 测试可以使用纯 Python 字典而不是依赖外部服务

### 5.2 数据层加入本地缓存

优化点：

- `TushareDataClient` 对请求结果按查询条件落本地 JSON

价值：

- 避免重复 API 请求
- 降低回测迭代时的等待时间
- 避免 `Tushare` 调用次数成为瓶颈

### 5.3 股票池过滤前置

优化点：

- 先过滤，再做因子标准化和因子合成

价值：

- 更符合真实研究逻辑
- 避免不可投资股票进入横截面分布
- 减少评分污染

### 5.4 因子标准化统一放到研究层

优化点：

- `z-score` 标准化不在单个因子里重复实现，而在合成前统一处理

价值：

- 单因子职责更单一
- 多因子比较口径一致
- 更便于后续替换成 winsorize + standardize + neutralize 流水线

### 5.5 交易成本和滑点显式进入回测引擎

优化点：

- 成本和滑点不是事后附加计算，而是在回测收益里直接扣减

价值：

- 回测结果更接近真实
- 换手率与收益之间的关系可追踪
- 后续接更精细的执行模型更自然

### 5.6 TDD 驱动实现

优化点：

- 每次扩展功能，先补测试再补实现

价值：

- 让行为边界更清晰
- 降低连续重构时的回归风险
- 对当前这种逐步搭骨架的项目尤其重要

## 6. 当前设计重点

当前设计最重要的不是“功能多”，而是下面几点。

### 6.1 分层边界清晰

现在每一层职责都比较清楚：

- 数据层负责拿数据和转格式
- 股票池层负责过滤
- 因子层负责生成信号
- 研究层负责标准化和合成
- 组合层负责把评分变成权重
- 回测层负责收益和指标

这决定了后续扩展时不会牵一发动全身。

### 6.2 先跑通闭环，再补真实性

当前很多地方仍然是“简化版”，例如：

- 回测执行还不是订单级
- 滑点还是线性模型
- 因子预处理还没有去极值和中性化

这是刻意选择，不是遗漏。当前阶段的重点是：

- 先跑通
- 先能测
- 先能迭代

### 6.3 真实 A 股约束开始进入研究主链路

目前已经把下列约束纳入股票池过滤：

- `ST`
- 停牌
- 上市天数
- 涨跌停
- 流动性

这意味着框架已经从“纯示意性研究”向“更接近实盘约束的研究”迈了一步。

## 7. 当前局限

当前仍然有一些明确限制。

### 7.1 因子预处理还不完整

目前只有 `z-score`，没有：

- 去极值
- 缺失值处理
- 行业中性化
- 市值中性化

### 7.2 回测执行仍然比较粗

目前还没有：

- 订单级撮合
- 买卖方向分开成本
- 调仓日不可买、持仓日可卖等执行逻辑
- 停牌跨期持仓处理细节

### 7.3 数据层目前仍以 `Tushare` 为主

虽然框架分层已准备好，但现在真正接通的外部数据源只有 `Tushare`。

### 7.4 结果分析能力还弱

当前有基础绩效指标，但还没有：

- IC / RankIC
- 分层收益
- 风格暴露
- 行业暴露
- 因子相关性分析
- 实验结果归档

## 8. 后续优先优化方向

### 8.1 优先级最高

1. 因子预处理流水线
   增加去极值、缺失值处理、中性化

2. 更真实的执行约束
   区分买入限制和卖出限制
   处理停牌与涨跌停下的调仓失败

3. 本地数据存储升级
   从 JSON 缓存升级到 CSV/Parquet
   便于批量回测和更大样本

### 8.2 第二优先级

1. 因子研究分析模块
   加 IC、RankIC、分层回测

2. 组合构建升级
   加行业中性、风险约束、多空组合

3. 实验管理
   保存参数、结果、运行时间、版本信息

## 9. 推荐阅读顺序

如果新开发者要快速理解这个项目，建议按下面顺序看代码：

1. [domain.py](/E:/Projects/QuantFactorBacktest/src/quant_factor_backtest/domain.py)
2. [pipeline.py](/E:/Projects/QuantFactorBacktest/src/quant_factor_backtest/research/pipeline.py)
3. [construction.py](/E:/Projects/QuantFactorBacktest/src/quant_factor_backtest/portfolio/construction.py)
4. [engine.py](/E:/Projects/QuantFactorBacktest/src/quant_factor_backtest/backtest/engine.py)
5. [filters.py](/E:/Projects/QuantFactorBacktest/src/quant_factor_backtest/universe/filters.py)
6. [tushare.py](/E:/Projects/QuantFactorBacktest/src/quant_factor_backtest/data/tushare.py)
7. [tests](/E:/Projects/QuantFactorBacktest/tests)

## 10. 总结

当前架构的核心价值不在于它已经“完整”，而在于它已经具备了正确的演进方向：

- 有清晰分层
- 有统一数据对象
- 有研究主链路
- 有真实约束入口
- 有测试保护
- 有继续扩展到更完整量化平台的空间

如果把这个项目继续往前推，最应该守住的重点有三个：

- 不要破坏分层边界
- 不要把数据源细节泄漏到研究层
- 每次扩展都继续维持测试先行
