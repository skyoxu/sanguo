---
PRD-ID: PRD-SANGUO-T2
Title: 08-T51 倍率合成与 applied_multipliers（事件快照）
Status: Draft
ADR-Refs:
  - ADR-0004
  - ADR-0005
Arch-Refs:
  - CH01
  - CH06
---

# T51：倍率合成与 applied_multipliers（事件快照）

本页为 T51 的功能纵切拆页。经济数值计算只在 Core 发生，UI 只展示事件/投影字段（ADR-0004）。

## 范围
- 统一倍率合成规则（steps + clamp + 单次乘法）：
  - `base_steps = 2`（= 1.0x）
  - `effective_steps = clamp(base_steps + sum(step_delta), 1, 6)`
  - `effective_multiplier = effective_steps * 0.5`
  - `amount = floor(base_amount * effective_multiplier)`（仅此处发生金额乘法；UI 不参与计算）
- 统一步进：止损版仅允许 0.5 步进（内部用 int steps 表达：`1..6` 对应 `0.5x..3.0x`；`step_delta` 为整型加法）。
- 经济相关域事件 payload 必须包含 `applied_multipliers`（只读快照），记录本次实际使用的 steps breakdown 与 `effective_multiplier`（UI 只展示）。

## 非目标
- 不支持任意小数倍率（避免测试爆炸与回放不稳定）。
- UI 不推导、不复算、不猜测分项倍率来源。

## 契约（EventType + 触发点）
- 任何“影响金钱数值”的域事件在发布时必须携带 `applied_multipliers`（买地/收租/月末结算/建造收益/事件效果等）。

## 验收条款（ACC）
- ACC:T51.1 任意组合输入下 `effective_steps` 必须 clamp 到 [1, 6]（对应 `0.5x..3.0x`），且只允许 0.5 步进。
- ACC:T51.2 经济相关域事件 payload 必含 `applied_multipliers`（只读快照）。
- ACC:T51.3 UI 事件日志仅展示事件里的倍率快照，不参与计算。

## Test-Refs
- `Game.Core.Tests/Tasks/Task51MultiplierCompositionTests.cs`
- `Game.Core.Tests/Tasks/Task51AppliedMultipliersPayloadTests.cs`
- `Tests.Godot/tests/Integration/test_task51_ui_does_not_compute_money.gd`

