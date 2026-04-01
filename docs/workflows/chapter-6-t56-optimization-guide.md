# Workflow 第六章 T56 优化与升级指南

本文件记录 `workflow.md` 第六章在 `T56` 实战日志驱动下完成的优化、问题闭环、流程变化，以及其他项目如何对齐到本仓当前的完整能力。

适用范围：

- 上游参考模板仓 `godotgame`
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

1. `resume-task`
2. `check_tdd_execution_plan.py`
3. red
4. green
5. refactor
6. `run_review_pipeline.py`
7. 只有需要时再 `llm_review_needs_fix_fast.py`

变化点不是命令变了，而是执行语义更硬了：

- `6.1` 不再只是“找资料”，而是恢复 active-task sidecar、latest pointers、repair guide 的正式入口。
- `6.3` 不再只是一个提醒器，而是决定是否需要 execution-plan、Serena MCP、taskdoc 的轻量分流器。

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
- `semantic-equivalence-auditor`

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

#### B. Pipeline / acceptance / test helper

- `scripts/sc/_pipeline_plan.py`
- `scripts/sc/_pipeline_support.py`
- `scripts/sc/_pipeline_helpers.py`
- `scripts/sc/_pipeline_session.py`
- `scripts/sc/_acceptance_runtime.py`
- `scripts/sc/_acceptance_steps.py`
- `scripts/sc/_acceptance_steps_quality.py`
- `scripts/sc/_sc_test_steps.py`

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
- `scripts/sc/tests/test_llm_review_tier.py`
- `scripts/sc/tests/test_llm_review_prompt_shaping.py`
- `scripts/sc/tests/test_llm_review_needs_fix_fast.py`
- `scripts/sc/tests/test_validate_task_overlays_scope.py`

#### G. 文档与入口索引

- `workflow.md`
- `workflow.example.md`
- `docs/workflows/stable-public-entrypoints.md`
- `docs/workflows/script-entrypoints-index.md`
- `docs/workflows/run-protocol.md`
- `docs/PROJECT_DOCUMENTATION_INDEX.md`
- 本文档：`docs/workflows/chapter-6-t56-optimization-guide.md`

### 6.3 旧项目升级后的最小验证顺序

在旧项目中，按下面顺序验证，不要跳步：

1. `py -3 scripts/sc/run_review_pipeline.py --task-id <id> --dry-run --skip-test --skip-acceptance --skip-agent-review`
2. `py -3 -m unittest scripts.sc.tests.test_run_review_pipeline_preflight`
3. `py -3 -m unittest scripts.sc.tests.test_sc_test_orchestration`
4. 如需真实验证，再执行一次 `py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN"`
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
2. `py -3 scripts/sc/check_tdd_execution_plan.py --task-id <id> --tdd-stage red-first --verify unit --execution-plan-policy draft`
3. red / green / refactor
4. `py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship`
5. 只有真的出现 `Needs Fix` 时，再跑 `py -3 scripts/sc/llm_review_needs_fix_fast.py ...`

额外说明：

- 同一任务重跑前，先看是否改了代码。没改代码才期待 `sc-test` 复用。
- `fast-ship` 现在就是默认日常姿态，不需要额外手工压参数。
- 如果第六章失败，优先看：
  - `summary.json`
  - `repair-guide.md`
  - `run-events.jsonl`
  - `sc-test.log`
  - `child-artifacts/sc-acceptance-check/summary.json`

## 8. 最终结论

基于 T56 日志驱动的这轮优化后，本仓第六章已经具备以下性质：

1. 有统一入口，而不是手工三连。
2. 有前置自检，尽量避免晚失败。
3. 有同快照 `sc-test` 复用，重复重跑成本显著下降。
4. `fast-ship` 默认审查成本下降，但仍保留核心风险面。
5. perf gate 不再被模板 smoke 日志误导。
6. 旧项目可以按本文档成批迁移，完整对齐，而不是只对齐表面命令。

如果一个项目做完本文档第 6 节中的迁移和验证，它就可以视为“与当前模板仓的 Chapter 6 能力对齐”。
