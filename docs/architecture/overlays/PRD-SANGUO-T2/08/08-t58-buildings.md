---
PRD-ID: PRD-SANGUO-T2
Title: 08-T58 建筑扩展（买地后建造类型）
Status: Draft
ADR-Refs:
  - ADR-0004
Arch-Refs:
  - CH05
  - CH06
---

# T58：建筑扩展（买地后建造类型）

本页为 T58 的功能纵切拆页。止损版建筑效果只通过 steps（0.5 步进）体系影响经济，并要求可审计（事件）。

## 范围
- 买地后允许选择建造类型（配置只读）。
- 建造/升级成本与结算收益来自配置（base 值 + steps）。
- 建造效果：`economyStepDeltas`（steps 为整型步进，1=+0.5；最终仍按 T51 口径 clamp）。
- 建造行为发布事件，用于 UI 展示与回放定位。

## 非目标
- 不引入复杂建筑树/升级链。

## 口径冻结
- 建筑“未建造”= 该 tile 的 building 状态列表中不存在该 `building_id`；首次建造直接落 `level=1`，升级递增直到 `max_level`（不使用 `level=0` 作为哨兵值）。

## 契约（EventType + 触发点）
- `core.sanguo.building.built`：建造完成并对经济/状态产生影响后。

## 验收条款（ACC）
- ACC:T58.1 建造触发后发布 `core.sanguo.building.built`。
- ACC:T58.2 建造效果只通过倍率快照进入经济计算（UI 不计算）。

## Test-Refs
- `Game.Core.Tests/Tasks/Task58BuildingsTests.cs`
