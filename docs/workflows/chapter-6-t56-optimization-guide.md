# Workflow 第六章 T56 优化与升级指南

本文件记录 `workflow.md` 第六章在 `T56` 实战日志驱动下完成的优化、问题闭环、流程变化，以及其他项目如何对齐到本仓当前的完整能力。

适用范围：

- 当前仓库 `godotgame`
- 本机其他仍处于旧版 Chapter 6 口径的业务仓
- 需要读取第六章后直接执行任务循环的 AI 代码助手

## 1. 为什么要写这份文档

`workflow.md` 第六章已经定义了单任务日常循环，但在 `T56` 的真实运行中，暴露出了“文档可执行”与“流水线实际效率/稳定性”之间的几个差距：

1. 同一任务反复重跑时，`sc-test` 没有复用，浪费 10 到 20 分钟。
2. 某些 CLI 参数不兼容或 summary schema 漂移，可能在重步骤跑完后才暴露，属于晚失败。
3. `llm_review` 默认上下文过大，容易截断，且 `fast-ship` 默认审查面过重。
4. `acceptance_check` 的 `perf-budget` 误拿“最新但无 `[PERF]` 的 smoke 日志”，导致假失败。
5. 旧项目如果只抄 `workflow.md`，不一起升级脚本、配置、schema、测试和索引，会得到“文档看起来一致，行为实际不一致”的伪对齐状态。

这份文档的目标不是替代 `workflow.md`，而是解释第六章现在为什么这样设计，以及旧项目应如何完整升级。

## 2. T56 真实日志给出的关键信号

以下结论来自 `2026-03-31` 的真实运行：

### 2.1 第一轮真实 `6.7`

- 命令：
  - `py -3 scripts/sc/run_review_pipeline.py --task-id 56 --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship`
- run id：
  - `4f49ce0fe9634fa7b788278bfc9a45a9`
- 结果：
  - `SC_REVIEW_PIPELINE status=fail`
- 总耗时：
  - `986s`

关键观察：

- `acceptance_preflight_completed` 在启动后约 `13s` 就完成，说明 CLI/self-check 类错误没有晚爆。
- 真正失败点是 `sc-acceptance-check`，不是 `sc-test`，也不是 `llm_review`。
- 失败根因最终定位为 `perf-budget` 选错了 `headless.log`。

### 2.2 第二轮同快照重跑

- run id：
  - `8bfde169a6214532b1401b3006046c46`
- 结果：
  - `SC_REVIEW_PIPELINE status=fail`
- 总耗时：
  - `35s`

关键观察：

- `sc-test` 明确命中复用。
- `sc-test.log` 中存在：
  - `reused sc-test from matching git snapshot`
- 同一 git 快照下，从约 `986s` 降到 `35s`，节省约 `951s`，即 `15.9` 分钟。

### 2.3 perf gate 根因

当时最新 `headless.log` 是：

- `logs/ci/2026-03-31/smoke/20260331-134012/headless.log`

内容只有：

- `[TEMPLATE_SMOKE_READY]`

它没有 `[PERF]` 行，因此旧逻辑把它当作 perf 输入时会产生假失败。

而同一天更早的日志：

- `logs/ci/2026-03-31/smoke/20260331-015310/headless.log`

包含可用 perf 指标：

- `[PERF] frames=300 ... p95_ms=6.91 ...`

这说明问题不是“没有 perf 证据”，而是“选错了日志”。

### 2.4 修复后的真实验证

- 真实 acceptance 证据（通过统一入口触发）：
  - 入口：`py -3 scripts/sc/run_review_pipeline.py --task-id 56 --godot-bin "$env:GODOT_BIN"`
  - 关键 acceptance 参数：`run-id=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`、`delivery-profile=fast-ship`、`security-profile=host-safe`、`require-task-test-refs=true`、`subtasks-coverage=warn`、`perf-p95-ms=33`
  - 结果：`SC_ACCEPTANCE status=ok`
  - 耗时：`38s`
  - perf 证据：`p95_ms=6.91 <= 33`

- 真实 `6.7` 成功轮：
  - run id：`31da74a983994809bd5e71f39d311f24`
  - 结果：`SC_REVIEW_PIPELINE status=ok`
  - 总耗时：`1351s`

## 3. 这次第六章优化了哪些工具和脚本

下表只列与 Chapter 6 直接相关、并在 T56 周期中产生实效的项。

