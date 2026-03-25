# workflow.md

## 0. 适用范围

这是本仓库的日常可执行工作流。

- 操作系统：Windows
- Shell：PowerShell
- Python 启动器：`py -3`
- 下方命令均为单行、PowerShell 安全命令
- 真实项目任务文件必须位于 `.taskmaster/tasks/`
- `examples/taskmaster/**` 只作为模板 fallback，不是业务仓 SSoT
- 默认的任务级主入口是 `scripts/sc/run_review_pipeline.py`
- 日常工作中不要手工串 `scripts/sc/test.py + scripts/sc/acceptance_check.py + scripts/sc/llm_review.py`

## 1. 全局规则

### 1.1 先恢复，再继续

按以下顺序恢复：

1. 先读 `AGENTS.md` 和 `docs/agents/00-index.md`
2. 如果存在，先读 `logs/ci/active-tasks/task-<id>.active.md`
3. 执行 `py -3 scripts/python/dev_cli.py resume-task --task-id <id>`
4. 只有当 recovery summary 仍然不够时，再执行 `py -3 scripts/python/inspect_run.py --kind pipeline --task-id <id>`

### 1.2 先选 Delivery Profile

在进入较大工作量或重复工作前，先确定 `DELIVERY_PROFILE`。

- `playable-ea`：最快的可玩性验证模式
- `fast-ship`：默认日常模式
- `standard`：更严格的收敛模式

默认安全映射：

- `playable-ea` -> `host-safe`
- `fast-ship` -> `host-safe`
- `standard` -> `strict`

参考：`DELIVERY_PROFILE.md`

### 1.3 Serena 是加速器，不是阻塞器

当你需要 symbol lookup、reference tracing 或更稳的重构上下文时，使用 Serena MCP。
如果 Serena 不可用，继续走确定性工具链，不要因此阻塞任务。
可选本地笔记可以写入 UTF-8 的 `taskdoc/<id>.md`。

### 1.4 Prototype work 不进入正式任务环

如果工作仍处于探索阶段、尚未准备进入正式 Taskmaster 跟踪，请先走 prototype lane。
参考：`docs/workflows/prototype-lane.md`

## 2. Phase 0：仓库初始化（Repository Bootstrap）

从模板创建新仓后，先执行这一阶段。

### 2.1 清理名称和路径残留

至少检查并修改：

- `README.md`
- `AGENTS.md`
- `docs/**`
- `.github/**`
- `project.godot`
- workflow names、release names、project paths、PRD ids

目标：

- 不残留旧仓库名
- 不残留旧技术栈语义
- 不残留失效入口链接

### 2.2 重建入口索引

确认以下入口文档已指向新仓当前状态：

- `README.md`
- `AGENTS.md`
- `docs/PROJECT_DOCUMENTATION_INDEX.md`
- `docs/agents/00-index.md`

### 2.3 立刻运行仓库级硬检查

不要等到 commit 前再跑。
这是新仓在“完成改名、路径清理、入口索引修复”之后的第一个完整验证点。

```powershell
py -3 scripts/python/dev_cli.py run-local-hard-checks --godot-bin "$env:GODOT_BIN"
py -3 scripts/python/inspect_run.py --kind local-hard-checks
```

这第一次运行的价值：

- 刷新 repo health dashboard
- 提前暴露缺失的真实 `.taskmaster/tasks/*.json`
- 在正式进入任务流之前，发现 base 文档泄漏或 pure-core boundary 漂移

### 2.4 可选：启动本地 project-health 页面服务

如果你希望在浏览器里稳定查看本仓的健康页，而不是只打开静态文件，可启动本地服务：

```powershell
py -3 scripts/python/dev_cli.py serve-project-health
```

或者边扫描边起服务：

```powershell
py -3 scripts/python/dev_cli.py project-health-scan --serve
```

说明：

- 服务仅绑定 `127.0.0.1`
- 默认端口范围是 `8765-8799`
- 同仓存在活跃服务时会复用
- 选中的 URL 和 PID 会写入 `logs/ci/project-health/server.json`

## 3. Phase 1：任务三联（Task Triplet）初始化

