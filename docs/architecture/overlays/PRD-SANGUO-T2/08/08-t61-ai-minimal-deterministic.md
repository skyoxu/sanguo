---
PRD-ID: PRD-SANGUO-T2
Title: 08-T61 AI 最小确定性策略（止损层）
Status: Draft
ADR-Refs:
  - ADR-0004
  - ADR-0005
Arch-Refs:
  - CH06
---

# T61：AI 最小确定性策略（止损层）

## 范围
- AI 最小确定性决策：在买地/跳过、建造/跳过、弃牌等需要选择时给出确定性选择。
- 统一审计：AI 的关键选择必须发布 `core.sanguo.ai.decision.made`（ADR-0004）。

## 非目标
- 不做复杂 AI 状态机、评分模型与学习机制（后续任务）。

## 口径冻结
- 确定性：同一输入（GameStartConfig + random_seed + state + TurnNumber/RoundNumber）下，AI 选择结果 100% 可复现。
- 选择策略（止损）：总是选择“第一个合法选项”（按候选列表稳定排序）。
- RNG：允许使用随机，但必须绑定统一 `rng_context_id = "<stream>:<turn>:<round>:<sourceId>"` 并记录候选集证据（候选 id 升序、picked_index/picked_id/hash）。
- 审计：不得出现“未审计的隐式选择”；审计事件必须包含足够信息复盘“为何合法/为何被选中”。

## 契约（EventType + 触发点）
- `core.sanguo.ai.decision.made`：当 AI 在当前情境做出一个会影响游戏状态推进的选择后。
- 契约 SSoT（代码）：`Game.Core/Contracts/Sanguo/PlayerAndAiEvents.cs`
- 对齐页：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-contracts-taskmap-t50-t65.md`

## 验收条款（ACC）
- ACC:T61.1 同一输入下 AI 选择结果可复现。
- ACC:T61.2 关键决策点均走统一策略与统一审计事件。
- ACC:T61.3 AI 决策事件包含足够信息复盘选择过程。

## Test-Refs（占位）
- `Game.Core.Tests/Tasks/Task61AiDeterminismTests.cs`（占位，待实现）
