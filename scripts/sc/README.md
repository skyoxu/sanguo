# sc 兼容脚本（SuperClaude 命令等价实现）

这组脚本用于在 **Codex CLI** 环境下，提供类似 SuperClaude `/sc:*` 的“可执行入口”（但不是 Codex 的自定义 slash command）。

设计原则：
- 命令本体放在仓库内（可复用、可审计、可复现），避免把关键流程写死在聊天提示里。
- 所有运行输出统一落盘到 `logs/ci/<YYYY-MM-DD>/`，便于取证与排障。
- 默认遵循安全止损：高风险 Git 操作必须显式确认。

## “当前任务”从哪里来

- 默认优先读取 `.taskmaster/tasks/tasks.json` 中第一个 `status == "in-progress"` 的任务；模板仓缺少真实 triplet 时回退到 `examples/taskmaster/tasks.json`。
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
- `sc-review-pipeline` also writes `run-events.jsonl`, `harness-capabilities.json`, task-scoped `latest.json`, stable `logs/ci/active-tasks/task-<id>.active.{json,md}`, and supports on-demand `approval-request.json` / `approval-response.json` protocol files.

单元测试与覆盖率固定落盘到：`logs/unit/<YYYY-MM-DD>/`（由 `scripts/python/run_dotnet.py` 生成）。

## Task Recovery Before Another Full Rerun

在重新执行 `run_review_pipeline.py` 或 Chapter 6 的 `6.7 / 6.8` 之前，先走恢复链，而不是直接重跑：

- 先读 `logs/ci/active-tasks/task-<id>.active.md`，它是最短恢复摘要。
- 再执行 `py -3 scripts/python/dev_cli.py resume-task --task-id <id>`，读取 `Latest reason`、`Latest run type`、`Latest reuse mode`、`Latest artifact integrity`、`Chapter6 next action`、`Chapter6 blocked by`。
- 需要深挖时，再执行 `py -3 scripts/python/inspect_run.py --kind pipeline --task-id <id>`。

高价值止损口径：

- 若恢复链显示 `run_type = planned-only` 或 `reason = planned_only_incomplete`，该 bundle 只能当证据，不能直接 reopen `6.7` / `6.8`。
- 若 `Chapter6 blocked by = artifact_integrity`，先回退到上一轮真实 producer bundle，再决定是否继续。
- 若出现 `llm_retry_stop_loss`，优先走窄路径收敛 LLM 结果，不要再付一整轮 deterministic 成本。
- 若出现 `sc_test_retry_stop_loss`，说明同 run 的 unit 根因已被证明，先修根因，不要重复同参重跑。
- 若 `recommended_action = needs-fix-fast`，优先做定向 closure，不要再盲目开整轮 `6.7`。
- If `active-task`, `resume-task`, or project-health already exposes `recommended_action_why`, use it to choose between `inspect`, `resume`, and `needs-fix-fast` before paying for another rerun.

## TDD 门禁编排（重要说明）

`py -3 scripts/sc/build.py tdd ...` 是“门禁编排器”，不是自动生成业务代码的生成器：

- `--stage red`：可选生成红灯测试骨架（默认路径：`Game.Core.Tests/Tasks/Task<id>RedTests.cs`）
- `--stage green`：提示你把最小实现写到正确的层（通常是 `Game.Core/**`）
- `--stage refactor`：运行命名/回链/契约一致性等检查，确保改动可控

契约护栏（强制止损）：
- `tdd` 会快照 `Game.Core/Contracts/**/*.cs`；若检测到新增/修改契约文件会直接失败
- 若确实需要新增契约：应先补齐 ADR/Overlay/Test-Refs，再继续 TDD

## Generate Tests From Acceptance Refs

`scripts/sc/llm_generate_tests_from_acceptance_refs.py` generates missing test files from task acceptance `Refs:` entries and only allows repo-relative `.cs` / `.gd` test paths.

