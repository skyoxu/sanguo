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

## 验收条款（ACC）
- ACC:T64.1 地图加载时校验 region 定义与引用完整性；缺失/越界 fail-fast。
- ACC:T64.2 name/description 走 i18n key（地图索引与 region 均用 key）。

## Test-Refs
- `Game.Core.Tests/Tasks/Task64RegionsTests.cs`
