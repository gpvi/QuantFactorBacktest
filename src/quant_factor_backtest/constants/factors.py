from __future__ import annotations

# 综合因子输出的默认名称。
# 当前由 CompositeFactorModel.combine() 使用，作为多因子加权后的最终信号名。
# 如果以后研究层支持多种合成器，这个常量可以继续作为“默认综合分数”名称保留。
COMPOSITE_FACTOR_NAME = "composite"

# 动量因子的默认名称。
# 当前由 MomentumFactor 使用，主要影响：
# 1. 研究输出里因子的名字
# 2. 多因子权重字典里引用该因子时的 key
# 3. 调试或日志中对该因子的识别
MOMENTUM_FACTOR_NAME = "momentum"
