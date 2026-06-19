
# 🤖 QuantScout-AI: 高并发量化选股策略扫描与 AI 审计系统

[![Python Version](https://img.shields.io/badge/Python-3.9+-blue?svg=true&logo=python&logoColor=white)](https://github.com)
[![Gemini AI](https://img.shields.io/badge/AI-Gemini%201.5%20Flash-orange?svg=true&logo=google-gemini&logoColor=white)](https://github.com)
[![License](https://img.shields.io/badge/License-MIT-green?svg=true)](https://github.com)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey?svg=true)](https://github.com)

这是一个基于 Python 开发的**高并发、轻量级**量化选股策略扫描器。系统通过多线程并发调用本地/内网的行情 API，匹配自定义的技术面策略，并将命中的标的交由 **Gemini 1.5 Flash** 进行 AI 智能审计，最后将综合分析报告**实时推送**至用户的手机端。

---

## 💡 核心特性

* **🔄 多策略动态加载**：支持从特定目录自动读取、动态加载自定义的 Python 逻辑策略，扩展性极强。
* **⚡ 高并发扫描**：基于 `ThreadPoolExecutor` 多线程加速，配合 `tqdm` 动态进度条，支持快速扫描成百上千只股票。
* **🤖 AI 智能审计**：过滤出技术面命中的股票，再由大语言模型（Gemini）进行二次逻辑审计与打分，告别盲目跟从指标。
* **📱 移动端实时推送**：集成 **PushDeer** 推送服务，一键将选股报告（包含代码、名称、技术信号、AI分析原因）发送至手机。
* **⏱️ 定时自动轮询**：默认每 30 分钟全自动循环扫描，适合盘中实时监控或盘后自动化数据运行。

---

## 📂 项目目录结构

为了让策略文件能够正常动态加载，建议在 GitHub 仓库中保持如下目录结构：

```plaintext
.
├── main.py                 # 主程序入口
├── requirements.txt        # 依赖项清单
├── .gitignore              # 忽略配置文件（防止泄露敏感 key）
└── strategies/             # 策略文件夹（用户自定义策略存放处）
    ├── __init__.py
    ├── rsi_mom.py          # 自定义策略A（示例）
    └── alpha_break.py      # 自定义策略B（示例）

```

### ⚠️ 编写策略文件说明

放置在 `strategies/` 下的任何策略文件，**必须**暴露出以下两个方法供主程序反射调用：

1.  `run(df: pd.DataFrame) -> bool`: 接收包含 K线数据的 DataFrame，返回是否触发信号（`True` 或 `False`）。
    
2.  `get_name() -> str`: 返回该策略的易读中文名称（如 `"RSI超买"`、`"均线突破"`）。
    

## 🛠️ 环境准备与安装

### 1. 克隆仓库

Bash

```
git clone https://github.com/jackyezhang/quant-scout-ai.git
cd MyQuantBot

```

### 2. 安装依赖

Bash

```
pip install -r requirements.txt

```

> **主要核心依赖：** `google-genai`, `pandas`, `requests`, `tqdm`

## 🚀 配置与运行

在运行前，请打开 `main.py` 修改以下核心配置变量：

**配置项**

**说明**

**示例值**

`BASE_URL`

你的行情 API 服务器地址

`"http://localhost:8080"`

`proxy_addr`

代理地址（若国内环境调用 Gemini API 必备）

`"http://127.0.0.1:7890"`

`PUSH_DEER_KEY`

你的 PushDeer 推送密钥

`"PDKEY******"`

### 执行扫描

Bash

```
python main.py

```

## 🔒 安全与隐私提示 (Security Notice)

> [!CAUTION]
> 
> **重要安全提醒（上传至 GitHub 前必看）：**
> 
> 在将代码 `git push` 到公开仓库之前，请务必剔除或隐藏代码中硬编码的敏感信息！

-   ❌ **危险写法（易被黑客全网扫码抓取）：**
    
    Python
    
    ```
    PUSH_DEER_KEY = "PDKEY123456789"
    client = genai.Client(api_key="AIzaSyA123456...")
    
    ```
    
-   ✅ **推荐安全写法（使用系统环境变量）：**
    
    Python
    
    ```
    import os
    
    PUSH_DEER_KEY = os.getenv("PUSH_DEER_KEY")
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    ```
    

## 📄 免责声明

本项目仅用于技术研究与量化选股工具开发交流，不构成任何投资建议。股市有风险，入市需谨慎。据此入市，风险自担。
