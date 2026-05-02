# Repository Guide

本文件是 `sanguo` 的路由层，不承载大段细节。稳定规则放到 `docs/agents/**`、`docs/workflows/**`、`docs/adr/**`、`docs/architecture/**`。

## 项目标识

- Repository: `sanguo`
- Product: Windows-only Godot 4.5.1 + C# 单机项目
- 默认交付姿态: `fast-ship`
- 默认安全姿态: `host-safe`
- 升级对齐基线: `docs/workflows/business-repo-upgrade-guide.md`

## 不可协商规则

- 与用户沟通统一使用中文。
- 默认环境是 Windows，命令必须可在 Windows 执行。
- 文档读写统一 UTF-8。
- 不使用 Emoji。
- 代码、脚本、测试、注释、打印文本统一英文。
- 日志、审计和证据统一放在 `logs/**`。
- 非 trivial 任务必须显式分步并持续更新进度。
- 不保留无用兼容层，过期路径应清理。
- 若存在未修复 `Needs Fix`，必须先记录到 `decision-logs/**`，并在 `execution-plans/**` 写明后续修复入口与证据路径。

## Context Reset 后的启动顺序

1. `README.md`
2. `docs/agents/00-index.md`
3. `docs/agents/01-session-recovery.md`
4. `docs/PROJECT_DOCUMENTATION_INDEX.md`
5. `docs/agents/13-rag-sources-and-session-ssot.md`
6. `DELIVERY_PROFILE.md`
7. `docs/testing-framework.md`
8. `docs/agents/16-directory-responsibilities.md`
9. `docs/workflows/prototype-lane.md`
10. `execution-plans/` 最新文件
11. `decision-logs/` 最新文件
12. 若已有审查流水线结果，读取 `logs/ci/<date>/sc-review-pipeline-task-<task-id>/latest.json`

## 权威来源

优先使用以下来源，不要随意重建索引。

- Taskmaster 三联:
  - `.taskmaster/tasks/tasks.json`
  - `.taskmaster/tasks/tasks_back.json`
  - `.taskmaster/tasks/tasks_gameplay.json`
- PRD:
  - `.taskmaster/docs/prd.txt`
  - `docs/prd/**`
- ADR:
  - `docs/adr/ADR-*.md`
  - `docs/architecture/ADR_INDEX_GODOT.md`
- Base 架构:
  - `docs/architecture/base/**`
- Overlay:
  - `docs/architecture/overlays/<PRD-ID>/08/**`
- 测试规则:
  - `docs/testing-framework.md`
- 交付与执行协议:
  - `DELIVERY_PROFILE.md`
  - `docs/workflows/run-protocol.md`
  - `docs/workflows/local-hard-checks.md`

## 核心入口

- 本地硬检查:
  - `py -3 scripts/python/dev_cli.py run-local-hard-checks --godot-bin <godot-bin>`
- 任务恢复（规范入口）:
  - `py -3 scripts/python/dev_cli.py resume-task --task-id <task-id>`
- 第六章重跑路由（先读工件再决定 6.7/6.8/止损）:
  - `py -3 scripts/python/dev_cli.py chapter6-route --task-id <task-id> --recommendation-only`
- 任务级统一评审流水线:
  - `py -3 scripts/sc/run_review_pipeline.py --task-id <task-id> --godot-bin <godot-bin>`
- 恢复文档校验:
  - `py -3 scripts/python/validate_recovery_docs.py --dir all`
- 门禁聚合:
  - `py -3 scripts/python/run_gate_bundle.py --mode hard --task-files .taskmaster/tasks/tasks_back.json .taskmaster/tasks/tasks_gameplay.json`

## Recovery Stop-Loss Signals

- `rerun_guard`: 确定性路径已经给出停止信号，不要盲目重开 `6.7`。
- `llm_retry_stop_loss`: 确定性已绿，且首轮长时 LLM 已超时；优先走窄化收敛而非全量重跑。
- `sc_test_retry_stop_loss`: 同一运行内重复单测重试已证明无效；先修单测根因再继续。
- `waste_signals`: 在已知单测/根因失败后仍发生引擎链路消耗；应先止损再执行后续步骤。

## 架构与契约规则

- 契约 SSoT 在 `Game.Core/Contracts/**`。
- 契约代码必须 BCL-only，不得引用 `Godot.*`。
- 领域逻辑在 `Game.Core/**`。
- Godot 适配在 `Game.Godot/**` 与 adapter 层。
- 功能纵切仅放在 `docs/architecture/overlays/<PRD-ID>/08/**`。
- 若阈值、契约、安全口径、发布策略改变，必须新增或 supersede ADR。

## 测试规则

- 领域逻辑: xUnit（`Game.Core.Tests/**`）。
- 场景与引擎胶水: GdUnit4（`Tests.Godot/**`）。
- 禁止通过关闭测试拿绿灯。
- acceptance 条目必须有 `Refs:`，并与 tasks 视图与 overlay 回链一致。

## 任务视图规则

- 真实任务文件在 `.taskmaster/tasks/**`。
- 跨文件映射固定:
  - `tasks.json.master.tasks[].id`
  - `tasks_back.json[].taskmaster_id`
  - `tasks_gameplay.json[].taskmaster_id`
- `semantic_review_tier` 必须写入真实视图文件，不仅是示例文件。

## 文档规则

- 保持仓库标识为 `sanguo`，清理过期模板名与无效示例。
- 不在 overlay 复制 Base/ADR 的阈值正文。
- 契约字段用路径引用，不做文档内重复粘贴。

## Prototype Lane Entrypoint

- 文档：`docs/workflows/prototype-lane.md`
- Playbook：`docs/workflows/prototype-lane-playbook.md`
- TDD 细化：`docs/workflows/prototype-tdd.md`
- 正式入口：`py -3 scripts/python/dev_cli.py run-prototype-tdd --slug <slug> --stage <red|green|refactor> --dotnet-target <path> --filter <Expr>`

## Chapter 7 UI Wiring Entries

- [Chapter 7 Profile Guide](docs/workflows/chapter7-profile-guide.md)
- [Chapter 7 UI Wiring GDD](docs/gdd/ui-gdd-flow.md)
- `py -3 scripts/python/dev_cli.py run-chapter7-ui-wiring --delivery-profile <profile>`
- `py -3 scripts/python/dev_cli.py apply-chapter7-status-patch --patch logs/ci/<date>/chapter7-ui-wiring/task-status-patch.json --dry-run`
