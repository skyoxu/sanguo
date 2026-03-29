# workflow.example.md

## 适用范围

这是“从模板仓复制出来的新业务仓”的第一周示例工作流。

- 新仓 bootstrap 阶段优先看这份文档
- 进入稳定日常开发后，切换到 `workflow.md`

## Day 1：改名并让仓库可运行

1. 统一修改项目名、路径、旧仓痕迹：
   - `README.md`
   - `AGENTS.md`
   - `docs/**`
   - `.github/**`
   - `project.godot`
2. 设置 `GODOT_BIN`
3. 立即跑一次仓库级硬检查：

```powershell
py -3 scripts/python/dev_cli.py run-local-hard-checks --godot-bin "$env:GODOT_BIN"
py -3 scripts/python/inspect_run.py --kind local-hard-checks
```

可选：启动本地 project-health 页面：

```powershell
py -3 scripts/python/dev_cli.py serve-project-health
```

目标：

- 仓库名称、索引、路径已改干净
- 入口文档可用
- 本地硬门禁能跑通

## Day 2：建立真实 task triplet

在 `.taskmaster/tasks/` 下建立或导入真实 triplet：

- `tasks.json`
- `tasks_back.json`
- `tasks_gameplay.json`

如果需要重建 `tasks.json`：

```powershell
py -3 scripts/python/build_taskmaster_tasks.py
```

校验 triplet：

```powershell
py -3 scripts/python/task_links_validate.py
py -3 scripts/python/check_tasks_all_refs.py
py -3 scripts/python/validate_task_master_triplet.py
```

提前固化 semantic review tier：

```powershell
py -3 scripts/python/backfill_semantic_review_tier.py --mode conservative --write
py -3 scripts/python/validate_semantic_review_tier.py --mode conservative
```

然后再跑一次 repo health：

```powershell
py -3 scripts/python/dev_cli.py project-health-scan --serve
```

目标：

- `triplet-missing` warning 消失
- project-health 开始反映真实业务仓状态

## Day 3：生成 overlays 并建立 contract baseline

先做 dry-run / simulate / 小范围 apply，然后冻结 overlay refs：

```powershell
py -3 scripts/sc/llm_generate_overlays_batch.py --prd <prd-main.md> --prd-id <PRD-ID> --prd-docs <prd-extra-a.md>,<prd-extra-b.md> --page-family core --page-mode scaffold --timeout-sec 1200 --dry-run --batch-suffix first-core-dryrun
py -3 scripts/sc/llm_generate_overlays_batch.py --prd <prd-main.md> --prd-id <PRD-ID> --prd-docs <prd-extra-a.md>,<prd-extra-b.md> --page-family core --page-mode scaffold --timeout-sec 1200 --batch-suffix first-core-sim
py -3 scripts/sc/llm_generate_overlays_from_prd.py --prd <prd-main.md> --prd-id <PRD-ID> --prd-docs <prd-extra-a.md>,<prd-extra-b.md> --page-filter <overlay-file.md> --page-mode scaffold --timeout-sec 1200 --run-suffix fix-page-1
py -3 scripts/sc/llm_generate_overlays_batch.py --prd <prd-main.md> --prd-id <PRD-ID> --prd-docs <prd-extra-a.md>,<prd-extra-b.md> --pages _index.md,ACCEPTANCE_CHECKLIST.md,08-rules-freeze-and-assertion-routing.md --page-mode scaffold --timeout-sec 1200 --apply --batch-suffix apply-core
py -3 scripts/python/sync_task_overlay_refs.py --prd-id <PRD-ID> --write
py -3 scripts/python/validate_overlay_execution.py --prd-id <PRD-ID>
```

建立 contract baseline：

```powershell
py -3 scripts/python/validate_contracts.py
py -3 scripts/python/check_domain_contracts.py
dotnet test Game.Core.Tests/Game.Core.Tests.csproj
```

## Day 4 及之后：开始真实任务执行

