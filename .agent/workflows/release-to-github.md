---
description: 自动更新文档与提交代码
---

# WORKFLOW: 自动更新文档与提交代码

1. **同步文档**: 阅读最新的代码变更，自动更新 `README.md` 中的特性列表或启动指令。
2. **冻结依赖**: 执行 `pip freeze > requirements.txt` 确保依赖列表是最新的。
3. **提交代码**: 
   - 自动执行 `git add .`
   - 根据本次修改的内容，自动生成一段符合 Conventional Commits 规范的 Git 提交信息并执行 commit。
4. **推送到云端**: 执行 `git push origin main`。