- Every generated file must include the matching `ACC:T<id>.<n>` anchors.
- Before long or mixed-surface generation, run `scripts/sc/check_tdd_execution_plan.py` first. It scores complexity from missing refs, mixed `.cs` / `.gd` targets, `red-first`, `verify auto|all`, anchor count, and test-root spread; `--execution-plan-policy draft` can auto-create a minimal `execution-plan`.
- C# anchors must appear within 5 lines above `[Fact]` / `[Theory]`; GDScript anchors must appear within 5 lines above `func test_...`.
- `--tdd-stage red-first` is a strict red mode.
  - If the run creates any new `.cs` tests, it forces task-scoped unit verification.
  - If the run creates any new `.gd` tests, it forces task-scoped `all --skip-smoke` verification.
  - Unexpected green runs or compile errors fail the whole generation step.
- Generated C# content is checked deterministically before write:
  - file name must be `PascalCase + Tests.cs`
  - class name must be PascalCase and match the file stem
  - test methods must use `ShouldX_WhenY`
  - local variables must use camelCase
- Internal helper ownership:
  - `_acceptance_testgen_llm.py`: prompt building and primary-ref selection
  - `_acceptance_testgen_flow.py`: task context / refs collection and verify orchestration
  - `_acceptance_testgen_quality.py`: deterministic naming and content validation
  - `_acceptance_testgen_red.py`: strict-red outcome classification (`unexpected_green`, `compile_error`, real red)

Examples:

```powershell
# Pre-check whether this task should create or require an execution plan first
py -3 scripts/sc/check_tdd_execution_plan.py --task-id 11 --tdd-stage red-first --verify auto --execution-plan-policy warn

# Auto-draft an execution plan when the complexity threshold is hit
py -3 scripts/sc/check_tdd_execution_plan.py --task-id 11 --tdd-stage red-first --verify auto --execution-plan-policy draft

# Normal scaffold generation
py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id 11 --verify unit

# Strict red-first generation for new tests
py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id 11 --tdd-stage red-first --verify auto --godot-bin "$env:GODOT_BIN"
```

## Semantic Review Tier Maintenance

Use these Python helpers when you want task views to carry an explicit `semantic_review_tier` policy instead of relying only on runtime delivery-profile defaults.

- `scripts/python/backfill_semantic_review_tier.py`
  - Fills or normalizes `semantic_review_tier` in `tasks_back.json` / `tasks_gameplay.json`.
  - Default `--mode conservative` only writes safe floors (`auto` / `full`) and avoids freezing profile-derived runtime defaults into task files.
  - Template repo behavior: prefer real `.taskmaster/tasks/*.json`; fall back to `examples/taskmaster/*` when the real triplet is missing.
- `scripts/python/validate_semantic_review_tier.py`
  - Enforces the field name `semantic_review_tier`.
  - Enforces legal values only.
  - Enforces consistency with the current computed suggestion.
  - Enforces no cross-view drift between `tasks_back` and `tasks_gameplay` for the same task.

Examples:

```powershell
# Dry-run conservative suggestions
py -3 scripts/python/backfill_semantic_review_tier.py

# Write conservative backfill into task views
py -3 scripts/python/backfill_semantic_review_tier.py --write

# Validate current task-view tiers
py -3 scripts/python/validate_semantic_review_tier.py
```

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
  - task-scoped unit coverage 若为 `0.0%`，默认直接失败，不再自动回退到全量 `dotnet test`；只有显式传 `--allow-full-unit-fallback` 才保留旧行为。
- 性能门禁（可选硬门）：解析最新 `logs/ci/**/headless.log` 的 `[PERF] ... p95_ms=...` 并与阈值比较
  - 启用方式：`--perf-p95-ms <ms>` 或设置环境变量 `PERF_P95_THRESHOLD_MS=<ms>`
  - 快捷方式：`--require-perf`（legacy）：等价于启用性能硬门禁，阈值取 `PERF_P95_THRESHOLD_MS`，否则默认 20ms（口径见 ADR-0015）
