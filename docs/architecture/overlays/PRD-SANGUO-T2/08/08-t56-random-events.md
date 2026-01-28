---
PRD-ID: PRD-SANGUO-T2
Title: 08-T56 随机事件池（事件格 + 每N回合全局事件）
Status: Draft
ADR-Refs:
  - ADR-0004
Arch-Refs:
  - CH06
---

# T56：随机事件池（事件格 + 每N回合全局事件）

本页为 T56 的功能纵切拆页。止损版事件效果统一走 `effectKind`（`moneyDelta` / `economyStepDelta` / `startCombat`），并由 `random_seed` 保证可复现。

## 范围
- 落到 `event` tile 触发事件。
- 每 N 回合触发全局事件（N 为 5/10/20）。
- 两类触发统一进入 RandomEventPool，按固定顺序执行（与 T52 对齐）。
  - effectKind 白名单：`moneyDelta` / `economyStepDelta` / `startCombat`（steps 为整型步进，1=+0.5；最终仍按 T51 口径 clamp）。
    - 约束：`startCombat` 仅允许用于 tile 事件；全局事件若抽到 `startCombat` 必须发布 `core.sanguo.random_event.rejected`（`rejectReason=effect_kind_not_allowed_for_global_events`）并不得产生数值变化。
  - 事件池拆分：
    - tile 触发使用 poolId=`default`
    - 全局触发使用 poolId=`global`
  - 冷却与唯一（per player）：
    - `cooldownRounds`：在冷却期内不得再次生效；当 pool 中无任何可选事件时发布 `core.sanguo.random_event.rejected`（`rejectReason=no_eligible_candidates`），不得产生数值变化。
    - `uniqueOnce=true`：同一玩家最多生效一次；再次触发同样走 rejected（`no_eligible_candidates`）。
  - RNG 子流隔离：
    - Random events 的抽样索引使用 `random_seed + rng_context_id + candidates hash` 派生种子（不消耗主 RNG），避免骰子/其他随机调用扰动事件选择。

## 非目标
- 不引入复杂事件树与文本脚本系统。

## 契约（EventType + 触发点）
- `core.sanguo.random_event.applied`：事件效果应用后（无论来源是 tile 还是全局事件）。
- `core.sanguo.random_event.rejected`：事件被选中但因白名单/数据缺失等原因被拒绝（不得产生数值变化）。

## 契约定义

### 事件
- **SanguoRandomEventApplied** (`core.sanguo.random_event.applied`)
  - 触发时机：随机事件生效后（事件格/全局事件统一）
  - 字段：GameId, PlayerId, EventId, EffectKind, MoneyDelta, StepDelta, OccurredAt, CorrelationId, CausationId, RngContextId, CandidatesSortedIdsHash, PickedIndex, PickedId, AppliedMultipliersAfter, EncounterId, EncounterTarget, TriggerSource
  - 触发来源：TriggerSource = tile / global
  - 契约位置：`Game.Core/Contracts/Sanguo/SanguoModuleEvents.cs`
- **SanguoRandomEventRejected** (`core.sanguo.random_event.rejected`)
  - 触发时机：随机事件被选中但因 effectKind 非白名单/缺失必要字段而被拒绝
  - 字段：GameId, PlayerId, EventId, EffectKind, RejectReason, MoneyDelta, StepDelta, OccurredAt, CorrelationId, CausationId, RngContextId, CandidatesSortedIdsHash, PickedIndex, PickedId, EncounterId, EncounterTarget, TriggerSource
  - 触发来源：TriggerSource = tile / global
  - 契约位置：`Game.Core/Contracts/Sanguo/SanguoModuleEvents.cs`

### DTO
- **SanguoRandomEventsCatalog**
  - 用途：随机事件目录（events + pools；只读）
  - 字段：`SchemaVersion`, `Version`, `Events[]`, `EventPools[]`
  - 契约位置：`Game.Core/Contracts/Sanguo/SanguoRandomEventsCatalog.cs`

## 验收条款（ACC）
- ACC:T56.1 事件格触发能从池中取出事件并应用。
- ACC:T56.2 每 N 回合全局事件触发稳定可复现（由 seed 驱动）。

## Test-Refs
- `Game.Core.Tests/Tasks/Task56RandomEventDeterminismTests.cs`
- `Game.Core.Tests/Tasks/Task56EventMultiplierTests.cs`
- `Tests.Godot/tests/UI/test_task56_hud_event_prompt_uses_payload.gd`
