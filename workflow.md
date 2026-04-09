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
2. 先执行 `py -3 scripts/python/dev_cli.py resume-task --task-id <id>`
3. 如果 recovery summary 仍然不够，再读 `logs/ci/active-tasks/task-<id>.active.md`
4. 只有当 `resume-task` 与 `active-task` 仍不足以判断时，再执行 `py -3 scripts/python/inspect_run.py --kind pipeline --task-id <id>`

补充说明：
- `resume-task` 现在会汇总 `Latest reason`、`Latest run type`、`Latest reuse mode`、`Latest artifact integrity`、`Chapter6 next action`、`Chapter6 can skip 6.7`、`Chapter6 can go to 6.8`、`Chapter6 blocked by`。
- `resume-task` also surfaces `recommended_action_why`; if it already says `recommended_action = needs-fix-fast`, prefer targeted closure before any full rerun.
- `inspect_run.py --kind pipeline` 也会导出同一组 `latest_summary_signals` / `chapter6_hints`，用于判断是继续 `6.7`、转 `6.8`，还是先修 deterministic 根因。
- `run_review_pipeline.py --dry-run` 仍会在本次 `out_dir` 写 `summary/execution-context/repair-guide`，但不再发布 `latest.json` 或 `active-task` sidecars；不要把 dry-run 当作恢复指针。
- `inspect_run.py --kind pipeline --task-id <id>` 在解析自动恢复指针时，会跳过只来自 dry-run 的更新候选，回退到最近一轮真实可恢复 run。

- Recovery order now requires reading `Latest reason`, `Latest run type`, `Latest reuse mode`, and `Latest artifact integrity` before trusting the newest `latest.json` pointer.
- `logs/ci/active-tasks/task-<id>.active.md` 现在是 `resume-task` 之后的短指针补充视图；只有当 recovery summary 还需要更快的人读入口时再看它，并继续结合 `Latest reason`、`Latest run type`、`Latest artifact integrity` 与 `Diagnostics artifact_integrity` 一起判断。
- If recovery shows `Latest run type = planned-only`, `Latest reason = planned_only_incomplete`, or `Chapter6 blocked by = artifact_integrity`, treat the bundle as evidence only; do not reopen `6.7` or `6.8` from it.

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

这一组脚本的目标不是“把所有语义脚本都再跑一遍”，而是用最小必要的包装，快速判断某个任务或一段任务是否值得继续投入语义修复。

建议把 5.1 理解成三层：`核心必用`、`高级可选`、`内部机制`。日常使用时，只记住核心层即可。

#### 5.1.1 核心必用

1. 单任务或很小的临时批次：直接跑 wrapper

```powershell
py -3 scripts/python/run_single_task_light_lane.py --task-ids <id> --delivery-profile fast-ship
```

2. 长区间、多任务、需要隔离 `out-dir` 时：优先跑 batch coordinator

```powershell
py -3 scripts/python/run_single_task_light_lane_batch.py --task-id-start 101 --task-id-end 180 --batch-preset stable-batch --delivery-profile fast-ship --max-tasks-per-shard 12
```

3. 默认建议

- 普通长区间：`--batch-preset stable-batch`
- 更保守、希望更早停下：`--batch-preset long-batch`
- 单任务默认不要先调高级参数，先看 `summary.json` 和 dashboard

4. 默认行为口径

- `preflight_acceptance_extract_guard` 现在是 `extract` 之前的确定性前置守卫；它会先拦截明显缺少 acceptance / Refs / 硬门语义的任务，避免把时间浪费在注定失败的 extract 上
- preflight 通过不代表后续质量门被跳过；`extract`、`align`、`coverage`、`semantic_gate` 仍然会照常执行，质量口径不降低
- `extract` 仍然是第一道 LLM 判断点；如果它已经失败，后续步骤默认会自动降载
- 单任务下：`--downstream-on-extract-fail auto` 默认更偏保守续跑
- 多任务 batch 下：`auto` 默认更偏向尽快止损
- family-aware 策略已经接入；遇到 `timeout` 或 `SC_LLM_OBLIGATIONS status=fail` 这类高置信失败，会直接短路当前任务的低价值后续步骤

5. 恢复口径

- 同一个 `out-dir` 只适合同一批任务、同一 `delivery-profile`、同一 `align --apply` 模式
- 跨区间重跑时，换新的 `out-dir`，或者显式传 `--no-resume`
- 如果上次只是在后半段失败，而前缀步骤已经成功，可以用：

```powershell
py -3 scripts/python/run_single_task_light_lane.py --task-ids <id> --delivery-profile fast-ship --resume-failed-task-from first-failed-step
```

- 如果你是在不同区间、不同 `delivery-profile`，或不同 `align --apply` 模式之间切换，为了避免同一个 `out-dir` 的进度字段被旧批次污染，显式换一个输出目录并关闭 resume：

```powershell
py -3 scripts/python/run_single_task_light_lane.py --task-ids <id> --delivery-profile fast-ship --out-dir logs/ci/<date>/single-task-light-lane-t<id>-fresh --no-resume
```

- 如果这一轮的目标只是尽快定位“当前任务最先卡死在哪一步”，而不是把后续低价值步骤也全跑完，可额外加：

