这是一个基于 Python 开发的高并发轻量级量化选股策略扫描器。系统通过多线程并发调用本地/内网的行情 API，匹配自定义的技术面策略，并将命中的标的交由 Gemini 1.5 Flash 进行 AI 智能审计，最后将综合分析报告实时推送至用户的手机端。

💡 核心特性
多策略动态加载：支持从特定目录自动读取、加载自定义的 Python 逻辑策略。

高并发扫描：基于 ThreadPoolExecutor 多线程加速，配合 tqdm 进度条，支持快速扫描成百上千只股票。

AI 智能审计：过滤出技术面命中的股票，再由大语言模型（Gemini）进行二次逻辑审计与打分，告别盲目跟从指标。

移动端实时推送：集成 PushDeer 推送服务，一键将选股报告（包含代码、名称、技术信号、AI分析原因）发送至手机。

定时轮询：默认每 30 分钟全自动循环扫描，适合盘中或盘后自动化运行。

📂 推荐项目目录结构
为了让策略文件能够正常加载，建议在 GitHub 仓库中保持如下目录结构：

Plaintext
.
├── main.py                 # 主程序入口
├── requirements.txt        # 依赖项清单
├── .gitignore              # 忽略配置文件（防止泄露敏感 key）
└── strategies/             # 策略文件夹
    ├── __init__.py
    ├── rsi_mom.py          # 自定义策略A（示例）
    └── alpha_break.py      # 自定义策略B（示例）
⚠️ 编写策略文件说明：
放置在 strategies/ 下的策略文件需要暴露出两个方法供主程序调用：

run(df: pd.DataFrame) -> bool: 接收包含 K 线数据的 DataFrame，返回是否触发信号。

get_name() -> str: 返回该策略的易读名称（如 "RSI超买"）。

🛠️ 环境准备与安装
克隆仓库

Bash
git clone https://github.com/你的用户名/你的仓库名.git
cd 你的仓库名
安装依赖

Bash
pip install -r requirements.txt
主要依赖：google-genai, pandas, requests, tqdm

🚀 配置与运行
在运行前，请打开 main.py 修改以下配置：

BASE_URL: 你的行情 API 服务器地址。

proxy_addr: 代理地址（若国内环境调用 Gemini API 需要）。

PUSH_DEER_KEY: 你的 PushDeer 推送密钥。

genai.Client(api_key="..."): 你的 Google Gemini API Key。

执行扫描：

Bash
python main.py
🔒 安全与隐私提示 (Security Notice)
🔴 重要安全提醒（上传至 GitHub 前必看）：
在将代码 git push 到公开仓库之前，请务必剔除或隐藏代码中硬编码的敏感信息！

PUSH_DEER_KEY (当前泄露风险)

genai.Client(api_key="AIzaSy...") (当前泄露风险)

强烈建议将上述秘钥改用环境变量或 dotenv 库读取，例如：

Python
import os
PUSH_DEER_KEY = os.getenv("PUSH_DEER_KEY")
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
免责声明
本项目仅用于技术研究与量化选股工具开发交流，不构成任何投资建议。据此入市，风险自担。
