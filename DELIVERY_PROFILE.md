# DELIVERY_PROFILE

## 1. 它是什么

`DELIVERY_PROFILE` 是本仓库的全局交付严格度开关。

它不是一个装饰性的标签，而是一组会真正影响仓库运行行为的参数包。它用于把以下内容统一到同一个模式下：

- CI 默认门禁
- 本地脚本默认参数
- `acceptance_check` 的严格度
- `test.py` 的覆盖率与 smoke 行为
- `run_gate_bundle.py` 的预算与硬门/软门倾向
- LLM 相关脚本的门槛、提示词强度和容错策略
- 默认安全姿态，也就是派生出来的 `SECURITY_PROFILE`
- `agent-review` 后置 sidecar 的执行/退出策略

一句话说清楚：

- `DELIVERY_PROFILE` 决定“当前阶段到底要多严”。

当前配置文件入口：

- `scripts/sc/config/delivery_profiles.json`

当前模板仓默认档位：

- `fast-ship`

## 2. 为什么要有它

这个机制是为了解决一个很容易反复出现的问题：

- 原型期需要先验证可玩性，不需要被重治理拖死。
- 日常开发需要基本质量和主机安全，但不该天天按发版级标准自虐。
- 发版前又必须收紧，不能继续用“差不多能跑”的口径糊过去。

如果没有 `DELIVERY_PROFILE`，团队通常会掉进两个坑：

- 到处手工加参数，最后每个脚本都是不同口径，CI 和本地也不一致。
- 整个仓库永远用一个过严默认值，日常开发速度被门禁长期拖慢。

所以 `DELIVERY_PROFILE` 的初衷就是止损：

- 用一个顶层开关，把“速度”和“治理”之间的平衡显式化。

## 3. 设计原则

这套机制的设计原则是：

- 只保留少量、清晰、可理解的档位。
- 由一个总开关驱动多个脚本，而不是每个脚本各搞一套默认值。
- 复制模板到新项目后，先改配置，不是先满仓库打补丁。
- `SECURITY_PROFILE` 默认从 `DELIVERY_PROFILE` 派生，避免双开关长期漂移。

这也意味着一条重要约束：

- 不要把 `DELIVERY_PROFILE` 变成失控的业务枚举表。

如果未来每个项目都开始新增一堆自定义 profile 名称，这套机制很快就会从“统一入口”退化成“新的复杂度来源”。

## 4. 当前三种模式

### 4.1 `playable-ea`

这是最轻的档位，核心目标是尽快验证“游戏能不能玩”。

适用场景：

- 非常早期的 EA 原型
- 主循环 spike
- 玩法试错分支
- 需要快速确认是否存在明显阻塞问题的阶段

当前口径概览：

- 默认派生 `security_profile = host-safe`
- `build.warn_as_error = false`
- 覆盖率硬门默认关闭
- 验收门禁大部分放宽
- LLM 语义类门禁大部分降级或跳过
- `task_links` 预警预算最高
- `agent_review.mode = skip`，默认不自动执行 reviewer sidecar

你可以把它理解为：

- 优先回答“能不能跑、能不能玩、有没有明显 blocker”。

它不适合作为长期发版默认档位。

### 4.2 `fast-ship`

这是模板当前默认档位，也是最适合日常开发的档位。

适用场景：

- 日常开发
- 功能集成
- 小团队快速商业化推进
- 需要基本质量，但不能被重治理压垮的项目阶段

当前口径概览：

- 默认派生 `security_profile = host-safe`
- `build.warn_as_error = true`
- 覆盖率门禁开启，但阈值低于 `standard`
- 验收门禁保留基础要求，但不过度苛刻
- LLM 审查以告警为主，不是高压强硬门
- `task_links` 预算处于中间值
- `agent_review.mode = warn`，会生成 reviewer sidecar，但 `needs-fix` 不会让主入口失败

你可以把它理解为：

- 优先回答“能不能较快交付，同时不把仓库搞烂”。

### 4.3 `standard`

这是最严的档位，核心目标是收口与发布前硬化。

适用场景：

- 发版前清账
- 重要里程碑前收口
- 合并到稳定主线前的强化检查
- 高风险改动后的严格回归

当前口径概览：

