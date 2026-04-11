# workflow.example.md

## 适用范围

这是“从模板仓复制出来的新业务仓”的第一周示例工作流。

- 新仓 bootstrap 阶段优先看这份文档
- 进入稳定日常开发后，切换到 `workflow.md`
- 只有当你需要查入口脚本的完整参数、依赖、适用前提，或准备偏离默认流程时，再读 `docs/workflows/script-entrypoints-index.md`。

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
py -3 scripts/python/dev_cli.py inspect-run --kind local-hard-checks
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

- `resume-task` 会直接带出 `Latest reason`、`Latest reuse mode`、`Chapter6 next action`、`Chapter6 can skip 6.7`、`Chapter6 can go to 6.8`、`Chapter6 blocked by`。
- 它现在还会带出 `Approval required action`、`Approval status`、`Approval decision`、`Approval reason`；先看这些字段，再决定是继续修复、进入 `pause`，还是允许 `fork`。
- `resume-task` also surfaces `recommended_action_why`; if it already says `recommended_action = needs-fix-fast`, prefer targeted closure instead of a full rerun.
- 恢复判断先看 `reason / run_type / reuse_mode / artifact_integrity`，不要只按最新 `latest.json` 时间戳决定是否重跑。

如果 recovery summary 仍然不够，再执行二级恢复入口：

```powershell
py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id <id>
```

- approval 路由现在也是确定性的：`pending -> pause`、`approved -> fork`、`denied -> resume`、`invalid/mismatched -> inspect`。
- 如果要确认 producer 真正停在哪个 item，先读 `run-events.jsonl` 的 `turn_id`、`item_kind`、`item_id`、`event_family`，不要只看事件名文本。
- `dev_cli.py inspect-run --kind pipeline` 会输出同一组 `latest_summary_signals` / `chapter6_hints`，适合在真正重跑前确认是继续 `6.7` 还是转 `6.8`。
- 如果这里已经显示 `run_type = planned-only`、`reason = planned_only_incomplete`，或 `Chapter6 blocked by = artifact_integrity`，把该 bundle 只当证据看，不要直接从它 reopen `6.7` / `6.8`。

只有任务很长或跨切面时，才创建 execution plan：

```powershell
py -3 scripts/python/dev_cli.py new-execution-plan --title "<topic>" --task-id <id>
```

当任务过程里出现重要取舍或口径变化时，再补 decision log：

```powershell
py -3 scripts/python/dev_cli.py new-decision-log --title "<topic>" --task-id <id>
```


TDD Sequence:

```powershell
py -3 scripts/sc/check_tdd_execution_plan.py --task-id <id> --tdd-stage red-first --verify unit --execution-plan-policy draft
py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id <id> --tdd-stage red-first --verify unit
py -3 scripts/sc/build.py tdd --task-id <id> --stage green
py -3 scripts/sc/build.py tdd --task-id <id> --stage refactor
```

Ordering Constraints:

- 6.5 green 会强制读取最近一次 `sc-llm-acceptance-tests/summary-<task>.json`。
- 这份 summary 必须来自 `red-first`，且不能存在失败 ref。
- 如果 6.4 创建了新测试文件，还要求 `red_verify.status = ok`，否则 6.5 直接阻断。
- 当你在 6.4 使用 `--verify auto|all` 且带 `--task-id` 时，task-scoped GdUnit 现在必须能从任务视图解析出 `.gd` refs；不再静默回退到 `tests/Scenes` 等全量目录。


如果 `check_tdd_execution_plan.py` 已经明显提示这是复杂任务，不要立刻手工加重所有步骤；先做两件事：

1. 先补一个最小 `execution-plan`
2. 再判断是否真的需要 Serena MCP

只有当复杂度来自“代码语义不清”时，才触发 Serena，例如：

- 不确定现有类 / 接口 / 服务是否已经存在
- 不确定事件契约 / DTO / Contracts 命名是否已有约定
- 需要 rename / refactor，并且担心跨文件引用影响
- 需要快速理解依赖链和模块边界

此时可以让 Codex / Serena 先做一轮最小语义检索：

```text
当前任务先执行 Serena MCP 语义检索，再继续实现。
只保留与当前任务直接相关的 symbols / contracts / references。
如果这些信息会影响实现边界，再写入 taskdoc/<id>.md；否则不要额外产出本地文档。
如果 Serena MCP 不可用，不要阻塞任务，继续 Day 4 流程。
```

