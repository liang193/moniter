# moniter · 科技资讯 AI 监控站

一个基于 **Python + Streamlit** 的科技资讯监控工具：自动抓取多个科技媒体的 RSS 源，解析并过滤最近文章，调用 **DeepSeek 大模型**对每篇文章进行**智能分类 + 深度摘要**，并在侧边栏生成按「来源 → 分类」组织的智能目录。

针对部分网站的反爬拦截（Cloudflare JS 挑战、指纹校验、人机验证），内置了 **cloudscraper 优先、Playwright 有头浏览器人工兜底** 的两级抓取方案。

## 功能特性

- **多源聚合**：内置 5 个科技媒体 RSS 源，支持在侧边栏自由勾选。
- **时间过滤**：按 1–7 天滑块筛选最近发布的文章。
- **两级反爬**：
  - 优先用 [cloudscraper](https://github.com/VeNoMouS/cloudscraper) 模拟 Chrome 浏览器指纹，绕过基础 JS 挑战与指纹校验；
  - 当返回 403 / 503 或解析不到文章时，自动用 [Playwright](https://playwright.dev/python/) 启动**有头浏览器**，预留 15 秒人工完成人机验证，随后在浏览器页面内直接 `fetch` 拿到验证后的原始数据。
- **AI 分类 + 深度摘要**：调用 DeepSeek，将文章自动归入 4 个固定标签，并生成约 100 字、涵盖核心技术点 / 商业影响的深度摘要。
- **智能目录**：侧边栏按「来源 → 分类标签」分组，列出文章标题与原文链接，便于快速导航。
- **健壮性处理**：
  - 启动时清空环境变量中的「幽灵代理」，避免请求卡死；
  - API Key 通过环境变量 `DEEPSEEK_API_KEY` 读取，代码中不硬编码；
  - 三级链接提取（`<link>` 文本 / `href` → `guid` / `id`），兼容 RSS 与 Atom；
  - 兼容多种日期格式，正文自动去除 HTML 标签并截取前 2500 字；
  - 抓取失败时展示明确的错误卡片，而不是静默失败。

## 监控的信息源

| 来源 | RSS 地址 |
| --- | --- |
| 量子位 | https://www.qbitai.com/feed |
| 36氪 | https://36kr.com/feed |
| 极客公园 | https://www.geekpark.net/rss |
| 爱范儿 | https://www.ifanr.com/feed |
| IT之家 | https://www.ithome.com/rss/ |

## 技术栈

- **Streamlit**：网页 UI 与交互（源多选、时间滑块、智能目录）
- **cloudscraper**：模拟浏览器指纹，绕过基础反爬
- **BeautifulSoup4 + lxml**：RSS / Atom 的 XML 解析与正文清洗
- **requests**：调用 DeepSeek Chat Completions API
- **Playwright**：有头浏览器人工过验证码、页面内抓取（兜底方案）

## 工作流程

```
勾选信息源 + 设定天数
        │
        ▼
cloudscraper 抓取 RSS ──(403/503 或无数据)──▶ Playwright 弹窗人工验证后页面内抓取
        │
        ▼
XML 解析 → 按时间过滤 → 清洗正文（去标签、截取）
        │
        ▼
DeepSeek 分类打标（4 类）+ 约 100 字深度摘要
        │
        ▼
网页展示 + 侧边栏「来源 → 分类」智能目录
```

## 快速开始

### 1. 克隆并安装依赖

```bash
git clone https://github.com/liang193/moniter.git
cd moniter
pip install -r requirements.txt
```

如需启用 Playwright 人工验证兜底（推荐安装）：

```bash
pip install playwright
playwright install chromium
```

### 2. 配置 DeepSeek API Key

通过环境变量提供，不要写进代码：

```powershell
# Windows PowerShell
$env:DEEPSEEK_API_KEY = "sk-你的密钥"
```

```bash
# macOS / Linux
export DEEPSEEK_API_KEY="sk-你的密钥"
```

### 3. 运行

```bash
streamlit run app.py
```

浏览器打开 http://localhost:8501 即可使用。手机与电脑连接同一局域网时，也可访问页面提示的 Network URL。

## 使用说明

1. 在侧边栏勾选要监控的信息源（默认选中「量子位」「36氪」）；
2. 拖动滑块选择获取多少天内的文章（1–7 天）；
3. 点击「🚀 立即获取并让 AI 总结」；
4. 若某来源触发人机验证，会自动弹出浏览器窗口，请在 **15 秒内**完成验证，程序随后会自动继续；
5. 结果按时间倒序展示，左侧「📑 智能目录」可按来源和分类快速跳转。

> 提示：程序启动时会清空 `http_proxy` / `https_proxy` 等环境变量。若你依赖代理上网，请知悉这一行为。

## 项目结构

```
moniter/
├── app.py            # 主程序：抓取、解析、AI 总结、Streamlit UI（单文件）
├── requirements.txt  # Python 依赖
└── .devcontainer/    # Dev Container 配置
```

## 后续可改进方向

- 用 `aiohttp` / `httpx` 做异步并发抓取与 API 调用，增加并发上限、重试与结果缓存；
- 用模型的 JSON mode / function calling 替代文本解析，让分类与摘要输出更稳定；
- 定时抓取 + 去重，出现关心的主题时主动通过微信 / 邮件推送；
- 基于文章原文做检索问答（RAG），支持「今天 AI 圈有什么大事」这类提问，进一步向自动化 Agent 演进。
