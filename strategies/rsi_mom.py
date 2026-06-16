"""
RSI动量稳健 v2
优化点：
1. 修复 Wilder 平滑 EMA 方式（原用 SMA 均值，标准 RSI 应用指数平滑）
2. 增加趋势过滤：MA20 向上确认动量方向
3. 增加数据长度保护，防止 NaN 误判
4. 支持参数配置
"""

RSI_PERIOD   = 14
RSI_LOW      = 52   # 原50，略抬以减少假信号
RSI_HIGH     = 68   # 原70，留出顶部缓冲
MA_PERIOD    = 20

def get_name():
    return "RSI动量稳健"

def run(df) -> bool:
    if len(df) < RSI_PERIOD + MA_PERIOD + 5:
        return False

    close = df["close"]

    # ── 标准 Wilder RSI（指数平滑）──────────────────────────────
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/RSI_PERIOD, min_periods=RSI_PERIOD, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/RSI_PERIOD, min_periods=RSI_PERIOD, adjust=False).mean()
    rs  = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))

    rsi_now = rsi.iloc[-1]
    if not (RSI_LOW < rsi_now < RSI_HIGH):
        return False

    # ── 趋势过滤：MA20 向上倾斜 ──────────────────────────────────
    ma20 = close.rolling(MA_PERIOD).mean()
    if ma20.iloc[-1] <= ma20.iloc[-3]:   # 3根K线斜率确认
        return False

    return True
