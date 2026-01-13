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

本页为 T58 的功能纵切拆页。止损版建筑效果只通过 `multiplier_step_delta` 影响经济，并要求可审计（事件）。

## 范围
- 买地后允许选择建造类型（配置只读）。
- 建造效果：`multiplier_step_delta`（整型步进，1=+0.5）。
- 建造行为发布事件，用于 UI 展示与回放定位。

## 非目标
- 不引入复杂建筑树/升级链。

## 契约（EventType + 触发点）
- `core.sanguo.building.built`：建造完成并对经济/状态产生影响后。

## 验收条款（ACC）
- ACC:T58.1 建造触发后发布 `core.sanguo.building.built`。
- ACC:T58.2 建造效果只通过倍率快照进入经济计算（UI 不计算）。

## Test-Refs
- `Game.Core.Tests/Tasks/Task58BuildingsTests.cs`