默认日常 profile：`fast-ship`

继续任务时：

```powershell
py -3 scripts/python/dev_cli.py resume-task --task-id <id>
```

如果 recovery summary 仍然不够，再执行二级恢复入口：

```powershell
py -3 scripts/python/inspect_run.py --kind pipeline --task-id <id>
```

只有任务很长或跨切面时，才创建 execution plan：

```powershell
py -3 scripts/python/dev_cli.py new-execution-plan --title "<topic>" --task-id <id>
```

当任务过程里出现重要取舍或口径变化时，再补 decision log：

```powershell
py -3 scripts/python/dev_cli.py new-decision-log --title "<topic>" --task-id <id>
```

TDD 建议顺序：

```powershell
py -3 scripts/sc/check_tdd_execution_plan.py --task-id <id> --tdd-stage red-first --verify unit --execution-plan-policy draft
py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id <id> --tdd-stage red-first --verify unit
py -3 scripts/sc/build.py tdd --task-id <id> --stage green
py -3 scripts/sc/build.py tdd --task-id <id> --stage refactor
```

统一 review pipeline：

```powershell
py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship
```

如果出现可执行的 `Needs Fix`：

```powershell
py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id <id> --max-rounds 1 --rerun-failing-only --time-budget-min 20 --agents code-reviewer,test-automator,semantic-equivalence-auditor
```

在 commit 或 PR 前：

```powershell
py -3 scripts/python/dev_cli.py run-local-hard-checks --godot-bin "$env:GODOT_BIN"
py -3 scripts/python/inspect_run.py --kind local-hard-checks
```

### Day 4 补充：轻量 lane 的默认口径

默认只记住两种入口：

1. 单任务或很小的临时批次：

```powershell
py -3 scripts/python/run_single_task_light_lane.py --task-ids <id> --delivery-profile fast-ship
```

2. 长区间、多任务：

```powershell
py -3 scripts/python/run_single_task_light_lane_batch.py --task-id-start 101 --task-id-end 180 --batch-preset stable-batch --delivery-profile fast-ship --max-tasks-per-shard 12
```

默认理解：

- `extract` 是第一判断点
- 如果 `extract` 已失败，脚本会自动做后续降载
- 遇到 `timeout` 或 `SC_LLM_OBLIGATIONS status=fail` 这类 family，会更早短路
- 只有在长批次明显不稳定时，才去调 `rolling-*`、`fill-refs-mode`、`no-align-apply`
- 如果一整轮日志里基本都是 `first_failed_step = extract`，不要继续往 5.1 里堆 stop-loss，优先修 obligations、task context、extract prompt、timeout、shard size

## 什么时候进入更重的 lanes

只有当以下情况出现时，才使用 semantics stabilization lane：

- acceptance 较弱或正在漂移
- refs 仍然是 placeholder
- subtasks 覆盖不清晰
- 重复的 `Needs Fix` 明显指向 task semantics，而不是代码实现

只有当以下情况出现时，才切到 `standard` profile：

- 任务本身高风险或跨切面
- contracts 或 architecture boundaries 已发生变化
- 你正在做 PR 前或 milestone freeze 前的收敛

## 止损规则（Stop-Loss）

- 不要把 `examples/taskmaster/**` 当成业务仓 SSoT
- 在真实 triplet 存在前，不要开始 overlays
- 默认不要运行重型 obligations freeze tooling
- 在读取 sidecars 前，不要从聊天记录恢复状态
- 除非你明确要覆盖，否则不要在 `standard` 上强制传 `host-safe`
- 不要为 `llm_fill_acceptance_refs.py` 虚构 `--dry-run` 参数；不带 `--write` 就是 dry-run
- 不要因为 Serena 暂时不可用就阻塞整项工作
- 当 `run_review_pipeline.py` 已存在时，不要手工串 test + acceptance + llm review
- 新仓不要等到第一笔业务提交前，才第一次跑 `run-local-hard-checks`
