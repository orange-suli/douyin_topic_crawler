---
trigger: always_on
---

# SKILL: 抖音抓取与可视化全栈系统 (Douyin-Scrawl Ecosystem)

## 1. 项目全局视界 (System Architecture)
本项目采用多智能体协作（Multi-Agent Collaboration）架构。所有参与本项目的 Agent 必须明确自身职责，严禁跨界修改文件或逻辑：
* **Scraper Agent**: 负责 Playwright 自动化与底层原始 JSON 数据截获。
* **Data Agent**: 负责原始数据的清洗、标准化与 SQLite 入库。
* **API Agent**: 负责基于 FastAPI 构建连接数据库与前端的中间层。
* **Frontend Agent**: 负责数据看板（Dashboard）的交互与图表渲染。
* **QA Agent**: 负责端到端（E2E）的自动化流转测试与错误溯源。

## 2. 运行环境与执行基准 (Critical Context)
* **专属沙盒**: 本项目的所有代码开发、依赖安装和终端执行，**必须**在 Conda 虚拟环境 `douyin-scrawl` 中进行。
* **终端指令**: Agent 在 Antigravity 内置终端执行任何操作前，需严格执行 `conda activate douyin-scrawl`。若由于终端限制无法激活，必须使用该环境下 Python 解释器的绝对路径。
* **依赖同步**: 任何新安装的第三方库（Playwright, Pandas, FastAPI 等），必须实时更新至项目根目录的 `requirements.txt`。

## 3. 分阶段执行规范与技术约束

### Phase 1: 数据抓取流 (Scraper Agent)
* **核心工具**: Playwright (Chromium)。首次运行须确保已执行 `playwright install chromium`。
* **数据截获 (最高优先级)**: **绝对禁止**通过解析脆弱的 HTML DOM 类名来获取视频核心数据。必须使用 `page.on("response", ...)` 监听并拦截 `/aweme/v1/web/search/item/` 等 XHR/Fetch 接口的 JSON 响应体。
* **深度抓取**: 若列表 JSON 中缺失“博主粉丝数”，需编写二次跳转逻辑，模拟点击进入博主详情页获取。
* **反风控与人机协作**:
  * 必须为每次页面操作注入随机延迟（2s - 8s）。
  * 遇到滑块验证码、风控弹窗或强制登录拦截时，程序必须立即调用 `page.pause()` 挂起。同时在终端输出高亮警告，等待开发者在 Antigravity 内置浏览器中手动完成验证或扫码后，再恢复执行。

### Phase 2: 数据清洗与持久化 (Data Agent)
* **核心工具**: Pandas, SQLite3。
* **清洗准则**:
  * **数值结构化**: 将非标准格式（如“1.2w”、“250万”）清洗并映射为精准的整型数值（12000, 2500000）。
  * **严密性**: 面对缺失字段（NaN/Null）需有明确的处理策略（如填充 `0` 或剔除记录）。必须保证清洗后的结构化数据能完美适配后续高阶的统计分析或 Logistic 回归等数学建模需求，杜绝脏数据污染数据库。
  * **并发安全**: SQLite 读写操作必须使用上下文管理器（`with sqlite3.connect(...)`）。

### Phase 3: 后端数据服务 (API Agent)
* **核心工具**: FastAPI, Uvicorn。
* **架构要求**:
  * 提供清晰的 RESTful 路由（例如：获取原始列表的 `/api/videos`，获取聚合分析的 `/api/stats`）。
  * 全面使用 `async/await` 异步语法以应对潜在的高并发请求。
  * 必须配置 CORS（跨域资源共享）中间件，确保前端能正常拉取数据。

### Phase 4: 前端可视化面板 (Frontend Agent)
* **核心工具**: HTML/JS 结合 ECharts（或基于 Vue/React）。
* **UI/UX 要求**:
  * 设计需具备高信噪比，重点突出：互动数据（点赞/评论/转发）的柱状对比图、视频标签 (Tags) 的词云图、以及粉丝数与互动率的散点关系图。
  * 必须保持页面动态性，数据需通过 `fetch` 或 `axios` 异步请求 FastAPI 接口，而非写死在前端文件中。

## 4. 交付物与测试验收 (Artifacts & Verification)
* **模块化**: 系统的抓取、清洗、后端、前端逻辑必须在不同的文件目录下物理隔离。
* **可视化验收**: 任何涉及到 UI 或完整链路的重构，Agent 必须通过 Antigravity 生成 **Browser Recording (录屏)** 或 **Screenshot (截图)** 工件。开发者只看最终渲染结果和终端日志，拒绝人工在浏览器中反复手动调试。