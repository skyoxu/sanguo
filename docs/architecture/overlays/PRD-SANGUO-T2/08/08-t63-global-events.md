---
PRD-ID: PRD-SANGUO-T2
Title: 08-T63 全局事件触发机制（RoundNumber）
Status: Draft
ADR-Refs:
  - ADR-0004
  - ADR-0005
Arch-Refs:
  - CH06
---

# T63：全局事件触发机制（RoundNumber）

## 范围
- 全局事件由 `RoundNumber` 驱动（替代季度/年度），每轮最多检查与触发一次。
- 触发点：在每轮开始前（发布 `core.sanguo.game.turn.started` 之前）检查并应用。

## 非目标
- 不实现季度/年度事件（本阶段已弃用）。

## 口径冻结
- 触发频率：每轮最多触发一次（同轮内不重复触发）。
- 复现：同一 random_seed 下事件选择与应用结果可复现（候选 id 升序、picked_index/picked_id/hash）。
- 契约：使用 `core.sanguo.random_event.applied` 表达“事件格/全局事件”的统一应用（Contracts 已定义）。
- 归属：全局事件的 `PlayerId` 绑定为该轮的“首个行动者”（用于事件归属与审计一致性）。
- 兜底：如因冷却/唯一性过滤导致候选为空，则使用兜底事件（冷却为 0 的小收益事件）保证流程可继续。

## 契约（EventType + 触发点）
- `core.sanguo.random_event.applied`：当全局事件被选中并成功应用后（source=global）。

## 验收条款（ACC）
- ACC:T63.1 每轮最多触发一次全局事件检查与应用（同轮内不重复触发）。
- ACC:T63.2 选择与效果应用在同一 random_seed 下可复现。
- ACC:T63.3 触发后发布事件供 UI 展示与复盘（以 `core.sanguo.random_event.applied` 为准）。

## Test-Refs
- `Game.Core.Tests/Tasks/Task63GlobalEventsTests.cs`