- 默认派生 `security_profile = strict`
- `build.warn_as_error = true`
- 覆盖率阈值最高
- 验收门禁最严格
- LLM 语义类门禁最严格
- `task_links` 预算最紧
- `agent_review.mode = require`，`needs-fix`/`block` 会让主入口返回非 0

你可以把它理解为：

- 优先回答“是否已经达到更稳定、更可发布的状态”。

它不适合作为每一次本地小改动的默认档位。

## 5. 三种模式与项目类型的建议映射

对于你前面提到的三类项目，可以这样映射：

- Windows only 的 PC 单机游戏 EA 简陋版 -> `playable-ea`
- Windows only 的 PC 单机游戏快速开发商业化版 -> `fast-ship`
- Windows only 的 PC 单机游戏正常版本 -> `standard`

但这里有一个容易误判的点：

- `fast-ship` 不是“最松”
- 真正最松的是 `playable-ea`
- `standard` 才是收口档

如果团队只看名字，不看定义，很容易切错档位。

## 6. 解析优先级

当前解析顺序应该理解为：

- CLI 参数 `--delivery-profile`
- 环境变量 `DELIVERY_PROFILE`
- `scripts/sc/config/delivery_profiles.json` 里的 `default_profile`

而 `SECURITY_PROFILE` 的正确定位是：

- 默认由 `DELIVERY_PROFILE` 派生
- 只有在你明确需要打破默认映射时，才手工覆写

这点非常重要。否则你会把一套总开关，又重新拆成两套长期漂移的开关。

## 7. 当前仓库的已验证接线矩阵

下面只列 2026-03-21 已核实的接线，不再使用“已影响或应当影响”这种混合口径。

如果某项只是计划接线，就不应该写进这一节。

| 范围 | 已验证 profile block | 已验证消费者 |
| --- | --- | --- |
| build | `build.warn_as_error` | `scripts/sc/build.py` |
| test / tdd | `test.coverage_gate`、`test.coverage_lines_min`、`test.coverage_branches_min`、`test.smoke_strict` | `scripts/sc/test.py`、`scripts/sc/build/tdd.py` |
| acceptance | `acceptance.strict_adr_status`、`acceptance.strict_test_quality`、`acceptance.strict_quality_rules`、`acceptance.require_task_test_refs`、`acceptance.require_executed_refs`、`acceptance.require_headless_e2e`、`acceptance.subtasks_coverage`、`acceptance.perf_p95_ms` | `scripts/sc/_acceptance_runtime.py`、`scripts/sc/acceptance_check.py`、`scripts/sc/_acceptance_orchestration.py`、`scripts/sc/_pipeline_plan.py` |
| run review pipeline | `acceptance.*` 默认值、`llm_review.semantic_gate`、`agent_review.mode`、默认安全映射 | `scripts/sc/run_review_pipeline.py`、`scripts/sc/_pipeline_session.py`、`scripts/sc/_pipeline_support.py` |
| llm review | `llm_review.agents`、`llm_review.timeout_sec`、`llm_review.agent_timeout_sec`、`llm_review.strict`、`llm_review.semantic_gate`、`llm_review.prompt_budget_gate`、`llm_review.model_reasoning_effort` | `scripts/sc/_llm_review_cli.py`、`scripts/sc/_llm_review_engine.py` |
| llm obligations | `llm_obligations.consensus_runs`、`llm_obligations.timeout_sec`、`llm_obligations.garbled_gate`、`llm_obligations.max_prompt_chars` | `scripts/sc/llm_extract_task_obligations.py` |
| llm semantic family | `llm_semantic_gate_all.consensus_runs`、`llm_semantic_gate_all.timeout_sec`、`llm_semantic_gate_all.model_reasoning_effort`、`llm_semantic_gate_all.max_prompt_chars`、`llm_semantic_gate_all.max_needs_fix`、`llm_semantic_gate_all.max_unknown`、`llm_semantic_gate_all.garbled_gate` | `scripts/sc/llm_semantic_gate_all.py`、`scripts/sc/llm_check_subtasks_coverage.py`、`scripts/sc/llm_align_acceptance_semantics.py` |
| gate bundle | `gate_bundle.task_links_max_warnings`、`gate_bundle.stability_template_hard` | `scripts/python/run_gate_bundle.py` |
| CI / workflow | `delivery_profile` 输入、默认安全映射、Step Summary 输出 | `.github/workflows/ci-windows.yml`、`.github/workflows/windows-quality-gate.yml` |

