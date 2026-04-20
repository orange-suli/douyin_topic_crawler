---
description: 抖音多关键词全量回归测试
---

# WORKFLOW: 抖音全栈系统自动化回归测试 (API驱动版)

## 1. 环境与服务拉起
- **环境激活**: 在所有终端执行 `conda activate douyin-scrawl`。
- **后端启动**: 在后台终端运行 `uvicorn backend.main:app --port 8000`。
- **健康检查**: 等待 3 秒，确保 API 服务已成功挂载。

## 2. 核心链路自动化测试 (测试集: ["大模型", "赛博朋克", "极光"])
QA Agent 请编写并运行一个临时的 Python 测试脚本 (`test_runner.py`)，针对上述测试集循环执行以下逻辑：
1. **API 触发**: 使用 `requests` 库向 `POST http://localhost:8000/api/crawl` 发起请求，Payload 为 `{"keyword": "当前词", "limit": 5}`。
2. **状态断言**: 记录接口耗时。断言 HTTP 状态码必须为 200，且返回成功状态。
3. **数据校验**: 随后立即请求 `GET http://localhost:8000/api/videos?keyword=当前词`，断言返回的 JSON 数组长度大于 0。
4. **防风控休眠**: 每个关键词测试完毕后，强制 `time.sleep(15)`。

## 3. 前端 UI 渲染验收
1. **页面访问**: 使用内置 Browser 打开前端看板页面。
2. **模拟交互**: 在前端页面的搜索框中输入“大模型”，点击“开始抓取”按钮。
3. **视觉快照**: 等待 Loading 状态结束且 ECharts 图表渲染完成后，生成一张完整的 Browser Screenshot 工件。
4. **清理资源**: 终止 `uvicorn` 和测试脚本的进程，清理控制台。