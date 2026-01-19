---
PRD-ID: PRD-SANGUO-T2
Title: 08-T62 宝物系统（Relics）
Status: Draft
ADR-Refs:
  - ADR-0004
  - ADR-0005
  - ADR-0019
Arch-Refs:
  - CH05
  - CH06
---

# T62：宝物系统（Relics）

## 范围
- 宝物（Relics）在战斗/事件/设施掉落后立刻生效；效果为永久有效。
- 同局唯一：`relic_id` 同一局内不得重复；重复则重抽，耗尽候选则返回 null 并写入审计。
- 稳定应用顺序：多宝物同时生效时按 `relic_id` 升序应用（保证同输入复现同输出）。
  - effectKind 白名单：`moneyDelta` / `economyStepDelta`（steps 为整型步进，1=+0.5；最终仍按 T51 口径 clamp）。

## 非目标
- 不实现宝物的 UI 详情面板与复杂联动（后续任务）。

## 口径冻结
- 掉落：允许来自 event tile、facility 与 PVE 掉落。
- 叠加：宝物效果与事件/卡牌效果可叠加生效；宝物本身永久有效。
- 审计：掉落结果（含“空掉落”）必须写入审计；主日志是否展示由 UI 策略决定。
- 不使用“max_id 兜底”：候选耗尽即返回 null。

## 契约（EventType + 触发点）
- `core.sanguo.loot.granted`：宝物/卡牌/金钱等掉落被发放后（无论来源是战斗/事件/设施）。
- `core.sanguo.relic.applied`：宝物生效并应用到玩家状态后。
- 经济侧影响仍通过经济事件的 `applied_multipliers` 快照对外暴露（UI 只展示）。
- 契约 SSoT（代码）：`Game.Core/Contracts/Sanguo/SanguoLootEvents.cs`、`Game.Core/Contracts/Sanguo/EconomyEvents.cs`
- 数据契约 SSoT（代码）：`Game.Core/Contracts/Sanguo/SanguoRelicsCatalog.cs`
- 对齐页：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-contracts-taskmap-t50-t65.md`

## 验收条款（ACC）
- ACC:T62.1 宝物掉落能被记录并立刻生效，且同局内不重复。
- ACC:T62.2 同一输入下宝物应用顺序与最终效果可复现。
- ACC:T62.3 掉落与生效产生可审计的域事件（以 Contracts 为准）。

## Test-Refs
- `Game.Core.Tests/Tasks/Task62RelicsTests.cs`