### 3.1 准备 planning inputs

准备项目需要的 PRD、GDD，以及任何 traceability / rules supporting docs。

### 3.2 构建 authoritative triplet

真实项目的标准形态：

- `.taskmaster/tasks/tasks.json`
- `.taskmaster/tasks/tasks_back.json`
- `.taskmaster/tasks/tasks_gameplay.json`

如果 `tasks_back.json` / `tasks_gameplay.json` 已存在，而你需要重建 `tasks.json`，执行：

```powershell
py -3 scripts/python/build_taskmaster_tasks.py
```

### 3.3 校验 triplet baseline

```powershell
py -3 scripts/python/task_links_validate.py
py -3 scripts/python/check_tasks_all_refs.py
py -3 scripts/python/validate_task_master_triplet.py
```

### 3.4 提前标准化 semantic review tier

推荐默认值：

```powershell
py -3 scripts/python/backfill_semantic_review_tier.py --mode conservative --write
py -3 scripts/python/validate_semantic_review_tier.py --mode conservative
```

默认使用 `conservative`。除非你明确要把 profile 的运行时默认值固化进 task views，否则不要提前 materialize。

## 4. Phase 2：Overlays 与 Contracts 基线

### 4.1 只有 triplet 有效后，才生成 overlay skeletons

推荐顺序：

1. batch dry-run
2. batch simulate
3. 对 outlier 做 single-page repair
4. limited apply

Batch dry-run：

```powershell
py -3 scripts/sc/llm_generate_overlays_batch.py --prd <prd-main.md> --prd-id <PRD-ID> --prd-docs <prd-extra-a.md>,<prd-extra-b.md> --page-family core --page-mode scaffold --timeout-sec 1200 --dry-run --batch-suffix first-core-dryrun
```

Batch simulate：

```powershell
py -3 scripts/sc/llm_generate_overlays_batch.py --prd <prd-main.md> --prd-id <PRD-ID> --prd-docs <prd-extra-a.md>,<prd-extra-b.md> --page-family core --page-mode scaffold --timeout-sec 1200 --batch-suffix first-core-sim
```

Single-page repair：

```powershell
py -3 scripts/sc/llm_generate_overlays_from_prd.py --prd <prd-main.md> --prd-id <PRD-ID> --prd-docs <prd-extra-a.md>,<prd-extra-b.md> --page-filter <overlay-file.md> --page-mode scaffold --timeout-sec 1200 --run-suffix fix-page-1
```

Limited apply：

```powershell
py -3 scripts/sc/llm_generate_overlays_batch.py --prd <prd-main.md> --prd-id <PRD-ID> --prd-docs <prd-extra-a.md>,<prd-extra-b.md> --pages _index.md,ACCEPTANCE_CHECKLIST.md,08-rules-freeze-and-assertion-routing.md --page-mode scaffold --timeout-sec 1200 --apply --batch-suffix apply-core
```

止损规则：

- 第一轮不要全量 apply
- 不要在同一步里直接改 acceptance
- 这一阶段只处理 overlay，不混入别的语义修复

### 4.2 Apply 后冻结 overlay refs

```powershell
py -3 scripts/python/sync_task_overlay_refs.py --prd-id <PRD-ID> --write
py -3 scripts/python/validate_overlay_execution.py --prd-id <PRD-ID>
py -3 scripts/python/check_tasks_all_refs.py
py -3 scripts/python/validate_task_master_triplet.py
```

### 4.3 创建或调整 contract skeletons

使用：

- `docs/workflows/contracts-template-v1.md`
- `docs/workflows/templates/contracts-event-template-v1.md`
- `docs/workflows/templates/contracts-dto-template-v1.md`
- `docs/workflows/templates/contracts-interface-template-v1.md`

规则：

- contracts 必须位于 `Game.Core/Contracts/**`
- contracts 中不能依赖 Godot
- 必须带 XML docs
- overlays 必须回链到 contract paths

### 4.4 固化 contract baseline

```powershell
py -3 scripts/python/validate_contracts.py
py -3 scripts/python/check_domain_contracts.py
dotnet test Game.Core.Tests/Game.Core.Tests.csproj
```