```powershell
py -3 scripts/python/run_single_task_light_lane.py --task-ids <id> --delivery-profile fast-ship --stop-on-step-failure
```

#### 5.1.2 高级可选

只有在以下场景明显出现时，再动这些参数：

- 长批次经常在中后段整体恶化
- `extract` 超时明显堆积
- 同一种 extract 失败 family 连续出现
- 你需要做“只读诊断”而不是继续写回 refs

可选能力：

- `--rolling-extract-policy warn|degrade|stop`
  - `warn`：只提示
  - `degrade`：后续 shard 自动切到更保守模式
  - `stop`：达到阈值后直接停止剩余 shard
- `--rolling-family-policy off|warn|stop`
  - 用于连续相同 extract failure family 的止损
- `--rolling-timeout-backoff-*`
  - 当前一个 shard 的 extract timeout 明显升高时，自动增大下一个 shard 的 LLM timeout，并缩小 shard size
- `--fill-refs-mode none|dry|write-verify`
  - 长批次一般保持 `none`
  - 真正需要看 refs 写回效果时，才切到 `dry` 或 `write-verify`
- `--no-align-apply`
  - 用于只读诊断，不做对齐写回

建议：如果你不是在跑长批次，不要先动这些参数。

#### 5.1.3 内部机制

以下内容保留在实现里，但不需要成为日常操作负担。

1. 单任务 wrapper 会：

- 把共享 inner artifacts 快照到 `tNNNN--<step>.artifacts/`
- 在顶层 `summary.json` 里聚合：
  - `failure_category_*`
  - `extract_fail_bucket_*`
  - `extract_fail_signature_*`
  - `extract_fail_family_*`
  - `prompt_trimmed_task_ids`
  - `semantic_gate_budget_hits`

2. batch coordinator 会：

- 把每个 shard 的结果写到 `shards/`
- 把任务级合并结果写到 `merged/summary.json`
- 把顶层 `summary.json` 当作一页式 batch dashboard
- 输出：
  - `family_hotspots`
  - `quarantine_ranges`
  - `extract_family_recommended_actions`

3. 现在最重要的诊断口径是 `family`，不是单条 `signature`

- `signature` 适合看“这一条到底报了什么”
- `family` 适合看“这一批任务为什么整体失败”
- dashboard 和批量排障时，优先看 family + recommended action

#### 5.1.4 何时不该继续加复杂度

如果一轮全量 5.1 日志里，绝大多数任务都还是 `first_failed_step = extract`，而且没有稳定出现第二类瓶颈，那么不要继续给 5.1 增加新 stop-loss。

这时更值钱的动作是：

- 修 obligations / task context
- 调整 extract prompt 或范围
- 调整 timeout / shard size
- 用 dashboard 看 `extract_family_recommended_actions`，而不是继续往 5.1 里堆逻辑
### 5.2 Batch instability lane

补充口径：
- 5.2 里每个任务在进入 `extract` 前，同样会先经过 `preflight_acceptance_extract_guard`
- preflight fail-fast 只是为了节省批量耗时，不替代后续真正的质量判定

只有当多个任务都表现出 obligations extraction 不稳定时才使用。

```powershell
py -3 scripts/python/run_obligations_jitter_batch5x3.py --task-ids 1,2,3 --batch-size 3 --rounds 3 --timeout-sec 420 --garbled-gate on --auto-escalate on --escalate-max-runs 3 --max-schema-errors 5 --reuse-last-ok --explain-reuse-miss
```

```powershell
py -3 scripts/python/run_obligations_freeze_pipeline.py --task-ids 1,2,3 --batch-size 3 --rounds 3 --timeout-sec 420 --garbled-gate on --auto-escalate on --reuse-last-ok --explain-reuse-miss
```

默认不要直接 promote freeze baseline。

复用已有 jitter 结果并把评估变成硬门：

```powershell
py -3 scripts/python/run_obligations_freeze_pipeline.py --skip-jitter --raw logs/ci/<date>/sc-llm-obligations-jitter-batch5x3-raw.json --require-judgable --require-freeze-pass
```

只有在你确认要推进 baseline 时，才显式放开 promote：

```powershell
py -3 scripts/python/run_obligations_freeze_pipeline.py --skip-jitter --raw logs/ci/<date>/sc-llm-obligations-jitter-batch5x3-raw.json --require-judgable --require-freeze-pass --approve-promote
```

## 6. Phase 4：单任务日常循环（Single Task Daily Loop）

这是主日常路径。

如需理解本章在 `T56` 实战中做过哪些优化、哪些脚本必须成批升级、以及旧项目如何完整对齐，请先读 `docs/workflows/chapter-6-t56-optimization-guide.md`。

### 6.1 先恢复状态

```powershell
py -3 scripts/python/dev_cli.py resume-task --task-id <id>
```

只有确实需要时再执行：

```powershell
py -3 scripts/python/inspect_run.py --kind pipeline --task-id <id>
```

只有在你需要把恢复证据稳定落盘，供后续脚本或人工继续消费时，显式输出：