| 类别 | 文件 | 优化内容 | 解决的问题 |
|---|---|---|---|
| 统一任务流水线 | `scripts/sc/run_review_pipeline.py` | 增加 `sc-test` 同快照复用；在执行前统一跑 downstream `--self-check`；按 delivery profile 控制默认 agents / diff mode；保留 child-artifacts 快照 | 重跑太慢；CLI/参数/summary 漂移晚失败；`fast-ship` 审查过重 |
| 测试入口 | `scripts/sc/test.py` | 增加 `--self-check`；执行前先做 planned summary schema 校验 | `sc-test` 跑完才发现 schema/CLI 配置不合法 |
| task-scoped unit fallback | `scripts/sc/_sc_test_steps.py` | 当 task-scoped coverage 为 `0.0%` 且属于 filter 假阴性时，自动退回无 filter 的 unit 重试 | 某些任务因为 scoped filter 把 coverage 打成 0，造成无意义失败 |
| acceptance 与测试复用 | `scripts/sc/_acceptance_steps.py` | `acceptance_check` 的 `tests-all` 可复用当前 pipeline 的 `sc-test` 结果 | 同一轮里重复做 unit 取证 |
| acceptance CLI 兼容 | `scripts/sc/_acceptance_runtime.py` | 接受 `--delivery-profile` 作为 pipeline 兼容参数 | `run_review_pipeline` 给 `acceptance_check` 传 profile 时出现不兼容风险 |
| acceptance perf gate | `scripts/sc/_acceptance_steps_quality.py` | `perf-budget` 优先选择“最近且含 `[PERF]` 的 `headless.log`” | 模板 smoke 日志被误判为 perf 日志，造成假失败 |
| overlay 校验范围 | `scripts/python/validate_task_overlays.py` | 支持 `--task-id` 精确校验单任务 | `acceptance_check` 为单任务跑 overlay 校验时仍全量扫描，效率低且噪音大 |
| review profile 选择 | `scripts/sc/_llm_review_tier.py` | tier 配置遵循 delivery profile 默认 agents，而不是硬编码 `all` | `fast-ship` 路径审查过重、耗时偏长 |
| review prompt 体积 | `scripts/sc/_llm_review_prompting.py` | 引入 compact/semantic task context | 大 diff、大 task context 容易截断 |
| review acceptance 摘要 | `scripts/sc/_llm_review_acceptance.py` | acceptance 语义改为压缩摘要而非全文堆叠 | prompt 冗长，低价值 token 过多 |
| review engine | `scripts/sc/_llm_review_engine.py` | 支持 diff mode 自适应，优先 `summary`，必要时再退化 | 截断率高，首轮审查耗时偏长 |
| delivery profile 配置 | `scripts/sc/config/delivery_profiles.json` | 为不同交付姿态定义默认 `llm_review.agents`、`diff_mode` 等 | profile 只是名字，实际行为未真正区分 |
| needs-fix 快速闭环 | `scripts/sc/llm_review_needs_fix_fast.py` | 优先复用上一轮成功 deterministic pipeline，再进入 needs-fix 清理 | 清理 Needs Fix 前还要手工重跑一整套确定性链路 |

## 4. 第六章流程发生了什么变化

### 4.1 `6.1` 和 `6.3` 从“建议”变成“重步骤前的前置条件”

当前推荐顺序仍是：

1. `resume-task` (when you only need the next recovery suggestion, use `resume-task --recommendation-only`; it skips extra summary outputs by default)
2. `check_tdd_execution_plan.py`
3. red
4. green
5. refactor
6. `run_review_pipeline.py`
7. 只有需要时再 `llm_review_needs_fix_fast.py`

变化点不是命令变了，而是执行语义更硬了：

- `6.1` 不再只是“找资料”，而是恢复 active-task sidecar、latest pointers、repair guide 的正式入口。
- `6.3` 不再只是一个提醒器，而是决定是否需要 execution-plan、Serena MCP、taskdoc 的轻量分流器。

- `6.1` 恢复时要按 `reason -> run_type -> reuse_mode -> artifact_integrity -> chapter6_hints` 顺序读取信号；不能只看 `status=ok` 或最新 `latest.json` 时间戳。
- `active-task` 不只是展示页，也是 stop-loss 判读面；会提前显示 `Latest run type`、`Latest artifact integrity` 和 `Diagnostics artifact_integrity`。