## 5. Phase 3：按条件进入语义稳定化（Conditional Semantics Stabilization）

这是条件阶段，不是每个任务都要跑。

只有在以下情况明显出现时才进入：

- acceptance 质量明显不足
- refs 正在漂移
- subtasks 覆盖不清晰
- 重复的 `Needs Fix` 指向 semantics，而不是代码实现

### 5.1 单任务轻量 lane

抽 obligations：

```powershell
py -3 scripts/sc/llm_extract_task_obligations.py --task-id <id> --delivery-profile fast-ship --reuse-last-ok --explain-reuse-miss
```

对齐 acceptance semantics：

```powershell
py -3 scripts/sc/llm_align_acceptance_semantics.py --task-ids <id> --apply --strict-task-selection
```

检查 subtasks coverage：

```powershell
py -3 scripts/sc/llm_check_subtasks_coverage.py --task-id <id> --strict-view-selection
```

对小范围 task 运行 batch semantic gate：

```powershell
py -3 scripts/sc/llm_semantic_gate_all.py --task-ids <id> --max-needs-fix 0 --max-unknown 3
```

先 dry-run 填 acceptance refs：

```powershell
py -3 scripts/sc/llm_fill_acceptance_refs.py --task-id <id>
```

确认后写回 refs：

```powershell
py -3 scripts/sc/llm_fill_acceptance_refs.py --task-id <id> --write
```

再验证收敛：

```powershell
py -3 scripts/sc/llm_fill_acceptance_refs.py --task-id <id>
```

### 5.2 Batch instability lane

只有当多个任务都表现出 obligations extraction 不稳定时才使用。

```powershell
py -3 scripts/python/run_obligations_jitter_batch5x3.py --task-ids 1,2,3 --batch-size 3 --rounds 3 --timeout-sec 420 --garbled-gate on --auto-escalate on --escalate-max-runs 3 --max-schema-errors 5 --reuse-last-ok --explain-reuse-miss
```

```powershell
py -3 scripts/python/run_obligations_freeze_pipeline.py --task-ids 1,2,3 --batch-size 3 --rounds 3 --timeout-sec 420 --garbled-gate on --auto-escalate on --reuse-last-ok --explain-reuse-miss
```

默认不要直接 promote freeze baseline。

## 6. Phase 4：单任务日常循环（Single Task Daily Loop）

这是主日常路径。

### 6.1 先恢复状态

```powershell
py -3 scripts/python/dev_cli.py resume-task --task-id <id>
```

只有确实需要时再执行：

```powershell
py -3 scripts/python/inspect_run.py --kind pipeline --task-id <id>
```

失败任务或恢复任务时，优先查看这些文件：

- `summary.json`
- `execution-context.json`
- `repair-guide.json`
- `repair-guide.md`
- `agent-review.json`
- `run-events.jsonl`
- `logs/ci/active-tasks/task-<id>.active.md`

### 6.2 只有在有价值时才创建 recovery documents

Execution plan：

```powershell
py -3 scripts/python/dev_cli.py new-execution-plan --title "<topic>" --task-id <id>
```

Decision log：

```powershell
py -3 scripts/python/dev_cli.py new-decision-log --title "<topic>" --task-id <id>
```

只有当它们能明显提升恢复效率，或让真实 tradeoff 可审计时才创建。

### 6.3 TDD preflight 决策

推荐默认：

```powershell
py -3 scripts/sc/check_tdd_execution_plan.py --task-id <id> --tdd-stage red-first --verify unit --execution-plan-policy draft
```

### 6.4 Red stage

偏 unit 的 red-first：

```powershell
py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id <id> --tdd-stage red-first --verify unit
```

混合 `.cs` + `.gd` 或需要 Godot-aware verification：

```powershell
py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id <id> --tdd-stage red-first --verify auto --godot-bin "$env:GODOT_BIN"
```

### 6.5 Green stage

```powershell
py -3 scripts/sc/build.py tdd --task-id <id> --stage green
```

### 6.6 Refactor stage