当前仓库里，`DELIVERY_PROFILE` 确实已经是运行时控制面，不只是文档概念。

但要明确边界：它当前主要统一的是 `scripts/sc/**`、部分 `scripts/python/**` 和 CI workflow 的运行时行为。

### 7.1 当前不应宣称为“已统一 profile 化”的范围

以下内容目前不应被描述成已经由 `DELIVERY_PROFILE` 统一控制：

- ADR / base 文档本身的写作严格度
- `execution-plans/` 与 `decision-logs/` 模板字段策略
- 没有显式接入 `--delivery-profile` 或环境变量解析的一次性脚本
- 非 `sc` 主链路的历史脚本

如果未来要把这些也纳入 profile 控制，正确顺序是：

1. 先补运行逻辑
2. 再补测试
3. 最后再改文档

不要反过来先把文档写成“已经统一”。

### 7.2 这节的核验依据

本节是按以下实现与测试核过的：

- `scripts/sc/config/delivery_profiles.json`
- `scripts/sc/_delivery_profile.py`
- `scripts/sc/tests/test_delivery_profile.py`
- `scripts/sc/tests/test_entrypoint_delivery_profile.py`
- `scripts/sc/tests/test_run_review_pipeline_delivery_profile.py`

## 8. 如何使用

### 8.1 单次命令切换

适合你明确知道这一次要用什么档位。

示例：

```powershell
py -3 scripts/sc/run_review_pipeline.py --task-id 10 --godot-bin "$env:GODOT_BIN" --delivery-profile playable-ea
py -3 scripts/sc/run_review_pipeline.py --task-id 10 --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship
py -3 scripts/sc/run_review_pipeline.py --task-id 10 --godot-bin "$env:GODOT_BIN" --delivery-profile standard
```

#

## 8.2 Task-Level `semantic_review_tier`

`run_review_pipeline.py` now reads an optional task-level review hint from `tasks_back.json` / `tasks_gameplay.json`.

- field name: `semantic_review_tier`
- allowed values: `auto | minimal | targeted | full`
- scope: only affects `sc-llm-review`
- non-scope: does not relax deterministic gates such as `sc-test`, `acceptance_check`, contracts, task links, executed refs, or test refs

Default mapping:

- `playable-ea` -> `minimal`
- `fast-ship` -> `targeted`
- `standard` -> `full`

Automatic stop-loss escalation:

- `priority = P1` escalates at least to `targeted`
- `priority = P0` escalates to `full`
- `contractRefs` / `contract_refs` escalates to `full`
- high-risk semantics also escalate to `full`, including: `security`, `contract`, `workflow`, `pipeline`, `ci`, `release`, `ADR`, `architecture`, `gate`, `sentry`, `performance`

Additional rules:

- explicit CLI `--llm-*` arguments still win over task-tier defaults
- the final effective tier and escalation reasons are written to `execution-context.json`
- `fast-ship` low-risk `minimal` / `targeted` tiers narrow the default reviewer set to `code-reviewer,security-auditor`; `semantic-equivalence-auditor` is added back automatically when the tier escalates to `full`, or when you explicitly override reviewers from CLI
- when the previous run already proved deterministic green and only reviewer/semantic-scope files changed, `playable-ea` / `fast-ship` can also narrow a later `6.7` rerun to the recent non-OK reviewers automatically; explicit `--llm-agents` disables that narrowing

## 8.3 `Needs Fix` and the Unified Technical Debt Register

`run_review_pipeline.py` now writes low-priority review findings into one shared technical debt document instead of creating one task-specific document per run.

Fixed policy:

- `P0/P1`: must-fix, never parked in the debt register
- `P2/P3/P4`: written to `docs/technical-debt.md`

Behavior:

- the register is grouped by task id
- when the same task completes `sc-llm-review` again, the task section is replaced instead of duplicated
- `dry-run`, `skip-llm-review`, failed `llm-review`, or runs without low-priority findings do not overwrite the existing register entry
- per-run sidecar: `logs/ci/<date>/sc-review-pipeline-task-<id>-<run_id>/llm-review-low-priority-findings.json`