### 4.2 `6.7` 现在是唯一推荐的任务级统一评审入口

不要再手工串：

- `scripts/sc/test.py`
- `scripts/sc/acceptance_check.py`
- `scripts/sc/llm_review.py`

第六章当前口径是：

- 日常默认：`run_review_pipeline.py --delivery-profile fast-ship`
- 收敛模式：`--delivery-profile standard`
- 快速可玩：`--delivery-profile playable-ea`

理由：

- profile 会决定默认的 `security_profile` 映射、`llm_review` agents、`diff_mode`、超时时间和 soft gate 行为。
- sidecars、latest pointers、technical debt 同步、repair guide 都依赖统一入口，不依赖手工三连。

### 4.3 `6.7` 内部新增了“先失败、再重步骤”的结构

当前 `run_review_pipeline.py` 在真正执行重步骤前，会做：

1. `acceptance_check.py --self-check`
2. `test.py --self-check`
3. `llm_review.py --self-check`

意义：

- 不再出现“跑了十几分钟后才发现下游不接受某个参数”的浪费。
- 不再把 summary schema 错误拖到收尾阶段才报。

### 4.4 `fast-ship` 的默认 `llm_review` 变轻了，但不是降质量

当前 `fast-ship` 默认只跑：

- `code-reviewer`
- `security-auditor`

但这里要分两层理解：

- `run_review_pipeline.py` 在低风险 `minimal / targeted` tier 下，默认先收窄到 `code-reviewer + security-auditor`
- `semantic-equivalence-auditor` 会在高风险任务、`contractRefs` 命中、P0/P1 升级、或 tier 升到 `full` 时自动补回
- `llm_review_needs_fix_fast.py` remains the targeted 6.8 closure entrypoint; it can still rerun `semantic-equivalence-auditor` by issue family or by profile defaults.
- Even when semantic reviewer is added back, `sc-llm-review` now runs primary reviewers first; semantic enters a second stage only after they are clean. This avoids paying the largest semantic prompt cost when code/security is already red.
- If semantic is defer-skipped because an earlier reviewer is not clean yet, that row is ignored by the 6.7 reviewer auto-shrink logic instead of being treated as a fresh semantic failure signal.
- If the latest deterministic pass is already green and this round only changes reviewer/semantic-side files, `run_review_pipeline.py` can still auto-narrow 6.7 to the reviewers that were truly non-OK last time; passing explicit `--llm-agents` disables that auto-shrink.
è¥ semantic reviewer å åç½® reviewer æª clean èè¢« defer-skipï¼è¿æ¡è®°å½ä¸ä¼åè¢« 6.7 ç reviewer auto-shrink è¯¯å½ææ°ç semantic å¤±è´¥ä¿¡å·ã
- `llm_review_needs_fix_fast.py` 作为第 6.8 定向收口脚本，仍可按问题类别或 profile 默认值补跑 `semantic-equivalence-auditor`
- 如果最近一轮已经证明 deterministic 绿，只剩 reviewer 问题，且你这轮只改 reviewer/语义侧文件，`run_review_pipeline.py` 还会进一步把 6.7 自动收窄到“上一轮真正非 OK 的 reviewers”；只有显式传 `--llm-agents` 时才关闭这条自动缩窄

默认 `diff_mode`：

- `summary`

这不是偷工减料，而是把“第六章日常循环”聚焦到最有价值的三类风险：

- 代码正确性
- 安全边界
- 语义等价

其他更重的角色，留给：

- `standard`
- 需要时的定向 `llm_review`
- `Needs Fix` 专项清理

### 4.5 `6.8` 已经不必总是从零起跑

`llm_review_needs_fix_fast.py` 现在的定位是：

- 先尽量复用最近一次成功 deterministic 结果
- 再只针对失败 reviewer 做最小回合清理

因此第六章当前的正确心智模型是：

- `6.7` 负责生成“完整事实面”
- `6.8` 负责在“事实面稳定后”做小范围收敛
- `6.8` 的 round 摘要如果出现 `timeout_agents` / `failure_kind = timeout-no-summary`，应先判定为“观测不足”而不是“事实已 clean”

### 4.6 现在新增了 rerun stop-loss 与更明确的窄路径信号

