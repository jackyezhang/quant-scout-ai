"""
分仓组合扫描器 v1  —  保守风格
────────────────────────────────────────────────────────────────
设计原则
  - 每个策略独立选股，仓位互不干扰
  - 命中股票须通过「共识过滤层」才进入报告（保守加固）
  - 共识层：RSI 不超买 + 成交量健康 + 非连续涨停
  - 输出按策略分组，便于 AI 审计和推送阅读
────────────────────────────────────────────────────────────────
"""

import importlib.util, os
import pandas as pd

# ── 策略加载 ──────────────────────────────────────────────────
STRATEGY_DIR = "./strategies"
TARGET_STRATEGIES = ["rsi_mom", "bollinger", "donchian", "alpha_break"]

def _load(name: str):
    path = os.path.join(STRATEGY_DIR, f"{name}.py")
    if not os.path.exists(path):
        print(f"⚠️  策略文件未找到: {path}")
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

# ── 共识过滤层（保守守门员）────────────────────────────────────
def consensus_filter(df: pd.DataFrame) -> tuple[bool, list[str]]:
    """
    通过返回 (True, []) / (False, [拒绝原因]) 方便调试。
    任意一项不通过即过滤。
    """
    reasons = []
    close  = df["close"]
    volume = df.get("volume", df.get("vol"))

    # 1. RSI 不超买（< 75）——防止在过热区域入场
    try:
        delta    = close.diff()
        avg_gain = delta.clip(lower=0).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        avg_loss = (-delta).clip(lower=0).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        rsi = 100 - 100 / (1 + avg_gain / avg_loss.replace(0, float("nan")))
        if rsi.iloc[-1] >= 75:
            reasons.append(f"RSI超买({rsi.iloc[-1]:.1f}≥75)")
    except Exception:
        pass

    # 2. 成交量不萎缩——今日量不低于5日均量的 80%
    if volume is not None:
        try:
            vol_avg5 = volume.iloc[-6:-1].mean()
            if vol_avg5 > 0 and volume.iloc[-1] < vol_avg5 * 0.8:
                reasons.append("量能萎缩(<80%均量)")
        except Exception:
            pass

    # 3. 非连续涨停——今日和昨日均未涨停（涨幅 < 9.5%）
    try:
        chg_today = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2]
        chg_prev  = (close.iloc[-2] - close.iloc[-3]) / close.iloc[-3]
        if chg_today >= 0.095:
            reasons.append(f"今日涨停({chg_today:.1%})")
        if chg_prev >= 0.095:
            reasons.append(f"连板风险(昨{chg_prev:.1%})")
    except Exception:
        pass

    return (len(reasons) == 0), reasons


# ── 主扫描函数 ────────────────────────────────────────────────
def run_combo(stock_list: list[dict], get_df) -> dict[str, list[dict]]:
    """
    参数
      stock_list : [{"code": "000001", "name": "平安银行"}, ...]
      get_df     : callable(code) -> pd.DataFrame | None  （由调用方传入 K 线获取逻辑）

    返回
      {策略名: [{"code":..., "name":..., "filter_passed": bool, "reject_reasons": [...]}]}
    """
    strategies = [s for s in (_load(n) for n in TARGET_STRATEGIES) if s]
    results: dict[str, list] = {s.get_name(): [] for s in strategies}

    for stock in stock_list:
        code = stock["code"]
        name = stock.get("name", "未知")
        df   = get_df(code)
        if df is None or len(df) < 25:
            continue
        df.columns = [c.lower() for c in df.columns]

        for s in strategies:
            try:
                if not s.run(df):
                    continue
            except Exception as e:
                continue

            passed, reasons = consensus_filter(df)
            results[s.get_name()].append({
                "code"          : code,
                "name"          : name,
                "filter_passed" : passed,
                "reject_reasons": reasons,
            })

    return results


def format_report(results: dict[str, list]) -> str:
    """将扫描结果格式化为推送文本，保守模式只展示通过共识层的股票。"""
    lines = []
    for strategy_name, hits in results.items():
        passed = [h for h in hits if h["filter_passed"]]
        blocked = len(hits) - len(passed)
        if not passed:
            continue
        lines.append(f"━━ {strategy_name} ━━  (共识层过滤掉 {blocked} 只)")
        for h in passed:
            lines.append(f"  【{h['name']}】{h['code']}")
    if not lines:
        return "本轮扫描无符合条件标的（保守过滤已启用）"
    return "\n".join(lines)
