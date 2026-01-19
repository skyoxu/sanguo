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

本页为 T56 的功能纵切拆页。止损版事件效果统一走 `effectKind`（`moneyDelta` / `economyStepDelta`），并由 `random_seed` 保证可复现。

## 范围
- 落到 `event` tile 触发事件。
- 每 N 回合触发全局事件（N 为 5/10/20）。
- 两类触发统一进入 RandomEventPool，按固定顺序执行（与 T52 对齐）。
  - effectKind 白名单：`moneyDelta` / `economyStepDelta`（steps 为整型步进，1=+0.5；最终仍按 T51 口径 clamp）。

## 非目标
- 不引入复杂事件树与文本脚本系统。

## 契约（EventType + 触发点）
- `core.sanguo.random_event.applied`：事件效果应用后（无论来源是 tile 还是全局事件）。

## 契约定义

### 事件
- **SanguoRandomEventApplied** (`core.sanguo.random_event.applied`)
  - 触发时机：随机事件生效后（事件格/全局事件统一）
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
- `Tests.Godot/tests/Integration/test_task56_event_tile_triggers_ui_notification.gd`
