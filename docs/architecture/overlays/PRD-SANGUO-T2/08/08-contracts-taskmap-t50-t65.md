---
PRD-ID: PRD-SANGUO-T2
Title: 08-T50–T65 契约映射（Events/DTO/Interfaces）
Status: Draft
ADR-Refs:
  - ADR-0004
  - ADR-0005
Arch-Refs:
  - CH06
---

# T50–T65 契约映射（Events/DTO/Interfaces）

本页用于把 T50–T65 的验收条款映射到“需要哪些领域事件/DTO/接口契约”，避免实现阶段重复造轮子或破坏既有契约（ADR-0004）。  
本页只列 **EventType + 触发点** 与 **契约位置**，不复制字段细节（字段以 `Game.Core/Contracts/Sanguo/**` 为准）。

## 领域事件（EventType）

- `core.sanguo.game.started`：新游戏配置通过 Core 校验并生成初始状态后。
- `core.sanguo.game.turn.started`：进入某行动者回合。
- `core.sanguo.game.turn.advanced`：推进到下一位行动者；若推进造成一轮结束则 `RoundNumber+1`。
- `core.sanguo.dice.rolled`：掷骰完成。
- `core.sanguo.board.token.moved`：棋子移动完成（逻辑与动画解耦）。
- `core.sanguo.action_card.played`：BeforeRoll 使用行动卡后。
- `core.sanguo.random_event.applied`：随机事件被选中并成功应用后（tile/global/facility 统一用 `EventId` 前缀区分）。
- `core.sanguo.building.built`：建造/升级完成并对状态产生影响后。
- `core.sanguo.combat.started`：PVE 开始（无论是否进入战斗场景）。
- `core.sanguo.combat.ended`：PVE 结束（无论是否进入战斗场景）。
- `core.sanguo.loot.granted`：掉落被发放后（钱/卡/宝物）。
- `core.sanguo.relic.applied`：宝物生效并应用到玩家状态后。
- `core.sanguo.city.bought`：城池购买完成后（经济事件，必须携带 `applied_multipliers`）。
- `core.sanguo.city.toll.paid`：过路费支付完成后（经济事件，必须携带 `applied_multipliers`）。
- `core.sanguo.city.owner.changed`：城市归属变化（买下/释放/夺取等）。
- `core.sanguo.player.eliminated`：玩家出局并释放资产为无主后（审计事件，主日志可选）。
- `core.sanguo.game.ended`：终局判定后（含 `reason_code`）。

## DTO（Contracts）

- `GameStartConfig`（唯一开局输入快照）：`Game.Core/Contracts/Sanguo/GameStartConfig.cs`
- `AppliedMultipliers`（steps 经济倍率快照）：`Game.Core/Contracts/Sanguo/AppliedMultipliers.cs`
- `SanguoMapsCatalog`（地图索引）：`Game.Core/Contracts/Sanguo/SanguoMapsCatalog.cs`
- `SanguoMapDefinitionV2`（地图定义 V2）：`Game.Core/Contracts/Sanguo/SanguoMapDefinitionV2.cs`
- `SanguoRandomEventsCatalog`（随机事件目录）：`Game.Core/Contracts/Sanguo/SanguoRandomEventsCatalog.cs`
- `SanguoActionCardsCatalog`（行动卡目录）：`Game.Core/Contracts/Sanguo/SanguoActionCardsCatalog.cs`
- `SanguoCharactersCatalog`（角色目录）：`Game.Core/Contracts/Sanguo/SanguoCharactersCatalog.cs`
- `SanguoBuildingsCatalog`（建筑目录）：`Game.Core/Contracts/Sanguo/SanguoBuildingsCatalog.cs`
- `SanguoEconomyStepDeltas`（steps 分项）：`Game.Core/Contracts/Sanguo/SanguoCharacterDefinition.cs`
- `SanguoBuildingDefinition`：`Game.Core/Contracts/Sanguo/SanguoBuildingDefinition.cs`

## 接口契约（Interfaces）

- `IEventBus`（发布领域事件）：`Game.Core/Services/EventBus.cs`
- `IRandomNumberGenerator`（确定性随机抽样）：`Game.Core/Utilities/IRandomNumberGenerator.cs`

## 按任务索引（最小）

### T50（开局配置）
- 事件：`core.sanguo.game.started`
- DTO：`GameStartConfig`
- 接口：`IEventBus`

### T51（steps 倍率与快照）
- 事件：所有影响金钱的经济事件必须携带 `AppliedMultipliers`
- DTO：`AppliedMultipliers`

### T52（回合窗口与顺序）
- 事件：`core.sanguo.game.turn.started` / `core.sanguo.action_card.played` / `core.sanguo.dice.rolled` / `core.sanguo.board.token.moved` / `core.sanguo.game.turn.advanced`
- 接口：`IEventBus`

### T56（随机事件）
- 事件：`core.sanguo.random_event.applied`
- 接口：`IRandomNumberGenerator`（抽样必须可复盘）

### T57（行动卡）
- 事件：`core.sanguo.action_card.played`

### T58（建筑）
- 事件：`core.sanguo.building.built`
- DTO：`SanguoBuildingDefinition`

### T59（PVE）
- 事件：`core.sanguo.combat.started` / `core.sanguo.combat.ended` / `core.sanguo.loot.granted`

### T60（终局/结算）
- 事件：`core.sanguo.player.eliminated` / `core.sanguo.city.owner.changed` / `core.sanguo.game.ended`

### T61（AI 最小确定性）
- 事件：`core.sanguo.ai.decision.made`
- 接口：`IRandomNumberGenerator`（若引入随机策略，必须绑定 rng_context 子流）

### T62（宝物）
- 事件：`core.sanguo.loot.granted` / `core.sanguo.relic.applied`

### T63（全局事件）
- 事件：`core.sanguo.random_event.applied`（source=global，EventId 前缀 `global:`）
- 接口：`IRandomNumberGenerator`

### T64（州郡数据）
- 事件：无新增（数据校验失败属于 data_invalid，阻止开始）

### T65（州郡机制）
- 事件：复用经济事件（必须携带 `AppliedMultipliers`），以及必要时通过 `core.sanguo.city.toll.paid` 体现“连协收费”结果



## DTO?Contracts?

- `GameStartConfigValidator`????????????`Game.Core/Contracts/Sanguo/GameStartConfigValidator.cs`
- `SanguoFacilitiesCatalog`???????`Game.Core/Contracts/Sanguo/SanguoFacilitiesCatalog.cs`
- `SanguoRegionsCatalog`???????`Game.Core/Contracts/Sanguo/SanguoRegionsCatalog.cs`
- `SanguoRelicsCatalog`???????`Game.Core/Contracts/Sanguo/SanguoRelicsCatalog.cs`