新增口径：
- 如果最近一轮已经是 deterministic 绿色（`sc-test = ok`、`sc-acceptance-check = ok`），只剩 `sc-llm-review` 不干净，而本轮没有命中 deterministic 相关改动，默认直接阻止再次完整 6.7；应先走 6.8 或 `llm_review_needs_fix_fast.py`。
- 如确实要保留完整重跑，显式传：`py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --allow-full-rerun`。
- 如果最近两轮都卡在同一类 `sc-test` 失败指纹，默认第三次完整 6.7 直接止损；如确需重试，显式传 `--allow-repeat-deterministic-failures`。
- `summary.json` / `latest.json` 现在会带出 `reason`、`reuse_mode`、`diagnostics`，其中重点看：
  - `diagnostics.rerun_guard`
  - `diagnostics.reuse_decision`
  - `diagnostics.acceptance_preflight`
  - `diagnostics.llm_timeout_memory`
- 如果当前同一轮里已经证明 deterministic 绿色，但 `sc-llm-review` 首次长等待就超时，`run_review_pipeline.py` 会把这轮直接止损，不再继续第二次长等待；证据写入 `diagnostics.llm_retry_stop_loss`。
- Even a manual reviewer-only rerun (`--skip-test --skip-acceptance`) is blocked when recent reviewer-only attempts keep repeating the same Needs Fix family; switch to `needs-fix-fast` or record the residual findings instead of reopening 6.7.
- 如果当前同一轮 `sc-test` 已经从 child summary 证明是 `unit` 失败，`run_review_pipeline.py` 会直接停掉同 run 的第二次同参重试；证据写入 `diagnostics.sc_test_retry_stop_loss`，避免把“已知 unit 根因”再付一轮 engine lane 成本。
- 新开 run 默认继承最近同任务的 `delivery/security profile` 组合；如果确实要改 profile，必须显式传 `--reselect-profile`，否则以 profile drift 失败。
- `resume-task` / `dev_cli.py inspect-run --kind pipeline` / active-task sidecar expose the same `latest_summary_signals` and `chapter6_hints`, so operators do not need to guess before reopening a run. They now also expose `Recommended command` / `Forbidden commands` directly. `dev_cli.py inspect-run --kind pipeline` forwards the latest pipeline recommendation fields into its payload, `resume-task` prefers those inspection fields first, and the producer-side `execution-context.json` now mirrors the same recommendation fields for downstream consumers.
- `resume-task` 现在还会带出 approval 恢复字段：`Approval required action`、`Approval status`、`Approval decision`、`Approval reason`。这让操作者在看摘要时就能区分“继续修复”“进入 pause 等审批”“已经允许 fork”三种路径。
- `inspect-run` 对 approval response 的消费现在是确定性的：`pending -> pause`、`approved -> fork`、`denied -> resume`、`invalid/mismatched -> inspect`。它不再把 approval 只当作软提示。
- `run_review_pipeline.py --resume` / `--fork` 也已经接入 approval hard block：`resume` 会阻断 `pending|approved|invalid|mismatched`，`fork` 会阻断 `pending|denied|invalid|mismatched`，避免操作者跳过审批状态机。
- `resume-task --recommendation-only` is the cheapest read path when you only need the next Chapter 6 action; it prints the compact recommendation block and skips default JSON/Markdown writes unless you explicitly request outputs. Add `--recommendation-format json` when the result should be consumed by another script.
- `dev_cli.py inspect-run --recommendation-only` is the fallback compact read path when `resume-task` is still not enough; it prints the next-action block without dumping the full inspection JSON to the terminal. Add `--recommendation-format json` when automation needs the same fields.
- Read `recommended_action_why` whenever it is available; if the action is already `needs-fix-fast`, prefer targeted closure instead of reopening a full `6.7`. If `Recommended command` already points to `needs-fix-fast`, do not reopen a full rerun against that recommendation.
- `run-events.jsonl` 不再只是 append-only 日志；它现在带稳定 taxonomy：`turn_id`、`item_kind`、`item_id`、`event_family`。恢复代理和自动化脚本应按这些字段判断 run/step/sidecar/approval/reviewer 的位置，而不是继续解析自由文本事件名。
- LLM reviewer 超时扩时不再只看“上一轮是否 timeout”，还会记住最近同任务 / 同 profile 的 agent 级有效超时，继续 timeout 时只定向抬高对应 reviewer。

