---
PRD-ID: PRD-SANGUO-T2
Title: 08-T65 州郡机制（全占增益 + 连协收费）
Status: Draft
ADR-Refs:
  - ADR-0004
  - ADR-0005
Arch-Refs:
  - CH05
  - CH06
---

# T65：州郡机制（全占增益 + 连协收费）

## 范围
- 州郡机制包含两部分：
  - 全占增益：某州郡内所有城市归属同一角色时立即生效；当城市释放为无主或被夺取导致不再全占时立即失效。
  - 连协收费：当角色落到州郡内的城市 A（owner=X）时，支付金额 = 该州郡内 owner=X 的全部城市的“最终过路费”求和；支付对象始终为落点城市 owner。

## 非目标
- 不实现非经济型州郡增益（后续可扩展）。

## 口径冻结
- 生效/失效：买下最后一座 city 时立即生效；出局释放资产为无主时立即失效；卡牌/宝物夺取城市同样触发生效/失效。
- 影响面：本阶段只做经济型影响（buy/toll/settlement 两类），且全部来自 Core 计算；UI 只展示。
- 连协收费：按 owner 在 region 内的占有城市集合求和；缺失 region 数据 fail-fast。
- 规避：连协收费可被机制（卡牌/宝物）规避，但规避必须通过明确机制能力实现，不是规则例外。

## 契约（EventType + 触发点）
- 连协收费与全占增益对经济的影响必须通过“经济事件倍率快照（applied_multipliers）”体现；如需显式审计事件，后续补充 Contracts（最终以 Contracts 为准）。
- 契约 SSoT（代码）：`Game.Core/Contracts/Sanguo/EconomyEvents.cs`
- 对齐页：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-contracts-taskmap-t50-t65.md`

## 验收条款（ACC）
- ACC:T65.1 全占增益生效/失效时点正确，且只影响本州郡城市的经济点（buy/toll/settlement）。
- ACC:T65.2 连协收费按 owner 在 region 内的占有城市集合求和；缺失 region 数据 fail-fast。
- ACC:T65.3 连协收费可被卡牌/宝物机制规避（规避作为机制能力，不是规则例外）。

## Test-Refs（占位）
- `Game.Core.Tests/Tasks/Task65RegionsMechanicsTests.cs`（占位，待实现）
