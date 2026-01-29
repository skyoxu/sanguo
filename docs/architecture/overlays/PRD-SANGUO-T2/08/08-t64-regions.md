---
PRD-ID: PRD-SANGUO-T2
Title: 08-T64 州郡数据模型（Regions）
Status: Draft
ADR-Refs:
  - ADR-0019
  - ADR-0005
Arch-Refs:
  - CH05
---

# T64：州郡数据模型（Regions）

## 范围
- 州郡（Regions）为配置数据模型：用于表达“州郡全占增益”与“州郡连协收费”的边界。
- region_id 跨地图复用：同一 region_id 可以在不同地图出现（用于复用增益配置）。

## 非目标
- 不实现地图编辑器与运行时热更新。

## 口径冻结
- 数据来源：配置只读，路径与白名单约束遵循 ADR-0019。
- 校验：地图加载时校验 region 定义与 tile.region_id 引用完整性；缺失/越界 fail-fast。
- i18n：region 的 name/description 一律使用 i18n key，不直接写展示文本。

## 契约（EventType + 触发点）
- 当前阶段优先在加载校验失败时走错误上报/审计；显式事件待后续任务补充（以 Contracts 为准）。


## 契约定义

### 事件
- **SanguoRegionCaptured** (`core.sanguo.region.captured`)
  - 触发时机：玩家达成州郡全占时
  - 字段：GameId, RegionId, OwnerId, CityIds, ReasonCode, OccurredAt, CorrelationId, CausationId
  - 契约位置：`Game.Core/Contracts/Sanguo/SanguoRegionEvents.cs`
- **SanguoRegionLost** (`core.sanguo.region.lost`)
  - 触发时机：州郡全占状态失效时
  - 字段：GameId, RegionId, OwnerId, ReasonCode, TriggerCityId, OccurredAt, CorrelationId, CausationId
  - 契约位置：`Game.Core/Contracts/Sanguo/SanguoRegionEvents.cs`

## 验收条款（ACC）
- ACC:T64.1 Regions catalog loads from res://Data/regions.json; missing/unparseable/missing required fields => initialization fails and refuses to start.
- ACC:T64.2 regionId is reusable across maps; when loading/validating a map, every city tile must provide regionId and it must exist in the regions catalog; missing/unknown => initialization fails and refuses to start.
- ACC:T64.3 Region bonus activates immediately when a region becomes fully owned by one actor; it deactivates immediately when any ownership change breaks the condition (taken over or becomes unowned).
- ACC:T64.4 Region bonus uses economyStepDeltas step deltas at this stage; it applies only to cities in that region; other regions remain unchanged; once deactivated it no longer applies.

## Test-Refs
- `Game.Core.Tests/Tasks/Task64RegionsTests.cs`
