# sc 兼容脚本（SuperClaude 命令等价实现）

这组脚本用于在 **Codex CLI** 环境下，提供类似 SuperClaude `/sc:*` 的“可执行入口”（但不是 Codex 的自定义 slash command）。

设计原则：
- 命令本体放在仓库内（可复用、可审计、可复现），避免把关键流程写死在聊天提示里。
- 所有运行输出统一落盘到 `logs/ci/<YYYY-MM-DD>/`，便于取证与排障。
- 默认遵循安全止损：高风险 Git 操作必须显式确认。

## “当前任务”从哪里来

- 默认读取 `.taskmaster/tasks/tasks.json` 中第一个 `status == "in-progress"` 的任务。
- 可用 `--task-id <n>` 显式指定。
- 三文件关联映射口径：
  - `tasks.json.master.tasks[].id` → `tasks_back[].taskmaster_id` → `tasks_gameplay[].taskmaster_id`
  - `sc-analyze` / `sc-git --smart-commit` 会把三者合并为一个 triplet 上下文。

## 输出位置（SSoT）

- `sc-analyze`：`logs/ci/<YYYY-MM-DD>/sc-analyze/`
- `sc-build`：`logs/ci/<YYYY-MM-DD>/sc-build/`
- `sc-test`：`logs/ci/<YYYY-MM-DD>/sc-test/`
- `sc-git`：`logs/ci/<YYYY-MM-DD>/sc-git/`
- `sc-acceptance-check`：`logs/ci/<YYYY-MM-DD>/sc-acceptance-check/`
- `sc-llm-review`：`logs/ci/<YYYY-MM-DD>/sc-llm-review/`（可选，本地 LLM 口头审查）

单元测试与覆盖率固定落盘到：`logs/unit/<YYYY-MM-DD>/`（由 `scripts/python/run_dotnet.py` 生成）。

## TDD 门禁编排（重要说明）

`py -3 scripts/sc/build.py tdd ...` 是“门禁编排器”，不是自动生成业务代码的生成器：

- `--stage red`：可选生成红灯测试骨架（默认路径：`Game.Core.Tests/Tasks/Task<id>RedTests.cs`）
- `--stage green`：提示你把最小实现写到正确的层（通常是 `Game.Core/**`）
- `--stage refactor`：运行命名/回链/契约一致性等检查，确保改动可控

契约护栏（强制止损）：
- `tdd` 会快照 `Game.Core/Contracts/**/*.cs`；若检测到新增/修改契约文件会直接失败
- 若确实需要新增契约：应先补齐 ADR/Overlay/Test-Refs，再继续 TDD

## Acceptance Check（等价于 Claude Code 的 /acceptance-check）

`py -3 scripts/sc/acceptance_check.py ...` 提供一个“可重复、可审计”的验收门禁脚本，用确定性检查替代 Claude Code 的多 Subagent 口头审查。

它把“6 个 subagents”映射为本仓库的可执行检查（部分为软门禁）：
- ADR 合规（硬）：任务 `adrRefs/archRefs/overlay`、ADR 文件存在、ADR 状态为 Accepted
- 任务回链（硬）：`scripts/python/task_links_validate.py`
- Overlay 校验（硬）：`scripts/python/validate_task_overlays.py`
- 契约一致性（硬）：`scripts/python/validate_contracts.py`
- 架构边界（硬）：`Game.Core` 不得引用 `Godot.*`
- 构建门禁（硬）：`dotnet build -warnaserror`（通过 `scripts/sc/build.py`）
- 安全软检查（软）：Sentry secrets / 核心契约检查 / 编码扫描
- 测试门禁（硬）：`scripts/sc/test.py --type all`（含 GdUnit4 + smoke）
- 性能门禁（可选硬门）：解析最新 `logs/ci/**/headless.log` 的 `[PERF] ... p95_ms=...` 并与阈值比较
  - 启用方式：`--perf-p95-ms <ms>` 或设置环境变量 `PERF_P95_THRESHOLD_MS=<ms>`
  - 快捷方式：`--require-perf`（legacy）：等价于启用性能硬门禁，阈值取 `PERF_P95_THRESHOLD_MS`，否则默认 20ms（口径见 ADR-0015）

可选：如果你仍希望保留“LLM 口头审查”的等价体验（但不建议作为硬门禁），使用：
`py -3 scripts/sc/llm_review.py --task-id <id> --base main`（输出落盘到 `logs/ci/<YYYY-MM-DD>/sc-llm-review/`）。
- 默认会尝试加载：
  - 仓库内：`.claude/agents/*.md`
  - 用户目录：`%USERPROFILE%\\.claude\\agents\\lst97\\*.md`（可用 `--claude-agents-root` 或 `CLAUDE_AGENTS_ROOT` 覆盖）

## Windows 用法示例

```powershell
# 任务分析（默认读当前 in-progress 任务）
py -3 scripts/sc/analyze.py --format report

# 构建（warn as error）
py -3 scripts/sc/build.py GodotGame.csproj --type dev --clean

# TDD 门禁编排
py -3 scripts/sc/build.py tdd --stage red --generate-red-test
py -3 scripts/sc/build.py tdd --stage green
py -3 scripts/sc/build.py tdd --stage refactor

# 测试（单测/全量含 Godot）
py -3 scripts/sc/test.py --type unit
py -3 scripts/sc/test.py --type all --godot-bin "$env:GODOT_BIN"

# 验收门禁（等价 /acceptance-check）
py -3 scripts/sc/acceptance_check.py --task-id 10 --godot-bin "$env:GODOT_BIN"

# 可选：LLM 口头审查（本地，软门禁；不建议作为 CI 硬门）
py -3 scripts/sc/llm_review.py --task-id 10 --base main

# Git（智能提交，脚本会读取 .superclaude/commit-template.txt）
py -3 scripts/sc/git.py commit --smart-commit --task-ref "#10.1"
```
