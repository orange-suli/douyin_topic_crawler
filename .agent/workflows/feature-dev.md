---
description: 功能分支同步
---

# WORKFLOW: 功能分支同步
1. **自动识别**: 获取当前 Git 分支名。
2. **冻结环境**: 执行 `pip freeze > requirements.txt`。
3. **提交代码**: 执行 `git add .` 并根据改动自动生成 commit 信息。
4. **推送分支**: 执行 `git push origin [当前分支名]`，在 GitHub 上创建一个对应的备份分支。