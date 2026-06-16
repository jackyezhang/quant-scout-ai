"""
main_combo.py v4  —  分组推送 + AI评分 Top N + 免费套餐限速
"""

import os, time, json, requests
import pandas as pd
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from google import genai
from combo_scanner import run_combo

# ── 配置 ──────────────────────────────────────────────────────
BASE_URL      = "http://192.168.11.48:8080"
PUSH_DEER_KEY = "PDU41834Tchqz88rCV2hySSkAOkoKL0tImOkHXy09"
MAX_WORKERS   = 20
TOP_N         = 5    # 每个策略最多推送几只

# 免费套餐限速：每分钟最多 12 次（上限15，留3次余量）
GEMINI_RPM    = 12
_rate_lock    = Lock()
_last_call_ts = [0.0]   # 用列表包装以便在闭包中修改

client = genai.Client(api_key="AIzaSyDt3tyx2ZpARY9aTzPXwz9PzCVyk4k61LE")

# ── K 线获取 ──────────────────────────────────────────────────
def get_df(code: str) -> pd.DataFrame | None:
    try:
        res  = requests.get(f"{BASE_URL}/api/kline?code={code}",
                            timeout=(2, 5), headers={"Connection": "close"})
        data = res.json().get("data", {}).get("List", [])
        return pd.DataFrame(data) if data else None
    except Exception:
        return None

# ── 限速等待（线程安全）──────────────────────────────────────
def _rate_wait():
    """确保两次 Gemini 调用间隔不低于 60/GEMINI_RPM 秒"""
    interval = 60.0 / GEMINI_RPM
    with _rate_lock:
        now  = time.time()
        wait = interval - (now - _last_call_ts[0])
        if wait > 0:
            time.sleep(wait)
        _last_call_ts[0] = time.time()

# ── AI 审计（含限速 + 429 自动重试）────────────────────────
def ai_audit(code: str, name: str, strategy: str) -> dict:
    prompt = (
        f"股票 {name}({code})，触发策略：{strategy}。"
        f"请综合基本面风险和技术面给出评分和简要理由。"
        f"只返回JSON，不要其他内容：{{\"score\":int(0-100),\"reason\":\"str\"}}"
    )
    for attempt in range(3):   # 最多重试3次
        _rate_wait()
        try:
            resp   = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            text   = resp.text.strip()
            if "```" in text:
                parts = text.split("```")
                text  = parts[1] if len(parts) >= 3 else parts[-1]
                text  = text.replace("json", "", 1).strip()
            result = json.loads(text)
            result["score"] = int(result.get("score", 0))
            return result
        except Exception as e:
            err = str(e)
            if "429" in err:
                wait = 60 * (attempt + 1)
                print(f"    ⏳ 限流，等待 {wait}s 后重试 [{code}]")
                time.sleep(wait)
            else:
                print(f"    ⚠️  AI审计异常 [{code}]: {e}")
                break
    return {"score": 0, "reason": "AI分析失败（已重试）"}

# ── 推送单条消息 ──────────────────────────────────────────────
def push(title: str, desp: str):
    try:
        requests.get(
            "https://api2.pushdeer.com/message/push",
            params={"pushkey": PUSH_DEER_KEY, "text": title, "desp": desp},
            proxies={"http": None, "https": None},
            timeout=10,
        )
    except Exception as e:
        print(f"⚠️  推送失败: {e}")

# ── 主流程 ────────────────────────────────────────────────────
def main():
    # 1. 获取股票池
    try:
        stock_list = requests.get(f"{BASE_URL}/api/codes", timeout=10).json()["data"]["codes"]
    except Exception as e:
        print(f"💥 获取股票池失败: {e}")
        return

    # 2. 并发拉取 K 线
    df_cache: dict[str, pd.DataFrame | None] = {}
    with tqdm(total=len(stock_list), desc="📡 拉取行情", unit="只") as pbar:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futs = {pool.submit(get_df, s["code"]): s["code"] for s in stock_list}
            for f in as_completed(futs):
                df_cache[futs[f]] = f.result()
                pbar.update(1)

    # 3. 组合扫描
    print("🔍 策略扫描中…")
    results = run_combo(stock_list, lambda code: df_cache.get(code))

    # 4. 按策略分组：取 Top N 候选 → AI 审计（限速）→ 排序推送
    total_pushed = 0
    for strategy_name, hits in results.items():
        passed = [h for h in hits if h["filter_passed"]]
        if not passed:
            continue

        # 先取前 TOP_N*3 候选（减少 AI 调用次数），再审计排序取 Top N
        candidates = passed[: TOP_N * 3]
        print(f"  [{strategy_name}] 命中 {len(passed)} 只，对前 {len(candidates)} 只 AI 审计中…")

        audited = []
        for h in candidates:
            audit = ai_audit(h["code"], h["name"], strategy_name)
            audited.append({**h, **audit})

        audited.sort(key=lambda x: x["score"], reverse=True)
        top = audited[:TOP_N]

        lines = [f"共 {len(passed)} 只命中，展示评分最高 {len(top)} 只\n"]
        for i, h in enumerate(top, 1):
            lines.append(
                f"{i}. 【{h['name']}】{h['code']}\n"
                f"   评分：{h['score']}/100\n"
                f"   {h['reason']}"
            )

        push(f"📊 {strategy_name}", "\n\n".join(lines))
        total_pushed += len(top)
        print(f"     → 推送 Top {len(top)} 只（最高分 {top[0]['score']}）")

    if total_pushed == 0:
        print("📭 本轮无命中。")
        push("📭 AI量化掘金", "本轮扫描无符合条件标的")
    else:
        print(f"✅ 本轮推送完成，共 {total_pushed} 只")

if __name__ == "__main__":
    while True:
        main()
        time.sleep(1800)