- 交付档位（建议显式）：
  - `--delivery-profile playable-ea`：最轻门禁，优先验证可玩性；默认派生 `security-profile=host-safe`；`agent_review.mode=skip`
  - `--delivery-profile fast-ship`：快速交付档位；默认派生 `security-profile=host-safe`；`agent_review.mode=warn`
  - `--delivery-profile standard`：标准收口档位；默认派生 `security-profile=strict`；`agent_review.mode=require`
  - 解析顺序：CLI `--delivery-profile` > `DELIVERY_PROFILE` > `scripts/sc/config/delivery_profiles.json` 中的 `default_profile`（当前为 `fast-ship`）
  - `--security-profile` 仅用于显式覆写派生结果；解析顺序：CLI > `SECURITY_PROFILE` > 由 `delivery-profile` 派生

  - `run_review_pipeline.py` normalizes agent-review verdicts into marathon guidance: isolated `needs-fix` -> `resume`, cross-step `needs-fix` -> `refresh`, and cross-step `block` or high-severity integrity issues -> `fork`; these hints only update sidecars and do not rewrite `summary.json`.
  - Noise guard: a single `medium` structural finding does not escalate by itself; escalation to `refresh` requires cross-step or cross-axis spread, or the structural category reaching `high`; `artifact-integrity`, `summary-integrity`, and `schema-integrity` prefer `fork`.
可选：如果你仍希望保留“LLM 口头审查”的等价体验（但不建议作为硬门禁），使用：
`scripts/sc/llm_review.py` writes outputs to `logs/ci/<YYYY-MM-DD>/sc-llm-review/`; prefer calling it via the unified pipeline.
- `agent-review.json` now includes top-level `explain` fields so a later agent can read the recommended action and rationale without re-deriving the category rules.
- 默认会尝试加载：
  - 仓库内：`.claude/agents/*.md`
  - 用户目录：`%USERPROFILE%\\.claude\\agents\\lst97\\*.md`（可用 `--claude-agents-root` 或 `CLAUDE_AGENTS_ROOT` 覆盖）

## Overlay Generation (PRD -> Overlay 08)

Use the overlay generator to turn one PRD wave into candidate pages under `docs/architecture/overlays/<PRD-ID>/08/`, with prompts, outputs, and diffs written to `logs/ci/<YYYY-MM-DD>/`.

Entry points:
- `py -3 scripts/sc/llm_generate_overlays_batch.py --prd <path> --prd-id <PRD-ID> --prd-docs <csv> --page-family core --page-mode scaffold --dry-run --batch-suffix <wave>-core-dryrun`
- `py -3 scripts/sc/llm_generate_overlays_from_prd.py --prd <path> --prd-id <PRD-ID> --prd-docs <csv> --page-filter <page>.md --page-mode scaffold --run-suffix <wave>-fix1`

Rules:
- Every path listed in `--prd-docs` is treated as required input; missing files hard-fail the run.
- Use `batch` for family-level review and `single-page` for repair/debug.
- Default flow is `dry-run -> simulate -> single-page repair -> batch apply`.
- Detailed guidance lives in `docs/workflows/overlay-generation-quickstart.md` and `docs/workflows/overlay-generation-sop.md`.

## Artifact Assertion Guardrails（防误判）

- 当使用 `--only tests` 等“部分执行”模式时，`acceptance-summary` 可能不完整。
- 在 GdUnit/集成层读取工件做断言前，必须先做两层守卫：
  - `run_id` 绑定校验（只消费当前运行批次工件）。
  - 必需步骤完整性校验（例如 `headless-e2e-evidence` 与 `acceptance-executed-refs` 已成功且可追溯）。
