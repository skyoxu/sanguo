# OpenSpec 与当前组合的对比记录

本文档只记录判断，暂不推进实际改造。

当前判断：对本仓现阶段来说，`bmad + taskmaster + 本仓 tasks/route/review 脚本` 仍然是更适合的主组合，`OpenSpec` 更适合作为方法论参考，而不是替代当前主工作流。

## 1. 结论

结论：当前组合更强，也更适合本仓。

原因：
- 本仓的目标不只是 spec 管理，而是把游戏任务稳定推进到可恢复、可审查、可收口的交付状态。
- `taskmaster + 任务三联 + overlays + contracts + Chapter 5/6/7 + review pipeline + sidecars` 已经覆盖从任务、语义、实现到恢复的完整闭环。
- `OpenSpec` 更强的是“把变更提案写清楚”和“多工具适配”，不是替你完成游戏项目的正式 TDD、review、Needs Fix 收敛与硬门治理。

因此，当前阶段不建议用 `OpenSpec` 替换本仓主工作流。

## 2. 当前组合为什么更适合本仓

当前组合的优势主要在交付闭环：
- `taskmaster` 负责任务化与任务状态推进。
- triplet / overlays / contracts 把任务、架构、语义和代码边界接起来。
- `workflow.md` 第五章、第六章、第七章提供条件语义稳定化、单任务正式闭环、UI wiring 收口。
- `resume-task`、`chapter6-route`、`inspect-run`、`run_review_pipeline.py`、`llm_review_needs_fix_fast.py` 提供恢复、路由、止损、重跑控制和产物消费能力。
- sidecar / artifact / latest summary 体系解决的是长任务、多轮重试、上下文压缩、审批状态机、重跑成本控制这些真实问题。

这些能力是本仓目前真正的价值所在，`OpenSpec` 不适合直接替换这一层。

## 3. OpenSpec 值得学习的地方

### 3.1 把“当前事实”和“变更提案”分得更清楚
- 可以继续强化当前 source of truth 与变更提案的边界。
- 当前事实仍应以 triplet、overlays、contracts、ADR、active sidecars 为准。
- 提案层可以更轻，但不应直接混入正式执行证据。

### 3.2 轻量 propose / apply / archive 思路
- 对 docs-only、overlay wording、ADR wording、prototype promote 前的小变更，可以以后考虑提供更薄的 change lane。
- 这个 lane 不替代 Chapter 5/6，只服务于低风险、非正式交付类变更。

### 3.3 schema 化的思路
- 可以继续把部分工件和工作流输入做成稳定 schema。
- 值得优先 schema 化的候选包括：prototype record、Chapter 7 UI wiring 输入输出、contract change record、semantic stabilization summary、residual / technical debt record。

### 3.4 多工具接线方式
- 这套思路很适合未来上云或多 agent 接入时复用。
- 特别适合 Phase A / Phase B 阶段，作为“同一工作流内核，对外暴露多个入口”的产品化参考。

### 3.5 archive 不是简单存档
- 如果以后引入更轻的 change lane，应该明确 archive 的语义：
- 变更已被吸收进正式 source of truth。
- 临时变更上下文不再作为活跃执行依据。
- 历史上仍可追溯，但不干扰当前主流程。

## 4. 不建议直接照搬的部分
- 不要用 `OpenSpec` 替换 taskmaster triplet / overlays / sidecars。
- 不要把游戏交付流程退化成只有 proposal/design/tasks 三件套。
- 不要为了贴近 `OpenSpec` 目录结构而破坏本仓现有的 Chapter 5/6/7 顶层编排与恢复协议。
- 不要把正式任务的 recovery / route / review / stop-loss 外移到纯文档层。

## 5. 当前最值得记住的一句话

当前阶段：保留 `bmad + taskmaster + 本仓脚本` 作为主组合。

如果以后要吸收 `OpenSpec`，优先吸收：
- source-of-truth 与 change proposal 的分离
- 轻量 propose / apply / archive lane
- schema 化
- 多工具接线
- archive 语义

暂不吸收：
- 替代现有主工作流
- 替代正式任务的恢复、路由、收口机制

## 6. 当前决策

当前决策：只记录认知，不立即实施优化。

后续如果需要落地，可以优先从以下低风险方向开始：
1. 为 docs-only / overlay wording 类变更设计轻量 change lane。
2. 为 prototype / Chapter 7 / residual 类工件补稳定 schema。
3. 为云端 Phase A / Phase B 补多入口适配层，而不是重写主工作流。
