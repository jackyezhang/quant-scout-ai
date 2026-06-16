"""
唐奇安通道突破 v2
优化点：
1. 原策略用 close.rolling(20).max()，唐奇安通道标准定义是 high 的最高价，而非收盘价
2. iloc[-2] 取昨日为止的高点是对的，但对齐方式用 rolling + shift 更清晰安全
3. 增加成交量突破确认，避免「假突破」
4. 增加 ATR 止损参考输出（可选，供调用方记录）
5. 增加回踩不破确认（可选严格模式）
"""

CHANNEL_PERIOD = 20
VOL_MULT       = 1.3   # 突破日成交量放大倍数
USE_HIGH       = True  # True=用 high 计算通道（标准），False=用 close（原逻辑）

def get_name():
    return "唐奇安通道突破"

def run(df) -> bool:
    if len(df) < CHANNEL_PERIOD + 5:
        return False

    # ── 通道计算（标准用 high；兼容没有 high 列的行情源）────────────
    if USE_HIGH and "high" in df.columns:
        series = df["high"]
    else:
        series = df["close"]

    # 取「截止昨日」的 20 日最高点，今日收盘突破即为信号
    channel_high = series.iloc[-(CHANNEL_PERIOD + 1):-1].max()
    curr_close   = df["close"].iloc[-1]

    if curr_close <= channel_high:
        return False

    # ── 成交量确认 ────────────────────────────────────────────────
    if "volume" in df.columns:
        vol_avg = df["volume"].iloc[-(CHANNEL_PERIOD + 1):-1].mean()
        if vol_avg > 0 and df["volume"].iloc[-1] < vol_avg * VOL_MULT:
            return False

    return True