```powershell
py -3 scripts/python/dev_cli.py resume-task --task-id <id> --out-json logs/ci/<date>/resume-task-<id>.json --out-md logs/ci/<date>/resume-task-<id>.md
py -3 scripts/python/inspect_run.py --kind pipeline --task-id <id> --out-json logs/ci/<date>/inspect-pipeline-<id>.json
```

失败任务或恢复任务时，优先查看这些文件：

- `summary.json`
- `execution-context.json`
- `repair-guide.json`
- `repair-guide.md`
- `agent-review.json`
- `run-events.jsonl`
- `logs/ci/active-tasks/task-<id>.active.md`

Recovery decision order:

1. Read `Latest reason`, `Latest run type`, `Latest reuse mode`, and `Latest artifact integrity` first.
2. Then read `Chapter6 next action`, `Chapter6 can skip 6.7`, `Chapter6 can go to 6.8`, and `Chapter6 blocked by`.
3. Only then decide whether to reopen the current run, move to 6.8, or start a fresh real run.

Hard stop-loss:

- If `Latest run type = planned-only` and `Latest reason = planned_only_incomplete`, treat it as a `planned-only terminal bundle`; it is not a resumable producer run.
- If `Chapter6 blocked by = artifact_integrity`, fall back to the previous real bundle first; if none exists, start a fresh real `6.7` instead of continuing `--resume` from the planned-only terminal state.
- If `active-task` or `inspect_run` reports `artifact_integrity_planned_only_incomplete`, do not enter `6.7` or `6.8` yet; fix artifact integrity first.

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

#### 6.3.1 复杂任务判断标准

把 `check_tdd_execution_plan.py` 当作第一个轻量判断器，而不是手工凭感觉判断。

满足任意 2 条，默认按“复杂任务”处理：

- 缺失测试文件数 `>= 3`
- 同时涉及 `.cs` 和 `.gd`
- `--verify auto|all`
- acceptance anchors 总数 `>= 4`
- 涉及多个测试根目录
- 任务包含明显的契约 / 事件 / 重构 / 跨模块边界变化

复杂任务的默认后续动作：

1. 先创建或补充 `execution-plan`
2. 再判断是否需要 Serena MCP 语义检索
3. 只有在 Serena 检索结果会影响实现边界时，才把摘要写入 `taskdoc/<id>.md`

#### 6.3.2 什么时候触发 Serena MCP

`check_tdd_execution_plan.py` 只能判断“是否需要更多准备”，不能替代 Serena 语义查询。

只有当复杂度来自“代码语义不清”，才触发 Serena。满足任意 1 条即可：

- 你要扩展现有功能，但不确定是否已有同名 / 近似类、接口、服务或管理器
- 你要对齐事件契约、DTO、接口命名，担心违反现有 ADR / Contracts 约定
- 你要做 rename / refactor，需要知道跨文件引用位置
- 你要理解某个模块边界、依赖链、谁在调用谁
- 前一轮 `Needs Fix` 明确指出重复定义、边界误判、契约漂移或遗漏现有实现

以下情况通常不需要 Serena：

- 只是测试文件较多
- 只是 `.cs` + `.gd` 混合，但模块边界已经很清楚
- 只是 `verify=auto|all` 导致执行更重，而不是理解更难
- 只是需要补测试，不涉及现有实现复用、契约对齐或引用追踪

#### 6.3.3 Serena 执行动作与提示词模板

如果触发 Serena，按以下顺序执行。优先用符号级查询，不要先用全文扫描替代：

1. `find_symbol`：查相关 symbols，确认现有类 / 接口 / 服务是否已经存在
2. `search_for_pattern`：查接口定义或关键契约模式，了解现有约定
3. `find_symbol`：查事件契约 / DTO / contract constants，确认事件系统口径
4. `find_referencing_symbols`：查依赖引用，确认现有模块如何使用该符号

建议给 Codex / Serena 的执行提示词：

```text
当前任务先执行 Serena MCP 语义检索，再继续实现。

触发原因：这是复杂任务，且复杂度来自代码语义而不是单纯测试规模。

按以下顺序执行：
1. find_symbol 查找相关 symbols
2. search_for_pattern 查找接口定义或关键契约模式
3. find_symbol 查找事件契约 / DTO / contract constants
4. find_referencing_symbols 查找依赖引用链

输出要求：
- 只保留与当前任务直接相关的上下文
- 总结“已有实现 / 应复用内容 / 契约约束 / 主要引用方”
- 如果这些信息会影响实现边界，再使用 Python + UTF-8 写入 `taskdoc/<id>.md`
- 如果 Serena MCP 不可用，不要阻塞任务；直接继续第 6 章流程，并在 execution-plan 或 decision-log 里记一条 `Serena skipped`
```

#### 6.3.4 taskdoc 使用口径

`taskdoc/<id>.md` 现在是可选的本地上下文材料，不是第 6 章日常必产物。

只有在以下情况下才值得写：

- Serena 查询结果明显影响实现边界
- 你需要把“已有实现 / 契约口径 / 依赖链”固化给后续 red / green / review 使用
- 任务会跨会话，且仅靠 sidecars 不足以快速恢复语义上下文

### 6.4 Red stage

偏 unit 的 red-first：

```powershell
py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id <id> --tdd-stage red-first --verify unit
```

