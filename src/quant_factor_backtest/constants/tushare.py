from __future__ import annotations

# 本地 SQLite 缓存文件名。
# TushareDataClient._default_cache_backend() 会把它拼到 cache_dir 下，
# 最终形成类似 .cache/tushare/cache.sqlite3 的路径。
CACHE_FILENAME = "cache.sqlite3"

# Tushare 数据层默认缓存目录。
# 当用户没有显式传入 cache_dir 时，TushareConfig 默认使用该目录。
DEFAULT_CACHE_DIRECTORY = ".cache/tushare"

# 默认复权模式。
# 当前项目里 truthy 即表示需要加载 adj_factor 并生成复权价格。
# 这里保留字符串值，是为了以后如果要区分 qfq/hfq 等模式时还有扩展空间。
DEFAULT_ADJUSTMENT_MODE = "qfq"

# 默认读取 token 的环境变量名。
# TushareConfig.from_env() 会优先从这个环境变量中取 token。
DEFAULT_TOKEN_ENV_VAR = "TUSHARE_TOKEN"

# 在缓存 key 中表达“全量查询”的占位值。
# 例如没有传 ts_codes 时，会把 code_key 记成 all，避免生成空串造成歧义。
QUERY_SCOPE_ALL = "all"

# Tushare 复权因子接口名。
# 用于获取 ts_code / trade_date 对应的 adj_factor。
ENDPOINT_ADJ_FACTOR = "adj_factor"

# Tushare 日线行情接口名。
# 当前项目主要从这里获取收盘价和成交额。
ENDPOINT_DAILY = "daily"

# Tushare 日度基础指标接口名。
# 当前用于估值、市值等横截面因子来源。
ENDPOINT_DAILY_BASIC = "daily_basic"

# Tushare 涨跌停价接口名。
# 当前用于构造 is_limit_up / is_limit_down。
ENDPOINT_STK_LIMIT = "stk_limit"

# Tushare 股票基础信息接口名。
# 当前用于获取股票名称和上市日期。
ENDPOINT_STOCK_BASIC = "stock_basic"

# Tushare 停牌信息接口名。
# 当前用于构造 is_suspended。
ENDPOINT_SUSPEND_D = "suspend_d"

# 支持传入 trade_date 的 endpoint 集合。
# fetch_records() 会根据这个集合决定是否把 trade_date 放进请求参数。
TRADE_DATE_PARAM_ENDPOINTS = {
    ENDPOINT_DAILY,
    ENDPOINT_ADJ_FACTOR,
    ENDPOINT_DAILY_BASIC,
    ENDPOINT_SUSPEND_D,
    ENDPOINT_STK_LIMIT,
}

# 支持传入 ts_code 的 endpoint 集合。
# 不是所有接口都支持 ts_code 过滤，所以这里集中维护能力边界，
# 避免在 fetcher 里写多处重复判断。
TS_CODE_PARAM_ENDPOINTS = {
    ENDPOINT_DAILY,
    ENDPOINT_ADJ_FACTOR,
    ENDPOINT_STK_LIMIT,
}

# Tushare 区间查询的结束日期参数名。
PARAM_END_DATE = "end_date"

# stock_basic 使用的 exchange 参数名。
PARAM_EXCHANGE = "exchange"

# Tushare 普遍使用的 fields 参数名。
# 当前所有 fetch_records / fetch_records_in_range 请求都会带上它。
PARAM_FIELDS = "fields"

# stock_basic 使用的上市状态参数名。
PARAM_LIST_STATUS = "list_status"

# Tushare 区间查询的开始日期参数名。
PARAM_START_DATE = "start_date"

# 单日查询的交易日参数名。
PARAM_TRADE_DATE = "trade_date"

# 股票代码过滤参数名。
PARAM_TS_CODE = "ts_code"

# stock_basic 中表示“已上市”的 list_status 值。
# 当前只拉取仍处于上市状态的股票。
STOCK_BASIC_LIST_STATUS_LISTED = "L"

# 复权因子列名。
# 出现在 adj_factor records 和 build_price_table() 的 join 结果中。
COLUMN_ADJ_FACTOR = "adj_factor"

# 成交额列名。
# daily 接口和 universe_table / MarketData.turnover_amount 都会使用它。
COLUMN_AMOUNT = "amount"

# 领域适配阶段使用的资产代码列名。
# 当数据从 MarketData 重新转成 DataFrame 时，会使用 asset 而不是 ts_code。
COLUMN_ASSET = "asset"

# 收盘价列名。
# 是 build_price_table() 里生成复权价格前的原始价格来源。
COLUMN_CLOSE = "close"

# 跌停价列名。
COLUMN_DOWN_LIMIT = "down_limit"

# 跌停标记列名。
# 由 build_universe_table() 派生得到。
COLUMN_IS_LIMIT_DOWN = "is_limit_down"

# 涨停标记列名。
COLUMN_IS_LIMIT_UP = "is_limit_up"

# ST 标记列名。
# 当前通过股票名称里是否包含 ST 派生。
COLUMN_IS_ST = "is_st"

# 停牌标记列名。
COLUMN_IS_SUSPENDED = "is_suspended"

# 上市日期列名。
COLUMN_LIST_DATE = "list_date"

# 上市天数列名。
# 当前通过 trade_date - list_date 计算得到。
COLUMN_LISTED_DAYS = "listed_days"

# 股票名称列名。
COLUMN_NAME = "name"

# 最终用于研究和回测的价格列名。
# 不论是否复权，后续统一都从 price 这一列读取价格。
COLUMN_PRICE = "price"

# 交易日列名。
# 贯穿 raw records、polars table 和 dict matrix 转换。
COLUMN_TRADE_DATE = "trade_date"

# Tushare 原始股票代码列名。
COLUMN_TS_CODE = "ts_code"

# 成交额元数据在 MarketData / UniverseFilter 中使用的列名。
# 注意它和 raw daily 的 amount 在语义上相关，但主要用于过滤层。
COLUMN_TURNOVER_AMOUNT = "turnover_amount"

# 涨停价列名。
COLUMN_UP_LIMIT = "up_limit"

# 因子值列名。
# build_factor_table() 和 factor_table_to_signal() 都使用这个统一名称。
COLUMN_VALUE = "value"

# 拉取价格所用的默认字段集合。
# 当前最常见的数据接入场景需要：
# - ts_code
# - trade_date
# - close
# - amount
DAILY_PRICE_FIELDS = "ts_code,trade_date,close,amount"

# 拉取 daily_basic 时的默认字段集合。
# 主要覆盖估值和市值类因子原型。
DAILY_BASIC_DEFAULT_FIELDS = "ts_code,trade_date,pe,pb,total_mv"

# 拉取 stock_basic 时的默认字段集合。
# 当前只取股票代码、名称和上市日期，避免引入过多暂时不用的字段。
STOCK_BASIC_FIELDS = "ts_code,name,list_date"

# 拉取 adj_factor 时的默认字段集合。
ADJ_FACTOR_FIELDS = "ts_code,trade_date,adj_factor"

# 拉取 suspend_d 时的默认字段集合。
SUSPEND_D_FIELDS = "ts_code,trade_date,suspend_type"

# 拉取 stk_limit 时的默认字段集合。
STK_LIMIT_FIELDS = "ts_code,trade_date,up_limit,down_limit"
