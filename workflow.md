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

å unit ç red-firstï¼

```powershell
py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id <id> --tdd-stage red-first --verify unit
```

æ··å `.cs` + `.gd` æéè¦ Godot-aware verificationï¼

```powershell
py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id <id> --tdd-stage red-first --verify auto --godot-bin "$env:GODOT_BIN"
```

è¯´æï¼

- 6.5 green ä¼å¼ºå¶è¯»åæè¿ä¸æ¬¡ `sc-llm-acceptance-tests/summary-<task>.json`ã
- è¿ä»½ summary å¿
é¡»æ¥èª `red-first`ï¼ä¸ä¸è½å­å¨å¤±è´¥ refã
- å¦æ 6.4 åå»ºäºæ°æµè¯æä»¶ï¼è¿è¦æ± `red_verify.status = ok`ï¼å¦å 6.5 ç´æ¥é»æ­ã
- å½ä½ å¨ 6.4 ä½¿ç¨ `--verify auto|all` ä¸å¸¦ `--task-id` æ¶ï¼task-scoped GdUnit ç°å¨å¿
é¡»è½ä»ä»»å¡è§å¾è§£æåº `.gd` refsï¼ä¸ä¼åéé»åéå° `tests/Scenes` ç­å
¨éç®å½ã

### 6.5 Green stage

```powershell
py -3 scripts/sc/build.py tdd --task-id <id> --stage green
```

è¯´æï¼

- green ä¹åä¼å 6.4 åç½®ç¡¬é¨ã
- å¦æ 6.4 æ²¡æè·å°å¹²åç¶æï¼å
åå»ä¿® 6.4ï¼ä¸è¦ç»§ç»­æ¨è¿ã

### 6.6 Refactor stage

```powershell
py -3 scripts/sc/build.py tdd --task-id <id> --stage refactor
```

è¯´æï¼

- refactor ä¹åä¼æ£æ¥æè¿ä¸æ¬¡åä»»å¡ `sc-build-tdd` ç green summaryï¼è¦æ± `stage = green` ä¸ `status = ok`ã
- å¦æ 6.5 å¤±è´¥äºï¼å¿
é¡»å
ä¿®å¤ 6.5ï¼åè¿å
¥ refactorã

`build.py tdd` å·²ç»å
ç½® task preflightã`sc-analyze`ãå¿
éç task-context validationï¼ä»¥å 6.4 -> 6.5 -> 6.6 çé¡ºåºç¡¬é¨ã

### 6.7 ç»ä¸ä»»å¡çº§ review pipeline

æ¥å¸¸é»è®¤ï¼

```powershell
py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship
```

æ´éçæ¶ææ¨¡å¼ï¼

```powershell
py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile standard
```

å¿«éå¯ç©éªè¯ï¼

```powershell
py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile playable-ea
```

è¯´æï¼

- é»è®¤æ¨¡æ¿å·²ç»æ¯ `scripts/sc/templates/llm_review/bmad-godot-review-template.txt`
- é¤éä½ æç¡®è¦è¦çé»è®¤æ å°ï¼å¦åä¸è¦æå·¥ä¼  `--security-profile`
- è¿ä¸ª pipeline ä¼å sidecarsãlatest pointersãactive-task summariesãrepair guidanceï¼ä»¥å technical debt sync outputs
- review pipeline å¯å¨åè¿ä¼æ£æ¥æè¿ä¸æ¬¡åä»»å¡ `sc-build-tdd` ç refactor summaryï¼è¦æ± `stage = refactor` ä¸ `status = ok`ï¼å¦æ 6.6 å¤±è´¥ï¼å
ä¿® 6.6ã
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
