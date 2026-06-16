import os, time, importlib.util, requests, json
import pandas as pd
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from google import genai

# --- 配置 ---
proxy_addr = "http://127.0.0.1:7890"
os.environ['http_proxy'] = proxy_addr
os.environ['https_proxy'] = proxy_addr
os.environ['no_proxy'] = "localhost,127.0.0.1,192.168.11.48,api2.pushdeer.com"

BASE_URL = "http://192.168.11.48:8080"
PUSH_DEER_KEY = "你的key"
STRATEGY_DIR = "./strategies"
TARGET_STRATEGIES = ["rsi_mom", "alpha_break"]
MAX_WORKERS = 20        # 并发线程数，按服务器承载力调整
REQUEST_TIMEOUT = (2, 5)

client = genai.Client(api_key="你的KEY")

def load_strategies():
    strategies = []
    if not os.path.exists(STRATEGY_DIR):
        os.makedirs(STRATEGY_DIR)
    targets = TARGET_STRATEGIES or [
        f[:-3] for f in os.listdir(STRATEGY_DIR)
        if f.endswith(".py") and f != "__init__.py"
    ]
    for name in targets:
        path = os.path.join(STRATEGY_DIR, f"{name}.py" if not name.endswith(".py") else name)
        if not os.path.exists(path):
            print(f"⚠️  策略文件未找到，已跳过: {path}")
            continue
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        strategies.append(mod)
    return strategies

def ai_audit(stock_code: str, tech_signal: str) -> dict:
    prompt = (
        f"分析标的 {stock_code}，技术信号：{tech_signal}。"
        '请按JSON格式返回: {"score": int, "reason": "str"}'
    )
    try:
        resp = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        text = resp.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        return {"score": 0, "reason": f"AI分析失败: {e}"}

def scan_stock(stock: dict, strategies: list) -> str | None:
    """单只股票扫描，供线程池调用。返回命中描述或 None。"""
    code = stock["code"]
    name = stock.get("name", "未知")
    try:
        res = requests.get(
            f"{BASE_URL}/api/kline?code={code}",
            timeout=REQUEST_TIMEOUT,
            headers={"Connection": "close"},
        )
        data = res.json().get("data", {}).get("List", [])
        if not data:
            return None
        df = pd.DataFrame(data)
        df.columns = [c.lower() for c in df.columns]
        for s in strategies:
            if s.run(df):
                return (code, name, s.get_name())   # 命中，返回元组
    except Exception:
        pass  # 单只异常静默跳过
    return None

def main():
    strategies = load_strategies()
    if not strategies:
        print("❌ 没有可用策略，退出。")
        return

    try:
        resp = requests.get(f"{BASE_URL}/api/codes", timeout=10)
        stock_list = resp.json()["data"]["codes"]
    except Exception as e:
        print(f"💥 获取股票池失败: {e}")
        return

    hits = []           # 命中列表（主线程聚合）
    lock = Lock()

    bar_fmt = "{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
    with tqdm(total=len(stock_list), desc="🚀 扫描中", unit="只", bar_format=bar_fmt) as pbar:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(scan_stock, s, strategies): s for s in stock_list}
            for fut in as_completed(futures):
                result = fut.result()
                if result:
                    with lock:
                        hits.append(result)
                pbar.update(1)

    # AI 审计仅对命中的票执行，大幅减少 API 调用次数
    if hits:
        report_lines = []
        for code, name, signal in hits:
            audit = ai_audit(code, signal)
            report_lines.append(
                f"【{name}】({code})\n技术面：{signal}\nAI分析：{audit['reason']}"
            )
        try:
            requests.get(
                "https://api2.pushdeer.com/message/push",
                params={"pushkey": PUSH_DEER_KEY, "text": "AI量化掘金报告",
                        "desp": "\n\n".join(report_lines)},
                proxies={"http": None, "https": None},
                timeout=10,
            )
            print(f"✅ 推送完成，命中 {len(hits)} 只标的。")
        except Exception as e:
            print(f"⚠️  推送失败: {e}")
    else:
        print("📭 本轮无命中。")

if __name__ == "__main__":
    while True:
        main()
        time.sleep(1800)