如果复杂度只是“测试文件多、`.cs` + `.gd` 混合、verify 更重”，通常不需要 Serena，直接继续 TDD 即可。
统一 review pipeline：

```powershell
py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship
```

如果出现可执行的 `Needs Fix`：

```powershell
py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id <id> --delivery-profile fast-ship
```

说明：

- 6.7 会按 profile 自动选择默认 reviewer 集合；如果上一轮只有个别 reviewer timeout，当前轮只会定向放大这些 reviewer 的超时预算。
- 如果同一轮已经证明 deterministic 绿色，而 `sc-llm-review` 首次长等待就超时，pipeline 会直接止损，不再在同一轮继续第二次长等待。
- 新开 6.7 默认继承最近同任务的 `delivery/security profile`；只有你明确要换 profile 时，才加 `--reselect-profile`。
- `--llm-base` 默认是 `origin/main`；除非你明确要看别的比较基线，不要手工改回 `main`。
- 只有在最近两轮 6.7 都持续超时、而且定向扩时仍不够时，才手工提高总超时；不要一开始就把 `--llm-timeout-sec` 拉很大。
- 在决定重跑 6.7 前，先读 `run_type` 与 `artifact_integrity`；如果恢复链已经给出 `planned-only` / `planned_only_incomplete` / `artifact_integrity`，这一轮不是可恢复的 producer run。
- 6.7 的进一步 `sc-test` 复用只在 `playable-ea` / `fast-ship` 自动启用，而且只接受“文档/任务语义层”变更；只要触及代码、脚本、contracts、测试文件或运行时资源，就会回退到正常 `sc-test`。
- 如果 task-scoped `dotnet test --filter ...` 因 coverage 0.0% 失败，默认直接失败，不再自动回退到全量 `dotnet test`。
- 只有在你明确想验证“是否只是 filter 过窄”时，才额外执行：`py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship --allow-full-unit-fallback`。
- 如果最近一次完整 6.7 已经 clean，而当前只改了 `decision-logs/**`、`execution-plans/**`、`README.md`、`AGENTS.md`、`docs/agents/**` 这类非任务语义文档，6.7 会直接 clean skip。
- 如果这一轮动了 acceptance wording / `Refs:` / anchors，先跑：`py -3 scripts/python/dev_cli.py run-acceptance-preflight --task-id <id>`，再进 6.7。
- 默认阶段是 `refactor`；如果你想查 red/green 文案，可改成 `--stage red` 或 `--stage green`。要把日志落到别处时，加 `--out-dir <dir>`。

- 如果你只想先验证 wiring、latest pointer 和 planned steps 是否正常，可先做：`py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship --dry-run --skip-test --skip-acceptance --skip-agent-review`
- 单轮 6.7 明显可能拖太久时，可加 `--max-wall-time-sec 7200` 做墙钟止损
- 外部中断后优先 `--resume`；要保留旧 run 再分叉试另一套修法时用 `--fork`；确认旧 run 不该再继续时用 `--abort`
- 6.8 首轮会优先读取上一轮 `agent-review.json` / `sc-llm-review summary.json`，自动收缩 reviewer；如果没有稳定历史信号，再回退到 profile 默认集合。
- 中间回合把 6.8 当作 failing-only 快路径即可：优先修命中的 reviewer，不要反复重跑完整 6.7。
- 6.8 对 task semantics 文本改动会切到最小 acceptance 子集；如果 change fingerprint 没变，会优先复用上一次已经成功的最小 acceptance 结果。
- 6.8 的 round 摘要现在会写 `timeout_agents` / `failure_kind`；如果看到 `timeout-no-summary`，先看工件完整性，不要直接当 clean。
- 如果恢复链已经显示 `run_type = planned-only`、`reason = planned_only_incomplete`，或 `Chapter6 blocked by = artifact_integrity`，不要直接进 6.8；先回到真实 deterministic bundle 再决定是否收敛 Needs Fix。
- `standard` 不启用上面两条放宽路径；它只接受完全相同 snapshot 的复用，否则回到完整 deterministic 链路。
- 中间回合一般直接用 `--rerun-failing-only --max-rounds 1`；如果怀疑 reviewer 收缩过度，再改成 `--no-rerun-failing-only --max-rounds 1`
- 本轮只改 review / acceptance 文本时，才考虑 `--skip-sc-test`
- 如果本轮动了 acceptance wording / `Refs:` / anchors，先跑：`py -3 scripts/python/dev_cli.py run-acceptance-preflight --task-id <id>`，再进 6.8。
- 这里通常保持默认 `refactor` 即可；只有你明确在 red/green 阶段单独查 wording 时，才改 `--stage`。
- 如果最近一次完整 6.7 已经 clean，且本轮只改了非任务语义文档，6.8 会直接 no-op 退出。
- `fast-ship` 小 diff 中间回合默认已会只给 `code-reviewer` 做定向补时；只有它仍然 timeout 时，再试 `--step-timeout-sec 900 --min-llm-budget-min 8`
- 最后一轮正式收口时，直接用 `--final-pass` 强制完整 deterministic 和完整 reviewer 集合。
- 如果最后一轮已经重新改了实现、测试、contracts 或运行时资源，就不要只跑 `--final-pass`；回到完整 `6.7 standard` 更稳。

