"""
布林带超卖反弹 v2
优化点：
1. 原逻辑只判断「当前在下轨以下」，无反弹确认，容易买在下跌途中（刀口接盘）
2. 增加反弹确认：收盘价从下轨下方回升到下轨以上（下影线反弹形态）
3. 增加成交量放大过滤：反弹需要量能配合
4. 增加整体趋势判断：避免在长期下跌趋势中逆势做多
"""

BOLL_PERIOD  = 20
BOLL_STD     = 2.0
VOL_MULT     = 1.2    # 反弹日成交量需 > 前5日均量的倍数
MA60_FILTER  = True   # True=开启长期趋势过滤

def get_name():
    return "布林带超卖反弹"

def run(df) -> bool:
    need = BOLL_PERIOD + 60 + 5 if MA60_FILTER else BOLL_PERIOD + 5
    if len(df) < need:
        return False

    close  = df["close"]
    ma20   = close.rolling(BOLL_PERIOD).mean()
    std20  = close.rolling(BOLL_PERIOD).std(ddof=1)
    lower  = ma20 - BOLL_STD * std20

    prev_close = close.iloc[-2]
    curr_close = close.iloc[-1]
    lower_prev = lower.iloc[-2]
    lower_curr = lower.iloc[-1]

    # ── 反弹形态：昨日收盘在下轨下方，今日收盘回到下轨上方 ────────
    bounce = (prev_close < lower_prev) and (curr_close >= lower_curr)
    if not bounce:
        return False

    # ── 成交量确认 ────────────────────────────────────────────────
    if "volume" in df.columns:
        vol_avg5 = df["volume"].iloc[-6:-1].mean()
        if vol_avg5 > 0 and df["volume"].iloc[-1] < vol_avg5 * VOL_MULT:
            return False

    # ── 长期趋势过滤（MA60 向上或走平才允许做多）────────────────────
    if MA60_FILTER:
        ma60 = close.rolling(60).mean()
        if ma60.iloc[-1] < ma60.iloc[-5]:   # 5日斜率向下则跳过
            return False

    return True
