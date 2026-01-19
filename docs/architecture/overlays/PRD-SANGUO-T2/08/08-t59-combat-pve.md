---
PRD-ID: PRD-SANGUO-T2
Title: 08-T59 战斗（PVE）触发与回主循环
Status: Draft
ADR-Refs:
  - ADR-0004
Arch-Refs:
  - CH06
---

# T59：战斗（PVE）触发与回主循环

本页为 T59 的功能纵切拆页。止损版战斗只要求“可进入、可退出、可复现”，并能回到主循环继续回合推进。

## 范围
- 落到指定 tile 或事件触发进入 PVE。
- 战斗结束后回到主循环（继续回合）。

## 非目标
- 不做 PVP。
- 不做复杂战斗系统与数值成长。

## 口径冻结
- 无论是否进入战斗场景，结果计算与事件字段必须一致；AI 一律不进入场景但仍发布 started/ended。
- `core.sanguo.combat.ended` 结果字段至少包含 `base_rating` / `effective_rating` / `encounter_target` / `won`。
- relic_id 同局唯一；重复掉落则重抽，耗尽候选则返回 null 并写入审计（不使用“max_id 兜底”）。

## 契约（EventType + 触发点）
- `core.sanguo.combat.started`：进入战斗场景时。
- `core.sanguo.combat.ended`：战斗结束并回到主循环时。

## 验收条款（ACC）
- ACC:T59.1 触发战斗时发布 `core.sanguo.combat.started`。
- ACC:T59.2 战斗结束后发布 `core.sanguo.combat.ended` 并返回主循环。

## Test-Refs
- `Game.Core.Tests/Tasks/Task59CombatTriggerAndReturnTests.cs`
- `Game.Core.Tests/Tasks/Task59CombatDeterminismTests.cs`
- `Tests.Godot/tests/Scenes/test_task59_pve_combat_scene_roundtrip.gd`