- 读取 `summary.json` / `latest.json` 时，必须同时看 `run_type` 和 `artifact_integrity`；只看 `reason` 和 `reuse_mode` 会漏掉 planned-only terminal bundle。
- 如果恢复链显示 `run_type = planned-only`、`reason = planned_only_incomplete`，或 `Chapter6 blocked by = artifact_integrity`，该 run 只能当作 `planned-only terminal bundle` 证据，不能作为 reopen `6.7` / `6.8` 的 producer run。
- 如果要判断 run 真正停在哪个 item，先读 `run-events.jsonl` 的 taxonomy 字段：`turn_id` 用于区分一次 run 生命周期内的恢复轮次，`item_kind` / `item_id` 用于定位具体 step 或 approval sidecar，`event_family` 用于快速区分 run / step / sidecar / approval / reviewer。
- 对 `planned-only terminal bundle`，应先读 `summary.json`、`repair-guide.md`、`run-events.jsonl` 和 active-task sidecars，然后回退到上一轮真实 bundle，或直接新开真实 run，不要继续 `--resume`。

## 5. 其他 AI 代码助手只读第六章，能否正确操作

结论：

- 可以，但前提是它读到的是“当前仓第六章 + 本文档 + 稳定入口索引”的组合，而不是只抄命令。

如果一个 AI 助手只看到旧版 Chapter 6，常见误操作有：

1. 手工拼 `test.py + acceptance_check.py + llm_review.py`
2. 每次重跑都重新做 `sc-test`，不知道同快照可复用
3. 手工强传 `--security-profile host-safe` 给 `standard`
4. 把 `Needs Fix` 清理当成新一轮完整流水线，而不是在 deterministic 结果上增量处理
5. 误以为“最新 smoke 日志”一定等于“最新 perf 证据”

因此，给其他 AI 助手的最低阅读集应是：

1. `workflow.md` 第六章
2. `docs/workflows/chapter-6-t56-optimization-guide.md`
3. `docs/workflows/stable-public-entrypoints.md`
4. `docs/workflows/script-entrypoints-index.md`
5. `docs/workflows/run-protocol.md`

AI 助手要正确执行第六章，必须遵守这些约束：

1. 统一从 `run_review_pipeline.py` 进入 `6.7`
2. 明白 `same task` 不等于 `same snapshot`；只有相同 git 快照才期待 `sc-test` 复用
3. 如果手工传 `--run-id`，必须是 32 位十六进制
4. 不把 `acceptance_check` 的模板 smoke marker 当 perf 证据
5. 不跳过 `6.1` 和 `6.3`
6. 不在 approval sidecar 为 `pending|invalid|mismatched` 时强行 `--resume` / `--fork`
7. 不把 `run-events.jsonl` 当自由文本日志；恢复自动化必须消费 `turn_id`、`item_kind`、`item_id`、`event_family`

## 6. 旧项目如何升级到本仓当前的第六章能力

### 6.1 升级原则

不要只复制 `workflow.md`。

Chapter 6 的正确升级单位是：

- 入口脚本
- helper 模块
- profile 配置
- schema
- 对应单测
- 文档索引

如果只同步其中一部分，会得到“文档对齐、行为未对齐”的半升级状态。

### 6.2 必须成批迁移的文件

#### A. 核心入口

- `scripts/sc/run_review_pipeline.py`
- `scripts/sc/test.py`
- `scripts/sc/acceptance_check.py`
- `scripts/sc/llm_review.py`
- `scripts/sc/llm_review_needs_fix_fast.py`
- `scripts/sc/check_tdd_execution_plan.py`
- `scripts/python/inspect_run.py`
- `scripts/python/resume_task.py`

#### B. Pipeline / acceptance / recovery helper

- `scripts/sc/_pipeline_plan.py`
- `scripts/sc/_pipeline_support.py`
- `scripts/sc/_pipeline_helpers.py`
- `scripts/sc/_pipeline_session.py`
- `scripts/sc/_pipeline_events.py`
- `scripts/sc/_acceptance_runtime.py`
- `scripts/sc/_acceptance_steps.py`
- `scripts/sc/_acceptance_steps_quality.py`
- `scripts/sc/_sc_test_steps.py`
- `scripts/sc/_approval_contract.py`
- `scripts/sc/_repair_approval.py`
- `scripts/sc/_sidecar_schema.py`
- `scripts/python/_chapter6_recovery_common.py`

#### C. LLM review helper 与 profile 配置

