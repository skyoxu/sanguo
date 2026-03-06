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

`scripts/sc/acceptance_check.py` 提供一个“可重复、可审计”的验收门禁脚本，用确定性检查替代 Claude Code 的多 Subagent 口头审查。

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
- 安全档位（建议显式）：
  - `--security-profile host-safe`：默认推荐，保持主机边界硬门，反篡改默认降级
  - `--security-profile strict`：发布收口/高风险改动，安全项全部硬门
  - 解析顺序：CLI > `SECURITY_PROFILE` > 默认 `host-safe`

可选：如果你仍希望保留“LLM 口头审查”的等价体验（但不建议作为硬门禁），使用：
`scripts/sc/llm_review.py` writes outputs to `logs/ci/<YYYY-MM-DD>/sc-llm-review/`; prefer calling it via the unified pipeline.
- 默认会尝试加载：
  - 仓库内：`.claude/agents/*.md`
  - 用户目录：`%USERPROFILE%\\.claude\\agents\\lst97\\*.md`（可用 `--claude-agents-root` 或 `CLAUDE_AGENTS_ROOT` 覆盖）

## Artifact Assertion Guardrails（防误判）

- 当使用 `--only tests` 等“部分执行”模式时，`acceptance-summary` 可能不完整。
- 在 GdUnit/集成层读取工件做断言前，必须先做两层守卫：
  - `run_id` 绑定校验（只消费当前运行批次工件）。
  - 必需步骤完整性校验（例如 `headless-e2e-evidence` 与 `acceptance-executed-refs` 已成功且可追溯）。
- 若守卫未通过，测试应按“上下文不完整”路径退出，不得把历史工件或半成品工件当作失败依据。
- 依赖真实工件的硬断言，统一放在 `post-evidence-integration` 阶段执行，不放在纯单元测试中。
- 如新增工件型断言，同步更新：
  - `scripts/sc/_acceptance_orchestration.py`
  - `scripts/sc/_acceptance_evidence_steps.py`
  - 相关 GdUnit 集成用例的守卫逻辑

## Windows 用法示例

```powershell
# 任务分析（默认读当前 in-progress 任务）
py -3 scripts/sc/analyze.py --format report

# 构建（warn as error）
py -3 scripts/sc/build.py NewRouge.csproj --type dev --clean

# TDD 门禁编排
py -3 scripts/sc/build.py tdd --stage red --generate-red-test
py -3 scripts/sc/build.py tdd --stage green
py -3 scripts/sc/build.py tdd --stage refactor

# Unified task-level entry (test + acceptance + llm review)
py -3 scripts/sc/run_review_pipeline.py --task-id 10 --godot-bin "$env:GODOT_BIN" --security-profile host-safe

# Strict profile for release hardening
py -3 scripts/sc/run_review_pipeline.py --task-id 10 --godot-bin "$env:GODOT_BIN" --security-profile strict

# Optional: skip llm review (deterministic gates only)
py -3 scripts/sc/run_review_pipeline.py --task-id 10 --godot-bin "$env:GODOT_BIN" --skip-llm-review

# Git（智能提交，脚本会读取 .superclaude/commit-template.txt）
py -3 scripts/sc/git.py commit --smart-commit --task-ref "#10.1"
```

## CI 白名单到期预警阈值（WHITELIST_WARN_DAYS）

统一预警脚本：
- `py -3 scripts/python/warn_whitelist_expiry.py`

阈值解析顺序：
- `--warn-days`（命令行显式传入）
- 环境变量 `WHITELIST_WARN_DAYS`
- 默认值 `90`

当前 Windows CI 工作流已设置：
- `WHITELIST_WARN_DAYS=90`

说明：
- 该检查是 **soft warning**，仅预警不阻断流水线。
- 阻断仍由 `forbid_manual_sc_triplet_examples.py` 的 hard gate + whitelist metadata require 负责。

## Lightweight Convention (Single Developer)

- If any summary field/structure changes under `scripts/sc`, update the matching schema in `scripts/sc/schemas/*.schema.json` in the same change set.
- After this type of change, run at least once: `py -3 scripts/sc/run_review_pipeline.py --task-id 1 --dry-run --skip-llm-review`.
- Do not commit summary-contract changes if this minimal self-check fails.
