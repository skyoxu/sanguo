# sc 兼容脚本（SuperClaude 命令等价实现）

这组脚本用于在 **Codex CLI** 环境下，提供类似 SuperClaude `/sc:*` 的“可执行入口”（但不是 Codex 的自定义 slash command）。

## 设计意图

- 以仓库内 Python 脚本实现“命令本体”，避免把关键流程绑死在聊天提示里
- 所有运行输出落盘到 `logs/ci/<YYYY-MM-DD>/`，便于审计与归档
- 默认遵循“安全止损”：高风险 Git 操作需要 `--yes` 显式确认

## Windows 用法示例

```powershell
# 静态分析（不编译、不跑引擎）
py -3 scripts/sc/analyze.py --focus security --depth deep --format report

# 构建（warn as error）
py -3 scripts/sc/build.py GodotGame.csproj --type dev --clean

# 测试：单测（含覆盖率） / E2E（需要 Godot）
py -3 scripts/sc/test.py --type unit
py -3 scripts/sc/test.py --type e2e --godot-bin \"$env:GODOT_BIN\"

# Git 操作（强制确认：reset/clean/rebase/force push）
py -3 scripts/sc/git.py status
py -3 scripts/sc/git.py commit --smart-commit --yes
```

