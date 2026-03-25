# workflow.example.md

## 适用范围

这个文件是“从模板复制出来的新业务仓”的初始化示例工作流。

- 新仓创建后的第一周优先参考本文件
- 当仓库已经完成 bootstrap 后，切换到 `workflow.md` 作为稳定日常工作流

## Day 1：改名并让仓库可运行

1. 在以下位置统一修改项目身份和路径残留：
   - `README.md`
   - `AGENTS.md`
   - `docs/**`
   - `.github/**`
   - `project.godot`
2. 修复失效链接和旧仓库名
3. 在本地设置 `GODOT_BIN`
4. 立即运行仓库级硬检查：

```powershell
py -3 scripts/python/dev_cli.py run-local-hard-checks --godot-bin "$env:GODOT_BIN"
py -3 scripts/python/inspect_run.py --kind local-hard-checks
```

可选：启动本地 project-health 页面服务，固定浏览器访问地址：

```powershell
py -3 scripts/python/dev_cli.py serve-project-health
```

目标：

- 新仓已经完成正确改名
- 核心入口文档可用
- 模板复制带来的早期 CI-hard 问题已基本清掉
- 可以在浏览器里稳定查看 repo health 页面

## Day 2：建立真实 task triplet

在 `.taskmaster/tasks/` 下创建或导入真实 triplet：

- `tasks.json`
- `tasks_back.json`
- `tasks_gameplay.json`

如果 view files 已存在，而 `tasks.json` 需要重建：

```powershell
py -3 scripts/python/build_taskmaster_tasks.py
```

校验 triplet：

```powershell
py -3 scripts/python/task_links_validate.py
py -3 scripts/python/check_tasks_all_refs.py
py -3 scripts/python/validate_task_master_triplet.py
```

提前标准化 semantic review tier：

```powershell
py -3 scripts/python/backfill_semantic_review_tier.py --mode conservative --write
py -3 scripts/python/validate_semantic_review_tier.py --mode conservative
```

到这一步时，建议再跑一次：

```powershell
py -3 scripts/python/dev_cli.py project-health-scan --serve
```

目标：

- `triplet-missing` warning 消失
- project-health 页面开始反映真实业务仓状态，而不是模板 fallback 状态

## Day 3：生成 overlays 并建立 contract baseline

先 dry-run overlays：

```powershell
py -3 scripts/sc/llm_generate_overlays_batch.py --prd <prd-main.md> --prd-id <PRD-ID> --prd-docs <prd-extra-a.md>,<prd-extra-b.md> --page-family core --page-mode scaffold --timeout-sec 1200 --dry-run --batch-suffix first-core-dryrun
```

然后 simulate：

```powershell
py -3 scripts/sc/llm_generate_overlays_batch.py --prd <prd-main.md> --prd-id <PRD-ID> --prd-docs <prd-extra-a.md>,<prd-extra-b.md> --page-family core --page-mode scaffold --timeout-sec 1200 --batch-suffix first-core-sim
```

只修 outlier pages：

```powershell
py -3 scripts/sc/llm_generate_overlays_from_prd.py --prd <prd-main.md> --prd-id <PRD-ID> --prd-docs <prd-extra-a.md>,<prd-extra-b.md> --page-filter <overlay-file.md> --page-mode scaffold --timeout-sec 1200 --run-suffix fix-page-1
```

只 apply 你确认可信的页面：

```powershell
py -3 scripts/sc/llm_generate_overlays_batch.py --prd <prd-main.md> --prd-id <PRD-ID> --prd-docs <prd-extra-a.md>,<prd-extra-b.md> --pages _index.md,ACCEPTANCE_CHECKLIST.md,08-rules-freeze-and-assertion-routing.md --page-mode scaffold --timeout-sec 1200 --apply --batch-suffix apply-core
```

冻结 overlay refs：

```powershell
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

默认日常模式：`fast-ship`

继续任务时：

```powershell
py -3 scripts/python/dev_cli.py resume-task --task-id <id>
```

只有当任务很长或跨切面时，才创建 execution plan：

```powershell
py -3 scripts/python/dev_cli.py new-execution-plan --title "<topic>" --task-id <id>
```

TDD preflight：

```powershell
py -3 scripts/sc/check_tdd_execution_plan.py --task-id <id> --tdd-stage red-first --verify unit --execution-plan-policy draft
```

生成红灯测试：

```powershell
py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id <id> --tdd-stage red-first --verify unit
```

Green：

```powershell
py -3 scripts/sc/build.py tdd --task-id <id> --stage green
```

Refactor：

```powershell
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

如果你希望一直保留本地健康页地址：

```powershell
py -3 scripts/python/dev_cli.py serve-project-health
```

## 什么时候进入更重的 lanes

只有当以下情况出现时，才使用 semantics stabilization lane：

- acceptance 较弱或正在漂移
- refs 仍然是 placeholder
- subtasks 覆盖不清晰
- 重复的 `Needs Fix` 明显指向 task semantics，而不是代码实现

只有当以下情况出现时，才使用 `standard` profile：

- 任务本身高风险或跨切面
- contracts 或 architecture boundaries 已发生变化
- 你正在做 PR 前或 milestone freeze 前的收敛

## 止损规则（Stop-Loss）

- 不要把 `examples/taskmaster/**` 当成业务仓 SSoT
- 在真实 triplet 存在前，不要开始 overlays
- 默认不要运行重型 obligations freeze tooling
- 在读取 sidecars 前，不要从聊天记录恢复
- 除非你明确要覆盖，否则不要在 `standard` 上强制传 `host-safe`
- 当 `run_review_pipeline.py` 已存在时，不要手工串 test + acceptance + llm review
- 新仓不要等到第一笔业务提交前，才第一次跑 `run-local-hard-checks`
