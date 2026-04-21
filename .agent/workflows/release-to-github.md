---
description: 正式版本发布
---

# WORKFLOW: 正式版本发布
1. **切回主线**: 执行 `git checkout main`。
2. **合并代码**: 执行 `git merge [功能分支名]`。
3. **文档同步**: 让 Doc Agent 自动更新 README 的版本号。
4. **推送主线**: 执行 `git push origin main`。
5. **清理**: 执行 `git branch -d [功能分支名]`。