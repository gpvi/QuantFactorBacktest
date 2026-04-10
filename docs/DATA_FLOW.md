# QuantFactorBacktest Data Flow

## 1. 文档目标

这份文档专门描述当前项目的数据流，粒度下沉到函数级别。

适合用于：

- 快速定位“某份数据是在哪个函数被拿到的”
- 理解 `raw records -> polars table -> domain object` 的转换边界
- 排查缓存、复权、股票池元数据、因子信号的来源
- 后续重构 `research / portfolio / backtest` 时对照当前链路

如果要看分层设计，请读 [ARCHITECTURE.md](/E:/Projects/QuantFactorBacktest/docs/ARCHITECTURE.md)。

## 2. 数据层主链路

当前 `Tushare` 数据层按下面 4 个模块协作：

- [fetch.py](/E:/Projects/QuantFactorBacktest/src/quant_factor_backtest/data/tushare/fetch.py)
  负责访问外部 API，返回原始 `records`
- [client.py](/E:/Projects/QuantFactorBacktest/src/quant_factor_backtest/data/tushare/client.py)
  负责缓存与编排
- [assemble.py](/E:/Projects/QuantFactorBacktest/src/quant_factor_backtest/data/tushare/assemble.py)
  负责把原始 `records` 组装成 `polars.DataFrame`
- [convert.py](/E:/Projects/QuantFactorBacktest/src/quant_factor_backtest/data/tushare/convert.py)
  负责把中间表转换成 `MarketData` / `FactorSignal`

统一的数据形态如下：

1. `fetch.py`
   输出 `RawRecords`
2. `client.py`
   负责 `cache hit / miss` 和按日期聚合
3. `assemble.py`
   输出 `pl.DataFrame`
4. `convert.py`
   输出领域对象

## 3. 函数级数据流

### 3.1 行情数据 `fetch_market_data`

入口函数：

- [TushareDataClient.fetch_market_data()](/E:/Projects/QuantFactorBacktest/src/quant_factor_backtest/data/tushare/client.py)

调用顺序：

1. `fetch_market_data(trade_dates, ts_codes)`
2. `_load_or_fetch_by_trade_dates(endpoint="daily", ...)`
3. `_load_adj_factor_by_trade_dates(...)`
4. `build_price_table(...)`
5. `price_table_to_market_data(...)`
6. 返回 `MarketData`

函数职责拆解：

- `_load_or_fetch_by_trade_dates(...)`
  按 `trade_date` 逐天查缓存，缺失的日期进入批量抓取流程

- `_load_adj_factor_by_trade_dates(...)`
  当 `config.adj` 为真时，加载 `adj_factor`；否则直接返回空映射

- `build_price_table(...)`
  把：
  - `daily_rows_by_date`
  - `adj_rows_by_date`

  组装成带以下列的表：
  - `trade_date`
  - `ts_code`
  - `close`
  - `price`
  - 可选 `adj_factor`

- `price_table_to_market_data(...)`
  把 `price` 列转换成：
  - `MarketData.prices[trade_date][ts_code]`

最终数据路径：

`daily / adj_factor records -> price_table -> MarketData.prices`

### 3.2 带股票池元数据的行情 `fetch_market_data_with_universe_metadata`

入口函数：

- [TushareDataClient.fetch_market_data_with_universe_metadata()](/E:/Projects/QuantFactorBacktest/src/quant_factor_backtest/data/tushare/client.py)

调用顺序：

1. `fetch_market_data_with_universe_metadata(trade_dates, ts_codes)`
2. `_load_or_fetch(endpoint="stock_basic", trade_date="all", ...)`
3. `_load_or_fetch_by_trade_dates(endpoint="daily", ...)`
4. `_load_adj_factor_by_trade_dates(...)`
5. `_load_or_fetch_by_trade_dates(endpoint="suspend_d", ...)`
6. `_load_or_fetch_by_trade_dates(endpoint="stk_limit", ...)`
7. `build_universe_table(...)`
8. `universe_table_to_market_data(...)`
9. 返回 `MarketData`

函数职责拆解：

- `_load_or_fetch(endpoint="stock_basic", ...)`
  加载静态股票基础信息：
  - `ts_code`
  - `name`
  - `list_date`

- `build_universe_table(...)`
  先内部调用 `build_price_table(...)` 形成价格主表，再补齐：
  - `amount`
  - `name`
  - `list_date`
  - `is_suspended`
  - `up_limit`
  - `down_limit`
  - `is_st`
  - `listed_days`
  - `is_limit_up`
  - `is_limit_down`

- `universe_table_to_market_data(...)`
  将中间表拆成：
  - `prices`
  - `is_st`
  - `is_suspended`
  - `listed_days`
  - `is_limit_up`
  - `is_limit_down`
  - `turnover_amount`