- `scripts/sc/_llm_review_tier.py`
- `scripts/sc/_llm_review_prompting.py`
- `scripts/sc/_llm_review_acceptance.py`
- `scripts/sc/_llm_review_engine.py`
- `scripts/sc/config/delivery_profiles.json`

#### D. 定位单任务 overlay / contract 噪音的配套脚本

- `scripts/python/validate_task_overlays.py`

#### E. Schema

- `scripts/sc/schemas/sc-test-summary.schema.json`
- `scripts/sc/schemas/sc-acceptance-check-summary.schema.json`
- `scripts/sc/schemas/sc-review-pipeline-summary.schema.json`
- `scripts/sc/schemas/sc-review-execution-context.schema.json`
- `scripts/sc/schemas/sc-review-latest-index.schema.json`
- `scripts/sc/schemas/sc-review-repair-guide.schema.json`
- `scripts/sc/schemas/sc-run-event.schema.json`
- `scripts/sc/schemas/sc-harness-capabilities.schema.json`
- `scripts/sc/schemas/sc-approval-request.schema.json`
- `scripts/sc/schemas/sc-approval-response.schema.json`

#### F. 回归测试

至少同步这批与第六章优化直接相关的测试：

- `scripts/sc/tests/test_sc_test_orchestration.py`
- `scripts/sc/tests/test_sc_test_steps.py`
- `scripts/sc/tests/test_acceptance_check_cli_guards.py`
- `scripts/sc/tests/test_acceptance_steps_reuse.py`
- `scripts/sc/tests/test_acceptance_steps_quality.py`
- `scripts/sc/tests/test_run_review_pipeline_delivery_profile.py`
- `scripts/sc/tests/test_run_review_pipeline_preflight.py`
- `scripts/sc/tests/test_run_review_pipeline_marathon.py`
- `scripts/sc/tests/test_pipeline_plan_preflight.py`
- `scripts/sc/tests/test_pipeline_support_snapshots.py`
- `scripts/sc/tests/test_pipeline_sidecar_protocol.py`
- `scripts/sc/tests/test_pipeline_approval.py`
- `scripts/sc/tests/test_llm_review_tier.py`
- `scripts/sc/tests/test_llm_review_prompt_shaping.py`
- `scripts/sc/tests/test_llm_review_needs_fix_fast.py`
- `scripts/sc/tests/test_validate_task_overlays_scope.py`
- `scripts/python/tests/test_inspect_run.py`
- `scripts/python/tests/test_resume_task.py`

#### G. 文档与入口索引

- `workflow.md`
- `workflow.example.md`
- `docs/workflows/stable-public-entrypoints.md`
- `docs/workflows/script-entrypoints-index.md`
- `docs/workflows/run-protocol.md`
- `docs/workflows/local-hard-checks.md`
- `docs/agents/03-persistent-harness.md`
- `docs/agents/06-harness-marathon.md`
- `docs/PROJECT_DOCUMENTATION_INDEX.md`
- 本文档：`docs/workflows/chapter-6-t56-optimization-guide.md`

### 6.3 旧项目升级后的最小验证顺序

在旧项目中，按下面顺序验证，不要跳步：

1. `py -3 scripts/sc/run_review_pipeline.py --task-id <id> --dry-run --skip-test --skip-acceptance --skip-agent-review`
2. `py -3 -m unittest scripts.sc.tests.test_run_review_pipeline_preflight`
3. `py -3 -m unittest scripts.sc.tests.test_sc_test_orchestration`
4. `py -3 -m unittest scripts.sc.tests.test_pipeline_sidecar_protocol scripts.sc.tests.test_pipeline_approval scripts.python.tests.test_inspect_run scripts.python.tests.test_resume_task`
5. 如需真实验证，再执行一次 `py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN"`
6. `py -3 -m unittest scripts.sc.tests.test_acceptance_steps_quality`
7. 选一个已有 task，连续真实跑两次 `run_review_pipeline.py`

第 7 步应满足：

- 第一次运行允许真实执行 `sc-test`
- 第二次在同 git 快照下应复用 `sc-test`
- `acceptance_check` 不得因为“最新日志无 `[PERF]`”而误判失败

### 6.4 旧项目常见升级误区

不要做以下事情：

1. 只升级 `workflow.md`，不升级脚本
2. 只升级 `run_review_pipeline.py`，不升级 `_llm_review_*` 和 `delivery_profiles.json`
3. 只升级 `test.py` / `acceptance_check.py`，不升级 schema
4. 只升级脚本，不升级回归测试
5. 只看 `summary.json`，不看 `run-events.jsonl` 和 `sc-test.log`

