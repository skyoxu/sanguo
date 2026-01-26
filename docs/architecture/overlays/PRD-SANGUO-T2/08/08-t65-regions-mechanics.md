---
PRD-ID: PRD-SANGUO-T2
Title: 08-T65 州郡连协收费（经济型止损版）
Status: Draft
ADR-Refs:
  - ADR-0004
  - ADR-0005
  - ADR-0011
  - ADR-0019
Arch-Refs:
  - CH02
  - CH04
  - CH07
  - CH10
---

# T65：州郡连协收费（经济型止损版）

## 范围
- 连协收费（经济型止损版）：当角色落到州郡内的城市 A（owner=X）时，支付金额 = 该州郡内 owner=X 的全部城市“最终过路费”求和；支付对象始终为落点城市 owner。

## 非目标
- 不实现“全占增益/非经济型增益”。
- 不在本任务引入卡牌/宝物对连协收费的实际规避效果（仅预留扩展入口）。

## 口径冻结
- 适用范围：仅当落点城存在 owner，且 owner 不是路过方/自身，并且 owner 在该州郡存在“已拥有城市集合”时才产生连协收费。
- 计算方式：逐城先计算“最终过路费”，再求和；返回 total 与 breakdown，且 total 必须等于 breakdown 金额之和。
- 止损与输入校验：必要数据缺失/不一致/越界时必须拒绝开始或立即 fail-fast（不得静默降级为 0 或部分结果）。
- 规避扩展：允许后续通过“明确的机制能力”对连协收费进行规避扩展；默认实现必须不规避。

## 契约（EventType + 触发点）
- 逐城扣费（经济记账/破产判定的事实来源）：`core.sanguo.city.toll.paid`
  - 含 `AppliedMultipliers`（用于 UI/复盘快照）。
- 连协收费汇总（UI 分组/复盘语义）：`core.sanguo.city.toll.synergy.paid`
  - 仅当本次实际发生 ≥2 次逐城扣费时发布 1 次汇总事件（避免单城时“重复记账”）。
  - `Breakdown[]` 必须覆盖本次实际逐城扣费（至少 `CityId/Amount/AppliedMultipliers`），并包含 expected/paid 的总额与计数字段用于复盘。

## 止损提醒（避免未来返工）
- UI/主日志优先以 `core.sanguo.city.toll.synergy.paid` 作为“本次连协收费”的唯一入口；逐城 `core.sanguo.city.toll.paid` 仅作为明细或审计展示。
- 逐城扣费的 `CityId` 代表“被计费的城市”，不代表路过方的落点；任何基于落点的展示/判定不得从 `core.sanguo.city.toll.paid.CityId` 反推。
- 若发生部分支付（如中途破产），必须使用 `PaidCitiesCount < ExpectedCitiesCount` 与 `PaidTotalAmount != ExpectedTotalAmount` 进行显式标记，避免把“未支付部分”误当作漏事件。

## 验收条款（ACC）
- xUnit: 连协收费计算：对 owner 在同一州郡内的 owned city set 逐城先计算该城的最终过路费，再将逐城结果求和得到 total；返回 breakdown（逐城金额明细），且 total 必须等于 breakdown 金额之和；逐城明细必须与逐城计算结果逐项一致（不得仅靠求和凑对）。 Breakdown order must be stable (sorted by CityId ordinal) for replay. Refs: Game.Core.Tests/Tasks/Task65RegionSynergyTollTests.cs
- xUnit: 适用范围：仅当落点城存在 owner，且 owner 不是路过方/自身，并且 owner 在该州郡存在 owned city set 时才产生连协收费；落点城无主/自身/无城集合时连协收费额外项为 0（breakdown 为空或不包含额外项）；ownerOwnedCityIds 若混入其他州郡城市，必须按落点州郡过滤，过滤后为空则视为无城集合。 ownerOwnedCityIds must be treated as a set (deduplicate CityId; no double-charge). Refs: Game.Core.Tests/Tasks/Task65RegionSynergyTollTests.cs
- xUnit: Must provide an extensible bypass policy hook; default policy must not bypass; when bypassed the result must be 0 and must not compute per-city tolls, and must not publish the summary event core.sanguo.city.toll.synergy.paid. Refs: Game.Core.Tests/Tasks/Task65RegionSynergyTollTests.cs, Game.Core.Tests/Tasks/Task65SynergyTollDomainEventTests.cs
- xUnit: Input validation & loss prevention: if landing city / region assignment (e.g. RegionId missing or blank) / owner / ownerOwnedCityIds / per-city toll inputs are missing, inconsistent, or out-of-range, it must fail fast (throw) and must not silently downgrade to 0 or partial results; it must not publish core.sanguo.city.toll.synergy.paid. Refs: Game.Core.Tests/Tasks/Task65RegionSynergyTollTests.cs, Game.Core.Tests/Tasks/Task65SynergyTollDomainEventTests.cs
- xUnit: When synergy toll triggers and owner has >=2 cities in landing region, publish summary event core.sanguo.city.toll.synergy.paid with at least PayerId, OwnerId, LandingCityId, RegionId, ExpectedTotalAmount, PaidTotalAmount, ExpectedCitiesCount, PaidCitiesCount and Breakdown[{CityId,Amount,AppliedMultipliers}]; ensure PaidTotalAmount == sum(Breakdown.Amount). When not triggered or only 1 city, do not publish it. Refs: Game.Core.Tests/Tasks/Task65SynergyTollDomainEventTests.cs

## Test-Refs
- `Game.Core.Tests/Tasks/Task65RegionSynergyTollTests.cs`
- `Game.Core.Tests/Tasks/Task65SynergyTollDomainEventTests.cs`
