# Superpowers 与第六章顶层路由编排的对比记录

本文档只记录判断，暂不推进实际改造。

当前判断：对本仓当前阶段来说，`workflow.md` 第六章的顶层路由编排仍然比 GitHub 上的 `superpowers` 项目更适合作为正式任务主流程；`superpowers` 更适合作为通用 agent 工程方法论参考，而不是替代本仓第六章。

## 1. 结论

结论：当前第六章顶层路由编排更适合本仓。

原因：
- `superpowers` 解决的是通用型 agent 开发协作问题，例如设计优先、计划优先、TDD、worktree、子代理协作、代码评审与分支收口。
- 本仓第六章解决的是本仓特有的正式任务闭环问题：恢复、route、stop-loss、6.7/6.8 成本控制、review pipeline、artifact 消费、Needs Fix 收敛。
- 对游戏仓来说，真正高价值的是“按真实工件恢复并收口”，而不是只拥有一套通用开发纪律。

因此，当前阶段不建议用 `superpowers` 替换本仓第六章顶层路由编排。

## 2. 为什么第六章更适合本仓

第六章的优势在于它已经绑定了本仓真实执行环境和真实产物：
- 它知道 `resume-task -> chapter6-route -> inspect-run -> 6.3~6.9` 的恢复顺序。
- 它知道何时进入 `6.7`，何时进入 `6.8`，何时应 `record-residual`，何时必须先止损。
- 它能消费 `summary.json`、`latest.json`、`repair-guide.json`、`execution-context.json`、`run-events.jsonl` 等真实工件。
- 它知道 `planned-only`、`artifact_integrity`、`approval pending`、`rerun_guard`、`llm_retry_stop_loss`、`sc_test_retry_stop_loss` 等真实 stop-loss 信号。
- 它与本仓现有的 taskmaster、triplet、overlays、contracts、review pipeline、Needs Fix 脚本已经形成闭环。

这些能力是本仓正式任务交付的核心，而 `superpowers` 不直接提供这类仓库特化的恢复与收口机制。

## 3. Superpowers 值得学习的地方

### 3.1 更强的 design-before-code 约束
- 对复杂任务，可以在进入重型 `6.4 / 6.5 / 6.7` 之前，再加强一次“设计是否已经足够清楚”的前置判断。
- 这类增强更适合做成复杂任务前置检查，而不是重写第六章主路由。

### 3.2 worktree 隔离思路
- 以后如果要做云端多任务并行、审批通过后 fork、或多任务并行修复，worktree 会比单仓多分支更稳。
- 这尤其适合 Phase A / Phase B 上云后的多工作区场景。

### 3.3 更清晰的两阶段 review
- 第六章现有 `6.7 / 6.8` 已经很强，但未来可以更明确地区分：
- 是否符合 task / overlay / acceptance / ADR 的意图。
- 代码质量、边界、安全性、可维护性是否达标。
- 这属于 review 视角增强，不等于推翻现有 review pipeline。

### 3.4 子任务切分模板化
- 未来可以继续增强“什么时候该拆子任务、什么时候可以并行”的规则模板。
- 但这层应建立在当前 route / sidecar / artifact 体系之上，而不是脱离本仓工件体系单独存在。

### 3.5 更明确的分支收口动作
- 当前本仓更强在执行中途的恢复与收敛。
- 后续如果要补体验，可以在“任务已完成”之后，增加更产品化的收口动作说明，例如 merge / archive / keep / discard 之类的明确出口。

## 4. 不建议直接照搬的部分
- 不要用 `superpowers` 替换第六章顶层路由。
- 不要把本仓 sidecar / artifact / latest / repair-guide / route 信号退化成纯通用技能链。
- 不要让通用型 subagent 协作逻辑覆盖掉本仓已有的 taskmaster、triplet、overlays、contracts、review pipeline 与 stop-loss 协议。
- 不要把游戏仓的正式任务恢复机制，改造成只靠设计文档和计划文档驱动。

## 5. 当前最值得记住的一句话

当前阶段：保留第六章顶层路由编排作为正式任务主入口。

如果以后要吸收 `superpowers`，优先吸收：
- design-before-code 的更强前置约束
- git worktree 隔离
- 更清晰的两阶段 review 视角
- 子任务切分模板化
- 完成后的分支收口体验

暂不吸收：
- 替代第六章主路由
- 替代当前 sidecar / artifact / stop-loss / recovery 协议
- 用通用方法论覆盖游戏仓专用交付逻辑

## 6. 当前决策

当前决策：只记录认知，不立即实施优化。

如果后续需要落地，建议优先从以下低风险方向开始：
1. 为复杂任务补更硬的设计前置检查。
2. 为上云后的多任务并行场景补 worktree 策略。
3. 为 `6.7 / 6.8` 补更清晰的 review 视角拆分，而不是重写主路由。
4. 为任务完成后的收口动作补更明确的出口定义。