如果只是快速验证可玩性：

```powershell
py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile playable-ea
```

如果准备做更重的收口：

```powershell
py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id <id> --delivery-profile standard --final-pass
```

在 commit 或 PR 前：

```powershell
py -3 scripts/python/dev_cli.py run-local-hard-checks-preflight --delivery-profile fast-ship
py -3 scripts/python/dev_cli.py run-local-hard-checks --godot-bin "$env:GODOT_BIN"
py -3 scripts/python/dev_cli.py inspect-run --kind local-hard-checks
```

- `run-local-hard-checks-preflight` 先挡 `gate-bundle-hard` / `run-dotnet` 的快失败；通过后再跑完整 6.9。
- 如果改了 `.taskmaster/tasks/*.json`、`overlay_refs` 或 overlay `_index.md`，先跑：`py -3 scripts/python/remind_overlay_task_drift.py --overlay-index docs/architecture/overlays/<PRD-ID>/08/_index.md --write`；单 overlay 仓可只用 `--write`。

2. 长区间、多任务：

```powershell
py -3 scripts/python/run_single_task_light_lane_batch.py --task-id-start 101 --task-id-end 180 --batch-preset stable-batch --delivery-profile fast-ship --max-tasks-per-shard 12
```

默认理解：

- `preflight_acceptance_extract_guard` 会先跑一次确定性 acceptance 预检查，提前拦截明显缺少 Refs 或硬门语义的任务
- preflight 通过后，`extract`、`align`、`coverage`、`semantic_gate` 仍然照常执行；它不是质量替代品，只是节省时间的前置守卫
- `extract` 仍然是第一判断点
- 如果 `extract` 已失败，脚本会自动做后续降载
- 遇到 `timeout` 或 `SC_LLM_OBLIGATIONS status=fail` 这类 family，会更早短路
- 只有在长批次明显不稳定时，才去调 `rolling-*`、`fill-refs-mode`、`no-align-apply`
- 如果一整轮日志里基本都是 `first_failed_step = extract`，不要继续往 5.1 里堆 stop-loss，优先修 obligations、task context、extract prompt、timeout、shard size
- 如果你要切换任务区间、profile，或者只是想开一轮完全隔离的重跑，显式换 `--out-dir` 并加 `--no-resume`，避免旧批次状态污染新结果
- 如果这一轮只是为了尽快定位第一个硬失败点，可加 `--stop-on-step-failure`，不要把后续低价值步骤也跑完

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
- 不要把 `run-events.jsonl` 当自由文本日志；恢复自动化应按 `turn_id` / `item_kind` / `item_id` / `event_family` 消费。
- 当 approval sidecar 已显示 `pending`、`invalid` 或 `mismatched` 时，不要硬开 `--resume` / `--fork`。
- 在真实 triplet 存在前，不要开始 overlays
- 默认不要运行重型 obligations freeze tooling
- 在读取 sidecars 前，不要从聊天记录恢复状态
- 除非你明确要覆盖，否则不要在 `standard` 上强制传 `host-safe`
- 不要为 `llm_fill_acceptance_refs.py` 虚构 `--dry-run` 参数；不带 `--write` 就是 dry-run
- 不要因为 Serena 暂时不可用就阻塞整项工作
- 当 `run_review_pipeline.py` 已存在时，不要手工串 test + acceptance + llm review
- 新仓不要等到第一笔业务提交前，才第一次跑 `run-local-hard-checks`
