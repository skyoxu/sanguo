# sc 兼容脚本（SuperClaude 命令等价实现）

这组脚本用于在 **Codex CLI** 环境下，提供类似 SuperClaude `/sc:*` 的“可执行入口”（但不是 Codex 的自定义 slash command）。

## 设计意图

- 以仓库内 Python 脚本实现“命令本体”，避免把关键流程绑死在聊天提示里
- 所有运行输出落盘到 `logs/ci/<YYYY-MM-DD>/`，便于审计与归档
- 默认遵循“安全止损”：高风险 Git 操作需要 `--yes` 显式确认

## “当前任务”从哪来

- 默认读取 `.taskmaster/tasks/tasks.json` 中**第一个** `status == "in-progress"` 的任务
- 可用 `--task-id <n>` 显式指定
- 三文件关联映射口径：
  - `tasks.json.master.tasks[].id` ↔ `tasks_back[].taskmaster_id` ↔ `tasks_gameplay[].taskmaster_id`
  - `sc-analyze` / `sc-git --smart-commit` 会把三者合并为一个“triplet 上下文”

## 输出位置（SSoT）

- `sc-analyze`：`logs/ci/<YYYY-MM-DD>/sc-analyze/`
  - `task_context.json` / `task_context.md`：当前任务 + back/gameplay 补充信息（含 taskdoc 追加内容）
  - `summary.json`（以及 `--format report` 时的 `report.md`）
- `sc-build`：`logs/ci/<YYYY-MM-DD>/sc-build/`
  - `dotnet-build.log`、`summary.json`
- `sc-test`：`logs/ci/<YYYY-MM-DD>/sc-test/`
  - `unit.log`、`gdunit-hard.log`、`smoke.log`、`summary.json`
  - 单测产物固定落盘到：`logs/unit/<YYYY-MM-DD>/`（由 `scripts/python/run_dotnet.py` 生成 `summary.json`）
- `sc-git`：`logs/ci/<YYYY-MM-DD>/sc-git/`
  - `commit-message.txt`（smart commit 生成的提交信息）
  - `<op>.log`、`summary.json`

## TDD 编排（重要说明）

`py -3 scripts/sc/build.py tdd ...` 是“门禁编排器”，不是自动写业务代码的生成器：

- `--stage red`：可选生成红灯测试骨架（默认路径：`Game.Core.Tests/Tasks/Task<id>RedTests.cs`）
- `--stage green`：提示你把最小实现写到正确层（通常是 `Game.Core/**`）
- `--stage refactor`：跑命名/任务引用/契约一致性等检查，确保改动可控

契约护栏（强制止损）：
- `tdd` 会快照 `Game.Core/Contracts/**/*.cs`；若检测到新增/修改契约文件会直接失败
- 若确实需要新增契约：先暂停脚本流程，按 ADR/Overlay 口径手工补齐（并同步测试/文档），再继续

## Windows 用法示例

```powershell
# 静态分析（不编译、不跑引擎）；默认读取 tasks.json 里第一个 status=in-progress 的任务
py -3 scripts/sc/analyze.py --focus security --depth deep --format report
py -3 scripts/sc/analyze.py --task-id 2 --format report

# 构建（warn as error）
py -3 scripts/sc/build.py GodotGame.csproj --type dev --clean

# TDD 门禁编排（非自动代码生成）：red/green/refactor 的可复现跑法与日志落盘
py -3 scripts/sc/build.py tdd --stage red --generate-red-test
py -3 scripts/sc/build.py tdd --stage green
py -3 scripts/sc/build.py tdd --stage refactor

# 测试：单测（含覆盖率门禁） / E2E（需要 Godot）
py -3 scripts/sc/test.py --type unit
py -3 scripts/sc/test.py --type unit --no-coverage-gate   # 仅用于本地调试（不建议在门禁中使用）
py -3 scripts/sc/test.py --type unit --no-coverage-report
py -3 scripts/sc/test.py --type e2e --godot-bin \"$env:GODOT_BIN\"

# Git 操作（强制确认：reset/clean/rebase/force push）
py -3 scripts/sc/git.py status
py -3 scripts/sc/git.py commit --smart-commit --yes
```

## 推荐顺序（最小闭环）

```powershell
py -3 scripts/sc/analyze.py --format report
py -3 scripts/sc/build.py tdd --stage red --generate-red-test
py -3 scripts/sc/build.py tdd --stage green
py -3 scripts/sc/build.py tdd --stage refactor
py -3 scripts/sc/test.py --type unit --no-coverage-report
py -3 scripts/sc/git.py commit --smart-commit --yes
```
