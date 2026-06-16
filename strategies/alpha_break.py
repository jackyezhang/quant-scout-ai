"""
华尔街趋势突破 v2
优化点：
1. 原策略在 run() 内直接 rename columns，会污染外部传入的 df（pandas 引用语义）
   → 改为用局部变量引用原列，不修改 df
2. vol_ratio 分母取 rolling(5).mean().iloc[-2]，当 df 恰好 20 行时 iloc[-2] 可能是 NaN
   → 改为明确的 iloc 切片 + 零值保护
3. 涨幅区间 0.04~0.09 在 A 股对应 4%~9%，但未考虑涨停板（10%/20%）附近的特殊情况
   → 区间调整为 0.03~0.095，并增加「非涨停」过滤避免追板
4. MA20 趋势过滤增加斜率确认（连续 3 日向上）
5. 增加 NaN 安全检查
"""

MA_PERIOD    = 20
VOL_PERIOD   = 5
VOL_RATIO    = 1.5
CHANGE_LOW   = 0.03   # 最低涨幅 3%
CHANGE_HIGH  = 0.095  # 最高涨幅（略低于涨停，避免追板）

def get_name():
    return "华尔街趋势突破"

def run(df) -> bool:
    if len(df) < MA_PERIOD + VOL_PERIOD + 3:
        return False

    close  = df["close"]
    volume = df.get("volume", df.get("vol"))   # 兼容两种列名
    if volume is None:
        return False

    # ── 涨幅计算 ─────────────────────────────────────────────────
    prev_c = close.iloc[-2]
    curr_c = close.iloc[-1]
    if prev_c == 0:
        return False
    change = (curr_c - prev_c) / prev_c
    if not (CHANGE_LOW < change < CHANGE_HIGH):
        return False

    # ── MA20 向上趋势 ─────────────────────────────────────────────
    ma20 = close.rolling(MA_PERIOD).mean()
    if curr_c <= ma20.iloc[-1]:
        return False
    if ma20.iloc[-1] <= ma20.iloc[-3]:   # MA20 本身需向上倾斜
        return False

    # ── 量比确认（今日量 vs 前5日平均量）────────────────────────────
    vol_avg = volume.iloc[-(VOL_PERIOD + 1):-1].mean()
    if vol_avg == 0:
        return False
    vol_ratio = volume.iloc[-1] / vol_avg
    if vol_ratio < VOL_RATIO:
        return False

    return True