最终数据路径：

`daily / adj_factor / stock_basic / suspend_d / stk_limit -> universe_table -> MarketData`

### 3.3 `daily_basic` 原始字段 `fetch_daily_basic`

入口函数：

- [TushareDataClient.fetch_daily_basic()](/E:/Projects/QuantFactorBacktest/src/quant_factor_backtest/data/tushare/client.py)

调用顺序：

1. `fetch_daily_basic(trade_date, fields)`
2. `_load_or_fetch(endpoint="daily_basic", ...)`
3. 返回 `RawRecords`

这个函数不经过 `assemble.py` 和 `convert.py`，因为它的目标是直接暴露原始 `daily_basic` 结果。

### 3.4 单字段因子信号 `fetch_factor_signal`

入口函数：

- [TushareDataClient.fetch_factor_signal()](/E:/Projects/QuantFactorBacktest/src/quant_factor_backtest/data/tushare/client.py)

调用顺序：

1. `fetch_factor_signal(trade_dates, field, factor_name)`
2. `_load_or_fetch_by_trade_dates(endpoint="daily_basic", ...)`
3. `build_factor_table(trade_dates, records_by_date, field)`
4. `factor_table_to_signal(...)`
5. 返回 `FactorSignal`

函数职责拆解：

- `build_factor_table(...)`
  从 `daily_basic` 原始记录中抽取：
  - `trade_date`
  - `ts_code`
  - `value`

- `factor_table_to_signal(...)`
  将 `value` 列转成：
  - `FactorSignal.values[trade_date][ts_code]`

最终数据路径：

`daily_basic records -> factor_table -> FactorSignal`

## 4. 缓存流

缓存编排全部发生在 [client.py](/E:/Projects/QuantFactorBacktest/src/quant_factor_backtest/data/tushare/client.py)。

### 4.1 单次查询 `_load_or_fetch`

调用顺序：

1. `_cache_key(...)`
2. `self._cache.get(cache_key)`
3. 未命中时：
   - `self._fetcher.fetch_records(...)`
   - `self._cache.set(cache_key, records)`

职责：

- 优先读 SQLite
- 未命中时访问 Tushare
- 将原始 `records` 回写缓存

### 4.2 多交易日查询 `_load_or_fetch_by_trade_dates`

调用顺序：

1. 对每个 `trade_date` 计算 `_cache_key(...)`
2. 对每个日期尝试 `self._cache.get(...)`
3. 将缺失日期汇总到 `missing_dates`
4. `_fetch_records_by_trade_dates(...)`
5. 将抓回的结果按日期写回缓存

职责：

- 复用逐日缓存键
- 避免整段区间只要一个日期 miss 就整体重拉

### 4.3 区间抓取 `_fetch_records_by_trade_dates`

调用顺序：

1. 若只有一个日期：
   - `self._fetcher.fetch_records(...)`
2. 若有多个日期：
   - 优先 `self._fetcher.fetch_records_in_range(...)`
3. 若区间 API 不支持：
   - fallback 到逐日 `fetch_records(...)`
4. 将结果重新 `group by trade_date`

职责：

- 在“批量抓取效率”和“接口兼容性”之间做平衡

## 5. Fetch 层函数

路径：[fetch.py](/E:/Projects/QuantFactorBacktest/src/quant_factor_backtest/data/tushare/fetch.py)

### 5.1 `TushareFetcher.fetch_records`

职责：

- 将业务参数转换成单日 Tushare API 参数
- 调用 `getattr(pro, endpoint)(**params)`
- 输出 `RawRecords`

### 5.2 `TushareFetcher.fetch_records_in_range`

职责：

- 将参数转换成 `start_date / end_date` 形式
- 调用区间版 Tushare API
- 输出 `RawRecords`

### 5.3 `TushareFetcher._pro_api`

职责：

- 初始化 `tushare`
- 设置 token
- 延迟创建 `pro_api()` client

### 5.4 `TushareFetcher.frame_to_records`

职责：

- 将 DataFrame-like 结果统一转换成 `list[dict]`
- 这是外部数据进入项目的第一个标准化入口

## 6. Assemble 层函数

路径：[assemble.py](/E:/Projects/QuantFactorBacktest/src/quant_factor_backtest/data/tushare/assemble.py)

### 6.1 `build_price_table`

输入：

- `trade_dates`
- `daily_rows_by_date`
- `adj_rows_by_date`
- `use_adj`

输出：

- `pl.DataFrame`

关键处理：

- 扁平化 `daily_rows_by_date`
- 构造 `daily_df`
- 若开启复权且有 `adj_factor`：
  - 按 `trade_date, ts_code` left join
  - 计算 `price = close * adj_factor`