Refs 语义不足、需要 PRD 辅助判定测试归属时：

```powershell
py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id <id> --tdd-stage red-first --verify unit --include-prd-context --prd-context-path .taskmaster/docs/prd.txt
```

混合 `.cs` + `.gd` 或需要 Godot-aware verification：

```powershell
py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id <id> --tdd-stage red-first --verify auto --godot-bin "$env:GODOT_BIN"
```

说明：

- 新建测试文件较多时，首轮 red 要优先走最便宜的验证口径；不要因为“反正后面还要 green/refactor/review”就第一轮直接上重验证。
- 如果本轮新建 `.gd` 测试文件 `>= 2`，或任务明显属于 UI / scene flow / Godot 交互路径，默认先用 `--verify unit`；只有当你明确需要 Godot-aware red 证据时，才升级到 `--verify auto`。
- 不要把 `--verify all` 当作首轮 red 默认值。它只适用于：你已经有稳定的 task-scoped `.gd` refs，且前一轮 red 已经证明最小验证口径不够。
- 6.5 green 会强制读取最近一次 `sc-llm-acceptance-tests/summary-<task>.json`。
- 这份 summary 必须来自 `red-first`，且不能存在失败 ref。
- 如果 6.4 创建了新测试文件，还要求 `red_verify.status = ok`，否则 6.5 直接阻断。
- 当你在 6.4 使用 `--verify auto|all` 且带 `--task-id` 时，task-scoped GdUnit 现在必须能从任务视图解析出 `.gd` refs；不再静默回退到 `tests/Scenes` 等全量目录。
- 如果首轮 6.4 出现 `unexpected_green`、大批量新建 GdUnit 同时失败，或外层直接超时，不要原命令重跑；先缩小验证范围，再重新生成干净 red 证据。

### 6.5 Green stage

```powershell
py -3 scripts/sc/build.py tdd --task-id <id> --stage green
```

补充口径，只在明确场景下启用：

- `--generate-red-test`：6.4 没有生成可执行红测骨架时再启用
- `--allow-contract-changes`：本任务明确要新建 `Game.Core/Contracts/**` 文件时才启用
- `--no-coverage-gate`：仅用于临时止损定位；恢复后应回到默认覆盖率门

```powershell
py -3 scripts/sc/build.py tdd --task-id <id> --stage green --allow-contract-changes
```

说明：

- green 之前会做 6.4 前置硬门。
- 如果 6.4 没有跑到干净状态，先回去修 6.4，不要继续推进。

### 6.6 Refactor stage

```powershell
py -3 scripts/sc/build.py tdd --task-id <id> --stage refactor
```

说明：

- refactor 之前会检查最近一次同任务 `sc-build-tdd` 的 green summary，要求 `stage = green` 且 `status = ok`。
- 如果 6.5 失败了，先修复 6.5，再进入 refactor。
- `build.py tdd` 已经内置 task preflight、`sc-analyze`、必要的 task-context validation，以及 6.4 -> 6.5 -> 6.6 的顺序硬门。

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

- 默认模板已经是 `scripts/sc/templates/llm_review/bmad-godot-review-template.txt`。
- 除非你明确要覆盖默认映射，否则不要手工传 `--security-profile`。
- 这个 pipeline 会写 sidecars、latest pointers、active-task summaries、repair guidance，以及 technical debt sync outputs。
- review pipeline 启动前还会检查最近一次同任务 `sc-build-tdd` 的 refactor summary，要求 `stage = refactor` 且 `status = ok`；如果 6.6 失败，先修 6.6。
- 如果 6.7 首轮失败，先判断是“仓库级噪音”还是“当前任务问题”。与当前任务无关的 unit 红灯、锁进程、全仓历史失败，不要继续按当前任务的 6.7/6.8 节奏推进。
- 如果上一轮 6.7 已经证明 `sc-test = ok` 且 `sc-acceptance-check = ok`，只有 `sc-llm-review` 超时或失败，而你本轮只改了 review / acceptance / overlay / task 语义文本，不要再手工重付完整 deterministic 成本；优先复用已通过的 deterministic，只重跑 LLM。
- 当最近一轮已经是 `sc-test = ok + sc-acceptance-check = ok + sc-llm-review != clean`，且本轮没有命中 deterministic 相关文件时，默认不要再开一轮完整 6.7；优先进入 6.8 或 `py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id <id> --delivery-profile fast-ship`。只有在你明确需要完整重跑时，才显式传 `--allow-full-rerun`。
- 当最近两轮 6.7 都停在同一类 `sc-test` 失败指纹时，默认先修根因，不要第三次原参数重跑；只有在你明确接受重复 deterministic 成本时，才显式传 `--allow-repeat-deterministic-failures`。
- 重跑前先读最近一轮 `summary.json` 和 `latest.json` 里的 `reason`、`reuse_mode` 与 `diagnostics`；这些字段会明确标出 `rerun_guard`、`reuse_decision`、`acceptance_preflight`、`llm_timeout_memory`。
- 如果同一轮里已经出现“`sc-test` / `sc-acceptance-check` 通过，但 `sc-llm-review` 首次长等待超时”的情况，pipeline 会在当前轮直接止损，不再继续第二次长等待；证据写入 `diagnostics.llm_retry_stop_loss`。
- `active-task` 的 `Chapter6 blocked by` 现在会区分 `rerun_guard`、`llm_retry_stop_loss`、`sc_test_retry_stop_loss`、`waste_signals`：前者表示不要再重复付 deterministic 成本，第二项表示优先走 llm-only follow-up，第三项表示同 run 的 unit 重试已经止损，最后一项表示先停掉无效 engine lane 成本并修 unit/root-cause。
- reviewer 超时扩时现在会继承最近同任务 / 同 profile 的 agent 级超时历史；继续 timeout 时只定向放大该 reviewer，而不是整体抬高全部 reviewer。
- `run_review_pipeline.py` 会按 `DELIVERY_PROFILE` 自动决定第六章的默认强度：
  - `playable-ea`：默认 `max_step_retries = 1`，首轮 review 更轻，适合先验证可玩性。
  - `fast-ship`：默认 `max_step_retries = 1`，首轮 review 聚焦 `code-reviewer + security-auditor + semantic-equivalence-auditor`。
  - `standard`：默认 `max_step_retries = 0`，保留更重的收口姿态，不自动帮你放宽执行节奏。
