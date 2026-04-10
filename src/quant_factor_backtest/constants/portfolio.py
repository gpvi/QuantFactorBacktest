from __future__ import annotations

# 组合构建层使用的调仓频率枚举值。
# daily 表示每个可用交易日都允许调仓。
REBALANCE_FREQUENCY_DAILY = "daily"

# monthly 表示每个月只取第一个可用交易日作为调仓日。
REBALANCE_FREQUENCY_MONTHLY = "monthly"

# 默认选股比例。
# 例如 0.2 表示每个调仓日选取评分前 20% 的股票进入组合。
DEFAULT_TOP_PERCENT = 0.2