## 7. 第六章现在的正确使用口径

对绝大多数日常任务，默认路径应为：

1. `py -3 scripts/python/dev_cli.py resume-task --task-id <id>`
   - For a quick recommendation-only read, use: `py -3 scripts/python/dev_cli.py resume-task --task-id <id> --recommendation-only`
2. `py -3 scripts/sc/check_tdd_execution_plan.py --task-id <id> --tdd-stage red-first --verify unit --execution-plan-policy draft`
3. red / green / refactor
4. `py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship`
5. 只有真的出现 `Needs Fix` 时，再跑 `py -3 scripts/sc/llm_review_needs_fix_fast.py ...`

7. `py -3 scripts/python/dev_cli.py chapter6-route --task-id <id> --recommendation-only`
8. 只有路由明确给出 `preferred_lane = run-6.8` 时，再跑 `py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id <id> --delivery-profile fast-ship --rerun-failing-only --max-rounds 1`
9. `py -3 scripts/python/dev_cli.py run-local-hard-checks --godot-bin "$env:GODOT_BIN"`
- 同一任务重跑前，先看是否改了代码。没改代码才期待 `sc-test` 复用。
- `fast-ship` 现在就是默认日常姿态，不需要额外手工压参数。
- 如果第六章失败，优先看：
  - `summary.json`
  - `repair-guide.md`
  - `run-events.jsonl`
  - `sc-test.log`
  - `child-artifacts/sc-acceptance-check/summary.json`

- During recovery, read `reason`, `run_type`, `reuse_mode`, and `artifact_integrity` first, then decide whether to reopen `6.7` or continue with `6.8`. If you only need a stop-loss / next-step decision, use `py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id <id> --recommendation-only` for the narrow read.
- `resume-task` and `inspect-run` now surface approval routing too: `pending -> pause`、`approved -> fork`、`denied -> resume`、`invalid/mismatched -> inspect`。如果摘要已经进入 `pause`，下一步应处理审批 sidecar，而不是继续脚本重跑。
- `py -3 scripts/python/dev_cli.py chapter6-route --task-id <id> --recommendation-only` is now the stable go/no-go router for this decision. It reads the same recovery artifacts first, then tells you whether to reopen `6.7`, narrow to `6.8`, stop for repo noise, or record residual P2/P3 findings.
- The repo-noise lane now uses three inputs in order: prior route reason, repeated recent failure family, then high-confidence lock/transport/process tokens. This reduces false positives where a task-local deterministic failure used to look like generic inspect-first noise.
- 如果 `active-task` 或 `inspect_run` 已显示 `planned_only_incomplete` / `artifact_integrity`，该 bundle 只能当作证据，不能继续用来做收敛步骤。

### 7.1 Fast mode 最省时执行模板

推荐命令顺序：

1. `py -3 scripts/python/dev_cli.py resume-task --task-id <id>`
   - For a quick recommendation-only read, use: `py -3 scripts/python/dev_cli.py resume-task --task-id <id> --recommendation-only`
2. `py -3 scripts/sc/check_tdd_execution_plan.py --task-id <id> --tdd-stage red-first --verify unit --execution-plan-policy draft`
3. `py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id <id> --tdd-stage red-first --verify unit`
4. `py -3 scripts/sc/build.py tdd --task-id <id> --stage green`
5. `py -3 scripts/sc/build.py tdd --task-id <id> --stage refactor`
6. `py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship`
7. `py -3 scripts/python/dev_cli.py chapter6-route --task-id <id> --recommendation-only`
8. 只有路由明确给出 `preferred_lane = run-6.8` 时，再跑 `py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id <id> --delivery-profile fast-ship --rerun-failing-only --max-rounds 1`
9. `py -3 scripts/python/dev_cli.py run-local-hard-checks --godot-bin "$env:GODOT_BIN"`

省时原则：