- 新开 `6.7` 时，默认会继承最近同任务成功解析出来的 `delivery/security profile` 组合；如果你明确要切换 profile，必须显式传 `--reselect-profile`，否则会因 task 级 profile lock 失败。
- 如果上一次同任务 `sc-llm-review` 里只有少数 reviewer 发生 `rc=124` timeout，6.7 会只对这些 reviewer 增加 `--agent-timeouts`，不会把全部 reviewer 一起扩时。
- `--llm-base` 的默认值现在是 `origin/main`；除非你明确需要对比别的基线，否则不要手工改回 `main`。
- 只有当最近两轮 6.7 都出现总超时，或大部分 reviewer 持续 `rc=124`，且定向扩时仍然不够时，才手工加大总超时，例如：`py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship --llm-timeout-sec 900`。
- 不要把大超时当作默认配置；首选仍然是“先按默认预算跑，再对命中过 timeout 的 reviewer 定向补时”。
- 如果首轮 6.7 在 `sc-test` 阶段就出现 `rc=124`，且此前没有稳定的 task-scoped 成功样本，不要连续多次 `--resume` 硬撞；先看 `run-events.jsonl`、`child-artifacts/sc-test/summary.json`、`sc-test.log`，修完根因再继续。
- 如果同一个 run 已经连续两次在 `sc-test` 失败，默认视为“当前 run 无继续价值”；优先修问题后重新开新 run，而不是在同一个 run 上反复 resume。
- 如果当前同一轮 `sc-test` 已经明确是 `unit` 失败，pipeline 现在会直接停掉同 run 的第二次同参重试；这类失败默认视为“已知根因”，先修 unit 再开新 run，不要指望同参数重试自愈。
- 每次决定重跑 6.7 之前，先看最近一轮的：
  - `summary.json`
  - `repair-guide.md`
  - `run-events.jsonl`
  - `child-artifacts/sc-test/summary.json`
  - `child-artifacts/sc-acceptance-check/summary.json`
- 没读工件前，不要直接再开一轮完整 6.7。
- 更进一步的 `sc-test` task-scope 化只在 `playable-ea` / `fast-ship` 自动启用；`standard` 只接受“完全相同 git snapshot”的 `sc-test` 复用。
- 触发这条放宽路径的前提是：最近一次同任务 pipeline 已经有可复用的 `sc-test`，并且本轮相对上轮的变化只落在文档/任务语义层，例如 `docs/**`、`.taskmaster/**`、`examples/taskmaster/**`、`execution-plans/**`、`decision-logs/**`、`AGENTS.md`、`README.md`、`workflow*.md`。
- 一旦变化触及代码、脚本、contracts、测试文件、Godot 运行时资源，6.7 会自动回退到正常 `sc-test`，不会继续走放宽路径；这里至少包括 `Game.Core/**`、`Game.Godot/**`、`Game.Core/Contracts/**`、`Game.Core.Tests/**`、`Tests.Godot/**`、`scripts/sc/**`、`scripts/python/**`、`project.godot`、`*.sln`、`*.csproj`、`*.cs`、`*.gd`、`*.tscn`、`*.tres`。
- 如果变化属于 task semantics，例如 taskmaster / overlay / ADR / PRD 文本，6.7 只复用 `sc-test`；后续 `acceptance_check` 仍会重跑，避免“假绿”。
- 如果你明确要保留旧行为，可以显式传：`py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile <profile> --allow-full-unit-fallback`。
- 这个开关只建议用于定位“task-scoped unit coverage = 0.0%”是否由 filter 过窄引起；默认不要开，否则会把任务级失败放大成全仓 `dotnet test`，拖慢单轮时长。

- 如果你只是想先验证 run wiring、profile 解析、latest pointer 和 planned steps 是否正常，而不想真正执行测试与 acceptance，可先做一轮最便宜的探针：

```powershell
py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship --dry-run --skip-test --skip-acceptance --skip-agent-review
```