```powershell
py -3 scripts/sc/build.py tdd --task-id <id> --stage refactor
```

`build.py tdd` 已经内置 task preflight、`sc-analyze` 和必需的 task-context validation。

### 6.7 统一任务级 review pipeline

日常默认：

```powershell
py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship
```

更重的收敛模式：

```powershell
py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile standard
```

快速可玩验证：

```powershell
py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile playable-ea
```

说明：

- 默认模板已经是 `scripts/sc/templates/llm_review/bmad-godot-review-template.txt`
- 除非你明确要覆盖默认映射，否则不要手工传 `--security-profile`
- 这个 pipeline 会写 sidecars、latest pointers、active-task summaries、repair guidance，以及 technical debt sync outputs

### 6.8 清理 Needs Fix

日常快速清理：

```powershell
py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id <id> --max-rounds 1 --rerun-failing-only --time-budget-min 20 --agents code-reviewer,test-automator,semantic-equivalence-auditor
```

标准清理：

```powershell
py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id <id> --max-rounds 2 --rerun-failing-only --time-budget-min 30
```

安全敏感清理：

```powershell
py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id <id> --security-profile strict --max-rounds 2 --rerun-failing-only --time-budget-min 45 --agents code-reviewer,security-auditor,test-automator,semantic-equivalence-auditor
```

### 6.9 Commit 前的仓库级验证

```powershell
py -3 scripts/python/dev_cli.py run-local-hard-checks --godot-bin "$env:GODOT_BIN"
py -3 scripts/python/inspect_run.py --kind local-hard-checks
```

如果你想在浏览器里持续观察 project-health 页面，可再执行：

```powershell
py -3 scripts/python/dev_cli.py serve-project-health
```

## 7. Profile 快速指引

### 7.1 playable-ea

当主要目标是“尽快验证可玩性”时使用。

```powershell
py -3 scripts/sc/check_tdd_execution_plan.py --task-id <id> --tdd-stage red-first --verify unit --execution-plan-policy warn
py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id <id> --tdd-stage red-first --verify unit
py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile playable-ea
```

### 7.2 fast-ship

正常日常工作使用，这是默认推荐值。

```powershell
py -3 scripts/sc/check_tdd_execution_plan.py --task-id <id> --tdd-stage red-first --verify unit --execution-plan-policy draft
py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id <id> --tdd-stage red-first --verify unit
py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship
```

### 7.3 standard

跨切面、高风险、或 PR 前收敛时使用。

```powershell
py -3 scripts/sc/check_tdd_execution_plan.py --task-id <id> --tdd-stage red-first --verify auto --execution-plan-policy draft
py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id <id> --tdd-stage red-first --verify auto --godot-bin "$env:GODOT_BIN"
py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile standard
```

## 8. 止损规则（Stop-Loss Rules）

- 在 triplet 有效前，不要开始 overlays
- 默认不要跑重型 obligations freeze toolchain
- 在读取 sidecars 前，不要用聊天记录恢复
- 不要在 `standard` 上强行传 `--security-profile host-safe`；除非你明确要覆盖默认映射，否则让它自然落到 `strict`
- 不要为 `llm_fill_acceptance_refs.py` 虚构 `--dry-run` 参数；不带 `--write` 就是 dry-run
- 不要因为 Serena 暂时不可用就阻塞整项工作
- 不要把 `run-local-hard-checks` 拖到新仓迁移结束时才跑

## 9. 最佳默认路径（Best Default）

对本仓的大多数真实工作，使用这条默认路径：

1. 选择 `fast-ship`
2. 如果是继续任务，先 `resume-task`
3. `check_tdd_execution_plan.py --execution-plan-policy draft`
4. `llm_generate_tests_from_acceptance_refs.py --tdd-stage red-first`
5. `build.py tdd --stage green`
6. `build.py tdd --stage refactor`
7. `run_review_pipeline.py --delivery-profile fast-ship`
8. 只有当 pipeline 产出明确的 `Needs Fix` 时，再执行 `llm_review_needs_fix_fast.py`
9. commit 或 PR 前执行 `run-local-hard-checks`