- 6.4 首轮用轻验证，不先上 `--verify all`。
- 6.7 先判断故障归属，不把仓库级噪音当成当前任务问题。
- 这个判断优先走 `chapter6-route --recommendation-only`，不要在没读工件前直接再开一轮完整 6.7。
- `run_review_pipeline.py` now consumes the same route signal before a new full rerun. If recovery already says `inspect-first`, `repo-noise-stop`, `fix-deterministic`, or `run-6.8`, the script stops before refactor preflight and downstream cost.
- `llm_review_needs_fix_fast.py` now consumes `chapter6-route` before paying deterministic / LLM cost; if the route does not return `run-6.8`, the script stops instead of reopening the same-shape 6.8 loop.
- `repair-guide.json` / `repair-guide.md` now mirror the same Chapter 6 route stop-loss families, so a blocked rerun explains whether the next action is inspect-first, repo-noise stop, deterministic repair, or targeted `6.8`.
- 6.8 只为新修复的 reviewer 锚点再付一次 LLM 成本。
- deterministic 已 clean 但只剩 P2/P3 证据问题时，优先用 `chapter6-route --record-residual` 记录并止损。
- The same residual rule is now enforced inside `llm_review_needs_fix_fast.py`: when only low-priority residual findings remain, the preflight can record follow-up docs and stop without reopening 6.8.

基于 T14 的补充止损规则：

- 6.4 首轮如果新建 `.gd` 测试文件较多，不要直接上 `--verify all`；先用最便宜的 red 验证口径拿到干净证据。
- 纯 `.cs` 任务默认保持 unit 路径；只有当 task views 明确声明 `.gd` test refs，或本轮显式走 `verify=all|e2e`，才拉入 Godot / GdUnit 重路径。
- 6.7 首轮若在 `sc-test` 就暴露仓库级噪音、锁进程或 `rc=124` 超时，先停下来查 `run-events.jsonl`、`child-artifacts/sc-test/summary.json`、`sc-test.log`，不要连续多次 `--resume`。
- 同一个 run 连续两次在 `sc-test` 失败时，默认判定这个 run 已经没有继续价值；修根因后新开 run。
- 如果上一轮 6.7 已经证明 `sc-test = ok` 且 `sc-acceptance-check = ok`，只有 `sc-llm-review` 超时或失败，而本轮只改了 review / acceptance / overlay / task 语义文本，下一轮应优先复用 deterministic，只重跑 LLM，不要再手工重付 `sc-test + acceptance_check`。
- 但 task semantics 变更不算真正的 docs-only clean reuse；这类改动默认最多只复用 `sc-test`，仍要重跑 `acceptance_check`，避免假绿。
- 一旦改动命中 `Game.Core/**`、`Game.Godot/**`、`Game.Core/Contracts/**`、测试文件、`scripts/**`、`project.godot`、`*.cs`、`*.gd`、`*.tscn`、`*.tres`、`*.csproj`、`*.sln`，就不要再走窄路径，直接回到完整 deterministic。
- 6.8 只有在本轮改动直接命中上一轮 reviewer 锚点时才值得立刻重跑；如果 deterministic 已经稳定通过，剩余只是 P2/P3 证据强度问题，默认记录并止损，不再重复支付 LLM 成本。
- 6.8 reviewer 默认要按问题类别定向收缩：代码问题优先 `code-reviewer`，语义 / acceptance / overlay / task-view 问题优先 `semantic-equivalence-auditor`，安全问题才补 `security-auditor`。
- 如果连续两轮 6.8 都落在同类 `Needs Fix`，且严重度、锚点和建议动作基本不变，默认直接止损并记录，不再开第三轮同口径 reviewer 重跑。
- If a previous 6.8 run only timed out, produced no new actionable finding, and `final_needs_fix_agents` is still empty, inspect and record instead of reusing the same parameters blindly. If `Forbidden commands` already list full rerun / resume, that stop-loss is deliberate and should not be bypassed.
- 如果上一轮只剩 `Unknown/timeout`，而本轮没有命中 reviewer 锚点文件，默认直接止损，不再继续支付同一轮 6.8。
## 8. 最终结论

基于 T56 日志驱动的这轮优化后，本仓第六章已经具备以下性质：

1. 有统一入口，而不是手工三连。
2. 有前置自检，尽量避免晚失败。
3. 有同快照 `sc-test` 复用，重复重跑成本显著下降。
4. `fast-ship` 默认审查成本下降，但仍保留核心风险面。
5. perf gate 不再被模板 smoke 日志误导。
6. 旧项目可以按本文档成批迁移，完整对齐，而不是只对齐表面命令。

如果一个项目做完本文档第 6 节中的迁移和验证，它就可以视为“与 `godotgame` 当前 Chapter 6 能力对齐”。