- 如果你要给单轮 6.7 明确设置墙钟上限，防止它无限拖长，可显式传：

```powershell
py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship --max-wall-time-sec 7200
```

- 如果上一轮 6.7 只是被外部中断、机器重启或手工停掉，而当前 run 的 sidecars 仍然有效，优先用 `--resume`，不要直接重开一轮：

```powershell
py -3 scripts/sc/run_review_pipeline.py --task-id <id> --resume
```

- `--resume` 默认只用于“外部中断后继续”或“已确认根因已修完的同 run 继续”，不要把它当作 deterministic 失败后的习惯性下一步。

- 如果你想保留旧 run 作为证据，同时从同一基线分叉继续试另一套修复路径，用 `--fork`；默认会 fork 最近一次匹配的 run，必要时再配 `--fork-from-run-id <run_id>`：

```powershell
py -3 scripts/sc/run_review_pipeline.py --task-id <id> --fork
```

- 如果当前 run 已明显失效，不该继续再被恢复，先标记 abort，再按正常模式新开一轮；必要时可配 `--run-id <run_id>` 精确指向旧 run：

```powershell
py -3 scripts/sc/run_review_pipeline.py --task-id <id> --abort
```

- 如果已知 task+run_id 对应的输出目录存在冲突，优先自动生成新 run id，而不是手工删目录：

```powershell
py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship --force-new-run-id
```

- 如果你明确就是要复用同一 run-id 的目录做本地临时重跑，才显式允许覆盖：

```powershell
py -3 scripts/sc/run_review_pipeline.py --task-id <id> --run-id <run_id> --allow-overwrite --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship
```

- 如果这一轮只想做确定性回归，不跑 LLM reviewer，可显式跳过：

```powershell
py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship --skip-llm-review
```

- 长跑或大 diff 任务里，如果你已经确认需要更严的语义门和更稳的单 agent 超时，可再加：

```powershell
py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship --llm-semantic-gate require --llm-agent-timeout-sec 300 --context-refresh-after-failures 2 --context-refresh-after-resumes 2
```

- 当工作区 diff 很大、review 明显被 prompt 体积拖慢时，可先缩小 diff 口径：

```powershell
py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship --llm-diff-mode summary --context-refresh-after-diff-lines 400 --context-refresh-after-diff-categories 4
```

- Before rerunning 6.7, read `run_type` and `artifact_integrity` in addition to `reason`, `reuse_mode`, and `diagnostics`; a `planned-only` / `planned_only_incomplete` / `artifact_integrity` signal means the bundle is not a resumable producer run.
- In that case, use the current bundle only for `summary / repair-guide / run-events` evidence, then fall back to the previous real producer run or start a fresh real 6.7.

### 6.8 清理 Needs Fix

快速可玩验证：

```powershell
py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id <id> --delivery-profile playable-ea
```

日常默认：

```powershell
py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id <id> --delivery-profile fast-ship
```

更重的收敛模式：

```powershell
py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id <id> --delivery-profile standard
```

说明：

- `llm_review_needs_fix_fast.py` 会按 `DELIVERY_PROFILE` 自动落默认值，不建议每轮手工传 reviewer / diff / timeout。
- profile 默认值：
  - `playable-ea`：`agents=code-reviewer,semantic-equivalence-auditor`，`diff_mode=summary`，`max_rounds=1`，`time_budget_min=20`。
  - `fast-ship`：`agents=code-reviewer,security-auditor,semantic-equivalence-auditor`，`diff_mode=summary`，`max_rounds=2`，`time_budget_min=30`。
  - `standard`：`agents=all`，`diff_mode=full`，`max_rounds=2`，`time_budget_min=45`。