- 若守卫未通过，测试应按“上下文不完整”路径退出，不得把历史工件或半成品工件当作失败依据。
- 依赖真实工件的硬断言，统一放在 `post-evidence-integration` 阶段执行，不放在纯单元测试中。
- 模板仓默认提供 Task 1 的环境证据后置硬门；复制到新项目后，如任务号或测试类名不同，可通过 `SC_POST_EVIDENCE_FILTER_TASK_<id>` 覆盖过滤器，或调整 `scripts/sc/_post_evidence_config.py`。
- `ci-windows.yml` 在模板仓缺少真实 `.taskmaster/tasks/*.json` 时会显式 skip 这层门禁；业务仓补齐真实 Taskmaster triplet 后即自动启用。
- 如新增工件型断言，同步更新：
  - `scripts/sc/_acceptance_orchestration.py`
  - `scripts/sc/_acceptance_evidence_steps.py`
  - 相关 GdUnit 集成用例的守卫逻辑

## Windows 用法示例

```powershell
# 任务分析（默认读当前 in-progress 任务）
py -3 scripts/sc/analyze.py --format report

# 构建（warn as error）
py -3 scripts/sc/build.py GodotGame.csproj --type dev --clean

# TDD 门禁编排
py -3 scripts/sc/build.py tdd --stage red --generate-red-test
py -3 scripts/sc/build.py tdd --stage green
# Unified task-level entry (test + acceptance + llm review + profile-aware agent-review sidecar)
py -3 scripts/sc/run_review_pipeline.py --task-id 10 --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship

# Standard profile for release hardening
py -3 scripts/sc/run_review_pipeline.py --task-id 10 --godot-bin "$env:GODOT_BIN" --delivery-profile standard

# Final closure pass for remaining Needs Fix items:
# force full deterministic checks + full reviewer set and disable fast-path shortcuts
py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id 10 --delivery-profile standard --final-pass

# Optional: explicit security override when you intentionally break the default mapping
py -3 scripts/sc/run_review_pipeline.py --task-id 10 --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship --security-profile strict

# Optional: skip llm review (deterministic gates only)
py -3 scripts/sc/run_review_pipeline.py --task-id 10 --godot-bin "$env:GODOT_BIN" --skip-llm-review

# Optional: if task-scoped unit coverage is 0.0%, allow one explicit repo-wide dotnet retry
py -3 scripts/sc/run_review_pipeline.py --task-id 10 --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship --allow-full-unit-fallback

# Retry a failing step once inside the same invocation
py -3 scripts/sc/run_review_pipeline.py --task-id 10 --godot-bin "$env:GODOT_BIN" --max-step-retries 1

# Bound one run with a wall-time stop-loss
py -3 scripts/sc/run_review_pipeline.py --task-id 10 --godot-bin "$env:GODOT_BIN" --max-wall-time-sec 1800

# Tighten or relax the context-refresh heuristic thresholds
py -3 scripts/sc/run_review_pipeline.py --task-id 10 --context-refresh-after-failures 2 --context-refresh-after-resumes 2 --context-refresh-after-diff-lines 200 --context-refresh-after-diff-categories 2

# Inspect and summarize the latest task-scoped recovery state before deciding resume/fork
# Or open logs/ci/active-tasks/task-<id>.active.md first for the shortest recovery summary
py -3 scripts/python/dev_cli.py resume-task --task-id 10

# Resume the latest task-scoped run after fixing the first blocking issue
py -3 scripts/sc/run_review_pipeline.py --task-id 10 --resume

# Fork the latest task-scoped run into a new run id while keeping the old artifacts immutable
py -3 scripts/sc/run_review_pipeline.py --task-id 10 --fork

# Fork from a specific source run id when you do not want the latest pointer
py -3 scripts/sc/run_review_pipeline.py --task-id 10 --fork --fork-from-run-id <old_run_id> --run-id <new_run_id>

# Abort the latest task-scoped run without executing more steps
py -3 scripts/sc/run_review_pipeline.py --task-id 10 --abort

# Git smart commit (reads .superclaude/commit-template.txt)
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

- If any summary field/structure or sidecar protocol changes under `scripts/sc`, update the matching schema in `scripts/sc/schemas/*.schema.json` in the same change set.
- After this type of change, run at least once: `py -3 scripts/sc/run_review_pipeline.py --task-id 1 --dry-run --skip-llm-review`.
- Do not commit summary-contract or sidecar-contract changes if this minimal self-check fails.