- 否则：
  - `price = close`

### 6.2 `build_universe_table`

输入：

- `daily_rows_by_date`
- `adj_rows_by_date`
- `suspend_rows_by_date`
- `limit_rows_by_date`
- `stock_basic_records`

输出：

- `pl.DataFrame`

关键处理：

1. 调 `build_price_table(...)`
2. 补 `amount`
3. 补 `name / list_date`
4. 补 `is_suspended`
5. 补 `up_limit / down_limit`
6. 衍生：
   - `is_st`
   - `listed_days`
   - `is_limit_up`
   - `is_limit_down`

### 6.3 `build_factor_table`

输入：

- `trade_dates`
- `records_by_date`
- `field`

输出：

- `pl.DataFrame`

关键处理：

- 只保留：
  - `trade_date`
  - `ts_code`
  - `value`
- 过滤掉 `field is None` 的记录

### 6.4 `_days_since_listing`

职责：

- 以 `trade_date - list_date` 计算上市天数
- 仅被 `build_universe_table(...)` 调用

## 7. Convert 层函数

路径：[convert.py](/E:/Projects/QuantFactorBacktest/src/quant_factor_backtest/data/tushare/convert.py)

### 7.1 `price_table_to_market_data`

职责：

- 读取 `price` 列
- 调 `_frame_to_float_matrix(...)`
- 生成仅含 `prices` 的 `MarketData`

### 7.2 `universe_table_to_market_data`

职责：

- 从中间表分别提取：
  - `price`
  - `is_st`
  - `is_suspended`
  - `listed_days`
  - `is_limit_up`
  - `is_limit_down`
  - `amount`
- 拼成完整 `MarketData`

### 7.3 `factor_table_to_signal`

职责：

- 读取 `value` 列
- 调 `_frame_to_float_matrix(...)`
- 生成 `FactorSignal`

### 7.4 `market_data_to_table`

职责：

- 将 `MarketData` 重新扁平化为 `pl.DataFrame`
- 当前主要供 `UniverseFilter` 使用

这一步是当前项目里一个重要的“反向适配”点：

`MarketData(dict) -> pl.DataFrame`

它说明研究主链路尚未完全列式化。

### 7.5 `filtered_market_data_from_frame`

职责：

- 将过滤后的 DataFrame 再转回 `MarketData`
- 按参数决定是否保留：
  - `is_st`
  - `is_suspended`
  - `listed_days`
  - `is_limit_up`
  - `is_limit_down`
  - `turnover_amount`

这一步是另一个关键“反向适配”点：

`pl.DataFrame -> MarketData(dict)`

### 7.6 `_frame_to_bool_matrix / _frame_to_int_matrix / _frame_to_float_matrix`

职责：

- 把长表按：
  - `trade_date`
  - `asset` 或 `ts_code`

恢复成：

- `dict[trade_date][asset]`

这是当前数据层与领域层的主要转换边界。

## 8. 股票池过滤数据流

入口函数：

- [UniverseFilter.apply()](/E:/Projects/QuantFactorBacktest/src/quant_factor_backtest/universe/filters.py)

调用顺序：

1. `market_data_to_table(market_data)`
2. 逐项构造 `polars` 过滤表达式
3. `filtered_frame = filtered_frame.filter(...)`
4. `filtered_market_data_from_frame(...)`
5. 返回 `FilteredMarketContext`

数据路径：

`MarketData(dict) -> DataFrame -> filter -> MarketData(dict)`

这也是当前项目最明显的中间过渡形态。

## 9. 研究主链路数据流

当前研究主链路还主要是 `dict` 语义。

### 9.1 `ResearchPipeline.run`

主流程：

1. 数据层获取 `MarketData`
2. `UniverseFilter.apply(...)`
3. 每个因子执行 `compute(...)`
4. `CompositeFactorModel` 做标准化和合成
5. 组合构建
6. 回测执行

### 9.2 当前转换边界

当前项目里最重要的边界是：

1. 数据接入前半段：
   `RawRecords -> DataFrame`
2. 数据接入后半段：
   `DataFrame -> MarketData / FactorSignal`
3. 股票池过滤：
   `MarketData -> DataFrame -> MarketData`
4. 研究、组合、回测：
   仍然主要使用 `dict`

这也是后续继续重构时最优先的观察点。

## 10. 当前最值得继续优化的位置

如果以后继续推进重构，优先顺序建议是：

1. `research/pipeline.py`
   将 `z-score` 和多因子合成迁到 `polars`
2. `portfolio/construction.py`
   将排序选股迁到列式实现
3. `backtest/engine.py`
   最后再考虑列式化

原因是：

- 现在 `data` 和 `universe` 已经基本收拢
- 研究主链路才是后续性能和结构统一的关键