- 快速清理脚本会把 `--delivery-profile` 继续透传给内部 `run_review_pipeline.py`，避免第 6.8 里外 profile 漂移。
- 中间回合默认把 6.8 当作 `rerun-failing-only` 快路径：优先只重跑上轮命中的 reviewer，适合“修 Needs Fix、补 wording、补 refs、补局部测试断言”这类收敛回合。
- 只要这一轮没有改实现、测试、contracts 或运行时资源，就不要急着回头重跑完整 6.7；先用 6.8 把命中的问题清干净。
- 只有当本轮改动直接命中了上一轮 reviewer 给出的锚点问题时，才值得立刻再跑 6.8。没有新修复内容时，重复跑 6.8 只是重复支付 LLM 成本。
- 如果上一轮 6.8 的 LLM 回合是超时退出、没有新的可执行 finding、`final_needs_fix_agents` 仍为空，默认先停下来读工件并记录，不要立刻重复同参数再跑一轮。
- 如果上一轮只剩 `Unknown/timeout`，而本轮改动没有命中 reviewer 相关锚点（代码、测试、contracts、tasks/overlays/ADR、review 模板），默认直接止损，不再重复支付 6.8。
- 6.8 的 round 摘要现在会额外记录 `timeout_agents` 与 `failure_kind`；当出现 `timeout-no-summary` 时，优先把它当“观测不足”，而不是把 `status=ok` 误判为 clean。
- 首轮 reviewer 会优先读取上一轮同任务 `agent-review.json` 或 `sc-llm-review summary.json`，自动收缩到真正命中的 reviewer；拿不到稳定信号时才回退到 profile 默认 reviewer 集合。
- deterministic 复用不再只看“当天 latest.json”，会跨日查找最近可复用的同任务 pipeline 产物。
- 如果当前变化只是非任务语义文档，例如 `README.md`、`AGENTS.md`、`docs/agents/**`，`playable-ea` / `fast-ship` 才会直接复用上一轮 deterministic 结果，不再重跑整条链路。
- 如果当前变化只落在 task semantics 文档，例如 `.taskmaster/**`、`examples/taskmaster/**`、`docs/architecture/**`、`docs/adr/**`、`docs/prd/**`、`workflow*.md`、`execution-plans/**`、`decision-logs/**`，不要把它当成真正的 docs-only clean reuse；`playable-ea` / `fast-ship` 默认最多只复用 `sc-test`，仍要重跑 `acceptance_check`，并切到最小 acceptance 子集，只重跑 `adr,links,overlay`，必要时再补 `subtasks`。
- 这条最小子集路径还带 change fingerprint；同一任务、同一 profile、同一变更指纹会优先复用上一次已经成功的最小 acceptance 结果。
- `standard` 不启用上述两条放宽路径；在 `standard` 下，除了完全相同 git snapshot 的复用，其他情况都会回到完整 deterministic 链路。
- 新增预算守门：如果 deterministic 之后剩余预算低于 profile 下限，就直接 fail-fast，不再白白开启一轮新的 LLM 回合。
- `--skip-sc-test` 仍然只建议用于“本轮只修 review / acceptance 文本，没有改实现和测试”的场景；不要把它当作常规默认。
- 如果 deterministic 已经稳定 `ok`，剩余 `Needs Fix` 主要是证据强度、文案粒度、ADR/overlay 回链这类 P2/P3 问题，`fast-ship` 下一般只跑一轮 6.8；第二轮仍然是同主题命中时，默认转为记录和后续跟踪，而不是继续循环。
- 6.8 的 reviewer 默认要按问题类别定向收缩，而不是整套重开：代码实现类优先 `code-reviewer`，语义 / acceptance / task-view / overlay 类优先 `semantic-equivalence-auditor`，安全边界类才补 `security-auditor`。只有无法稳定归类时，才回退到 profile 默认 reviewer 集合。
- 如果连续两轮 6.8 都给出同类 `Needs Fix`，且严重度、命中锚点、建议动作基本不变，默认直接止损并记录，不要再开第三轮同口径 reviewer 重跑。
- 如果剩余问题属于 P1 且会影响任务可交付判断，再决定是否补第二轮 6.8 或升级到 `standard --final-pass`；不要用重复快跑替代问题分级。
- 纯 `.cs` 任务默认保持 unit 路径；只有当 task views 明确声明 `.gd` test refs，或本轮显式走 `verify=all|e2e`，才把它拉入 Godot / GdUnit 重路径。

- 如果这是典型的“中间收敛回合”，而且你只想重跑上一轮真正命中的 reviewer，一般直接把轮数压到 1：

```powershell
py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id <id> --delivery-profile fast-ship --rerun-failing-only --max-rounds 1
```

- 如果你怀疑上一轮 reviewer 收缩过度，想强制回到 profile 默认 reviewer 集合，但仍然只想做一轮快速验证，可改成：

```powershell
py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id <id> --delivery-profile fast-ship --no-rerun-failing-only --max-rounds 1
```

- 如果本轮只改了 review / acceptance 文本，没有动实现与测试，而且你明确知道 `sc-test` 结果仍可复用，才显式传：

```powershell
py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id <id> --delivery-profile fast-ship --skip-sc-test --rerun-failing-only --max-rounds 1
```

- 如果 6.8 反复卡在少数 reviewer timeout，而不是逻辑问题，可只放大单步超时，并给一个更低但明确的预算下限：

```powershell
py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id <id> --delivery-profile fast-ship --rerun-failing-only --step-timeout-sec 900 --min-llm-budget-min 8
```

- 如果这是最后一次收口，直接执行：

```powershell
py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id <id> --delivery-profile standard --final-pass
```

- `--final-pass` 会强制完整 deterministic、完整 reviewer 集合，并关闭 reviewer 自动收缩与最小 acceptance 快捷路径。
- 推荐默认：把 `6.8 --delivery-profile standard --final-pass` 视为“最后一次任务级收口”。它适合已经完成主要实现，只剩最终 Needs Fix 清理的场景。
- 如果最后一轮改动已经超出 Needs Fix 修补范围，例如重新改了实现、测试、contracts、Godot 资源或 review sidecars 已明显过期，就不要只跑 `--final-pass`；应回到完整 `6.7 standard`，必要时再补一轮 6.8。
- 实用顺序：中间回合多用 6.8 快路径，最后收口在“`6.8 --final-pass`”和“完整 `6.7 standard`”之间二选一；然后统一进入 6.9 仓库级硬检查。

- If `resume-task`, `inspect_run`, or `active-task` already shows `run_type = planned-only`, `reason = planned_only_incomplete`, or `Chapter6 blocked by = artifact_integrity`, do not enter 6.8 directly; return to a real deterministic bundle first.

### 6.9 Commit 前的仓库级验证

```powershell
py -3 scripts/python/dev_cli.py run-local-hard-checks --godot-bin "$env:GODOT_BIN"
py -3 scripts/python/inspect_run.py --kind local-hard-checks
```

如果你想在浏览器里持续观察 project-health 页面，可再执行：

```powershell
py -3 scripts/python/dev_cli.py serve-project-health
```

如果一台设备上同时开了多个项目页面，显式指定端口更稳：

```powershell
py -3 scripts/python/dev_cli.py project-health-scan --serve --port 8877
py -3 scripts/python/dev_cli.py serve-project-health --port 8877
```

### 6.10 PR#61 增量快用

- 当本轮改动包含 acceptance wording、`Refs:`、anchors 或相关测试映射时，先跑轻量预检再进入 6.7/6.8：

```powershell
py -3 scripts/python/dev_cli.py run-acceptance-preflight --task-id <id>
```

- 在进入完整 6.9 前，先跑轻量硬门前置（`gate-bundle-hard + run-dotnet`）：

```powershell
py -3 scripts/python/dev_cli.py run-local-hard-checks-preflight --delivery-profile fast-ship
```

- `run_review_pipeline.py` 支持显式 `--llm-agent-timeouts`；会与自动推导超时合并，显式值优先。
- 当最近一轮完整 pipeline 已 clean 且当前仅为 docs-only / non-task-semantic 变更时，6.7 才允许整轮 clean reuse（刷新本轮 sidecars，不重开重步骤）；task semantics 变更不属于这条。
- `llm_review_needs_fix_fast.py` 在 fast-ship 小 diff 中间回合可只对 `code-reviewer` 做定向扩时；如果最近完整 pipeline 已 clean，也允许 clean-skip。
- 如果最近一轮完整 pipeline 不是完全 clean，但 deterministic 已经通过、失败仅剩 `sc-llm-review`，当前脚本也应优先走“复用 deterministic + 只重跑 LLM”的窄路径，而不是重新支付 `sc-test + acceptance_check`。

### 6.11 Fast mode 最省时执行模板

适用前提：

- 日常单任务循环
- 默认 `DELIVERY_PROFILE=fast-ship`
- 不手工覆盖默认 `SECURITY_PROFILE`
- 已正确设置 `$env:GODOT_BIN`

推荐顺序：

1. 恢复上下文：

```powershell
py -3 scripts/python/dev_cli.py resume-task --task-id <id>
```

2. TDD preflight：

```powershell
py -3 scripts/sc/check_tdd_execution_plan.py --task-id <id> --tdd-stage red-first --verify unit --execution-plan-policy draft
```

3. 6.4 red-first：

```powershell
py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id <id> --tdd-stage red-first --verify unit
```

- 只有明确需要 Godot-aware red 证据时，才升级为：

```powershell
py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id <id> --tdd-stage red-first --verify auto --godot-bin "$env:GODOT_BIN"
```

4. 6.5 green：

```powershell
py -3 scripts/sc/build.py tdd --task-id <id> --stage green
```

5. 6.6 refactor：

```powershell
py -3 scripts/sc/build.py tdd --task-id <id> --stage refactor
```

6. 6.7 review pipeline：

```powershell
py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship
```

7. 只有真的出现 `Needs Fix` 再进 6.8：

```powershell
py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id <id> --delivery-profile fast-ship --rerun-failing-only --max-rounds 1
```

8. 6.9 仓库级硬检查：

```powershell
py -3 scripts/python/dev_cli.py run-local-hard-checks --godot-bin "$env:GODOT_BIN"
py -3 scripts/python/inspect_run.py --kind local-hard-checks
```

省时规则：

- `6.4` 首轮默认 `unit`，不要先上 `--verify all`。
- `6.7` 首轮若暴露仓库级噪音、锁进程或 `sc-test rc=124`，先修根因，不要连续 `--resume`。
- 同一个 run 连续两次卡在 `sc-test`，默认放弃该 run；修完后新开 run。
- `6.8` 只在“本轮改动命中上一轮 reviewer 锚点”时才值得重跑。
- 如果 deterministic 已经稳定 `ok`，剩下只是 P2/P3 证据强度问题，默认记录并止损，不再重复支付 LLM 成本。

何时可以 `--resume`：

- 外部中断
- 机器重启
- 已确认根因修完，只想继续同一个 run

何时不要 `--resume`：

- `sc-test` 连续失败
- 首轮就暴露仓库级历史红灯
- 还没先看 `run-events.jsonl`、`sc-test.log`、`child-artifacts/sc-test/summary.json`

中间收敛回合的 6.8 快路径：

```powershell
py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id <id> --delivery-profile fast-ship --rerun-failing-only --max-rounds 1
```

只改了 review / acceptance 文本、没动实现和测试时：

```powershell
py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id <id> --delivery-profile fast-ship --skip-sc-test --rerun-failing-only --max-rounds 1
```

失败后优先看：

- `summary.json`
- `repair-guide.md`
- `run-events.jsonl`
- `sc-test.log`
- `child-artifacts/sc-acceptance-check/summary.json`


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
