# PRD-SANGUO-T2 契约目录（脚本生成）

本文件为脚本生成产物，用于在开始新任务前快速对齐“当前仓库已落盘的契约（Contracts）”与“任务视图声明的 contractRefs”。

- 生成时间（UTC）: `2026-01-18T08:07:04Z`
- 生成脚本: `scripts/python/generate_contracts_catalog_prd_sanguo_t2.py`
- 事件过滤: 仅收录 `core.sanguo.*`（默认规则；可用脚本参数调整）

## 来源（SSoT 引用）
- PRD: `.taskmaster/docs/prd.txt`
- Overlay（目录）: `docs/architecture/overlays/PRD-SANGUO-T2/08`
- Contracts（代码）: `Game.Core/Contracts/**`
- 任务视图（语义 SSoT）: `.taskmaster/tasks/tasks_back.json`, `.taskmaster/tasks/tasks_gameplay.json`
- 任务母表（结构/标题/状态）: `.taskmaster/tasks/tasks.json`

## 领域事件（Domain Events）

> 规则：事件命名与 `EventType` 常量口径遵循 ADR-0004；本目录只反映“当前代码中已落盘的 EventType”。

### `Game.Core/Contracts/Sanguo/SanguoModuleEvents.cs`
- `core.sanguo.action_card.played` -> `SanguoActionCardPlayed`
- `core.sanguo.building.built` -> `SanguoBuildingBuilt`
- `core.sanguo.random_event.applied` -> `SanguoRandomEventApplied`

### `Game.Core/Contracts/Sanguo/PlayerAndAiEvents.cs`
- `core.sanguo.ai.decision.made` -> `SanguoAiDecisionMade`
- `core.sanguo.player.state.changed` -> `SanguoPlayerStateChanged`

### `Game.Core/Contracts/Sanguo/BoardEvents.cs`
- `core.sanguo.board.token.moved` -> `SanguoTokenMoved`
- `core.sanguo.dice.rolled` -> `SanguoDiceRolled`

### `Game.Core/Contracts/Sanguo/EconomyEvents.cs`
- `core.sanguo.city.bought` -> `SanguoCityBought`
- `core.sanguo.city.owner.changed` -> `SanguoCityOwnerChanged`
- `core.sanguo.city.toll.paid` -> `SanguoCityTollPaid`
- `core.sanguo.economy.month.settled` -> `SanguoMonthSettled`
- `core.sanguo.economy.season.event.applied` -> `SanguoSeasonEventApplied`
- `core.sanguo.economy.year.price.adjusted` -> `SanguoYearPriceAdjusted`

### `Game.Core/Contracts/Sanguo/SanguoCombatContracts.cs`
- `core.sanguo.combat.ended` -> `SanguoCombatEnded`
- `core.sanguo.combat.started` -> `SanguoCombatStarted`

### `Game.Core/Contracts/Sanguo/GameEvents.cs`
- `core.sanguo.game.ended` -> `SanguoGameEnded`
- `core.sanguo.game.loaded` -> `SanguoGameLoaded`
- `core.sanguo.game.saved` -> `SanguoGameSaved`
- `core.sanguo.game.started` -> `SanguoGameStarted`
- `core.sanguo.game.turn.advanced` -> `SanguoGameTurnAdvanced`
- `core.sanguo.game.turn.ended` -> `SanguoGameTurnEnded`
- `core.sanguo.game.turn.started` -> `SanguoGameTurnStarted`
- `core.sanguo.player.eliminated` -> `SanguoPlayerEliminated`

### `Game.Core/Contracts/Sanguo/SanguoLootEvents.cs`
- `core.sanguo.loot.granted` -> `SanguoLootGranted`
- `core.sanguo.relic.applied` -> `SanguoRelicApplied`

## 接口契约（Interfaces）

### Ports（Core -> Adapters）

- `IAudioPlayer` (`Game.Core/Ports/IAudioPlayer.cs`)
- `IDataStore` (`Game.Core/Ports/IDataStore.cs`)
- `IErrorReporter` (`Game.Core/Ports/IErrorReporter.cs`)
- `IInput` (`Game.Core/Ports/IInput.cs`)
- `ILogger` (`Game.Core/Ports/ILogger.cs`)
- `IResourceLoader` (`Game.Core/Ports/IResourceLoader.cs`)
- `ISqlDatabase` (`Game.Core/Ports/ISqlDatabase.cs`)
- `ITime` (`Game.Core/Ports/ITime.cs`)

### Services（Core 内部服务抽象）

- `IEventBus` (`Game.Core/Services/EventBus.cs`)
- `ISanguoAiDecisionPolicy` (`Game.Core/Services/ISanguoAiDecisionPolicy.cs`)
- `IScoreService` (`Game.Core/Services/IScoreService.cs`)

### Repositories（持久化抽象）

- `IAchievementRepository` (`Game.Core/Repositories/IAchievementRepository.cs`)
- `IInventoryRepository` (`Game.Core/Repositories/IInventoryRepository.cs`)
- `ISaveGameRepository` (`Game.Core/Repositories/ISaveGameRepository.cs`)
- `IUserRepository` (`Game.Core/Repositories/IUserRepository.cs`)

## 按任务映射（contractRefs 视角）

> 说明：本节以 `tasks_back.json` 为全量视图；若 `tasks_gameplay.json` 存在对应任务，则同时展示。

### 任务 1: 设置Godot项目
- 母表状态: `done`
- 后端视图: `id=SG-0001` layer=`ci` status=`done`
- 玩法视图: `id=GM-0001` layer=`ci` status=`done`
- contractRefs（Back）: （空）
- contractRefs（Gameplay）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Tests.Godot/tests/Scenes/Smoke/test_main_scene_smoke.gd`

### 任务 2: 创建环形地图数据结构
- 母表状态: `done`
- 后端视图: `id=SG-0002` layer=`core` status=`done`
- 玩法视图: `id=GM-0002` layer=`core` status=`done`
- contractRefs（Back）: `core.sanguo.board.token.moved`, `core.sanguo.city.toll.paid`
- contractRefs（Gameplay）: `core.sanguo.board.token.moved`, `core.sanguo.city.toll.paid`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Domain/ValueObjects/CircularMapPositionTests.cs`

### 任务 3: 实现城池类
- 母表状态: `done`
- 后端视图: `id=SG-0003` layer=`core` status=`done`
- 玩法视图: `id=GM-0003` layer=`core` status=`done`
- contractRefs（Back）: （空）
- contractRefs（Gameplay）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Domain/CityTests.cs`

### 任务 4: 实现玩家类
- 母表状态: `done`
- 后端视图: `id=SG-0004` layer=`core` status=`done`
- 玩法视图: `id=GM-0004` layer=`core` status=`done`
- contractRefs（Back）: （空）
- contractRefs（Gameplay）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Domain/SanguoPlayerTests.cs`

### 任务 5: 实现骰子机制
- 母表状态: `done`
- 后端视图: `id=SG-0005` layer=`core` status=`done`
- 玩法视图: `id=GM-0005` layer=`core` status=`done`
- contractRefs（Back）: `core.sanguo.dice.rolled`
- contractRefs（Gameplay）: `core.sanguo.dice.rolled`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Services/SanguoDiceServiceTests.cs`

### 任务 6: 实现回合管理器
- 母表状态: `done`
- 后端视图: `id=SG-0006` layer=`core` status=`done`
- 玩法视图: `id=GM-0006` layer=`core` status=`done`
- contractRefs（Back）: `core.sanguo.game.turn.started`, `core.sanguo.game.turn.ended`, `core.sanguo.player.eliminated`, `core.sanguo.city.toll.paid`
- contractRefs（Gameplay）: `core.sanguo.game.turn.started`, `core.sanguo.game.turn.ended`, `core.sanguo.player.eliminated`, `core.sanguo.city.toll.paid`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Services/SanguoTurnManagerTests.cs`

### 任务 7: 实现经济结算管理器
- 母表状态: `done`
- 后端视图: `id=SG-0007` layer=`core` status=`done`
- 玩法视图: `id=GM-0007` layer=`core` status=`done`
- contractRefs（Back）: `core.sanguo.economy.month.settled`, `core.sanguo.economy.year.price.adjusted`
- contractRefs（Gameplay）: `core.sanguo.economy.month.settled`, `core.sanguo.economy.year.price.adjusted`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Services/SanguoEconomyManagerTests.cs`

### 任务 8: 实现事件管理器
- 母表状态: `done`
- 后端视图: `id=SG-0008` layer=`core` status=`done`
- 玩法视图: `id=GM-0008` layer=`core` status=`done`
- contractRefs（Back）: `core.sanguo.economy.season.event.applied`, `core.sanguo.player.eliminated`
- contractRefs（Gameplay）: `core.sanguo.economy.season.event.applied`, `core.sanguo.player.eliminated`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Services/EventBusTests.cs`

### 任务 9: 设计UI界面
- 母表状态: `done`
- 后端视图: `id=SG-0009` layer=`adapter` status=`done`
- 玩法视图: `id=GM-0009` layer=`adapter` status=`done`
- contractRefs（Back）: （空）
- contractRefs（Gameplay）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Tests.Godot/tests/UI/test_hud_scene.gd`, `Tests.Godot/tests/UI/test_hud_updates_on_events.gd`, `Game.Core.Tests/Domain/SanguoPlayerViewTests.cs`, `Game.Core.Tests/Tasks/Task9UiBoundaryTests.cs`

### 任务 10: 实现玩家棋子移动
- 母表状态: `done`
- 后端视图: `id=SG-0010` layer=`core` status=`done`
- 玩法视图: `id=GM-0010` layer=`core` status=`done`
- contractRefs（Back）: `core.sanguo.board.token.moved`
- contractRefs（Gameplay）: `core.sanguo.board.token.moved`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Tests.Godot/tests/Scenes/Sanguo/test_sanguo_board_view_token_move.gd`

### 任务 11: 实现AI行为
- 母表状态: `done`
- 后端视图: `id=SG-0011` layer=`core` status=`done`
- 玩法视图: `id=GM-0011` layer=`core` status=`done`
- contractRefs（Back）: `core.sanguo.ai.decision.made`
- contractRefs（Gameplay）: `core.sanguo.ai.decision.made`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Services/SanguoAiBehaviorTests.cs`, `Game.Core.Tests/Services/SanguoAiExecutionTests.cs`, `Game.Core.Tests/Domain/SanguoPlayerViewTests.cs`

### 任务 12: 实现土地购买逻辑
- 母表状态: `done`
- 后端视图: `id=SG-0012` layer=`core` status=`done`
- 玩法视图: `id=GM-0012` layer=`core` status=`done`
- contractRefs（Back）: `core.sanguo.city.bought`, `core.sanguo.player.eliminated`
- contractRefs（Gameplay）: `core.sanguo.city.bought`, `core.sanguo.player.eliminated`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Domain/SanguoPlayerTests.cs`, `Game.Core.Tests/Domain/CityTests.cs`, `Game.Core.Tests/Domain/SanguoBoardStateTests.cs`

### 任务 13: 实现过路费支付逻辑
- 母表状态: `done`
- 后端视图: `id=SG-0013` layer=`core` status=`done`
- 玩法视图: `id=GM-0013` layer=`core` status=`done`
- contractRefs（Back）: `core.sanguo.city.toll.paid`, `core.sanguo.player.eliminated`
- contractRefs（Gameplay）: `core.sanguo.city.toll.paid`, `core.sanguo.player.eliminated`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Services/SanguoEconomyManagerTests.cs`

### 任务 14: 实现月末收益结算
- 母表状态: `done`
- 后端视图: `id=SG-0014` layer=`core` status=`done`
- 玩法视图: `id=GM-0014` layer=`core` status=`done`
- contractRefs（Back）: `core.sanguo.economy.month.settled`
- contractRefs（Gameplay）: `core.sanguo.economy.month.settled`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task14MonthEndSettlementTests.cs`

### 任务 15: 实现季度环境事件
- 母表状态: `done`
- 后端视图: `id=SG-0015` layer=`core` status=`done`
- 玩法视图: `id=GM-0015` layer=`core` status=`done`
- contractRefs（Back）: `core.sanguo.economy.season.event.applied`
- contractRefs（Gameplay）: `core.sanguo.economy.season.event.applied`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task15QuarterEventTests.cs`, `Game.Core.Tests/Services/QuarterlyEnvironmentEventTests.cs`

### 任务 16: 实现年度地价调整
- 母表状态: `done`
- 后端视图: `id=SG-0016` layer=`core` status=`done`
- 玩法视图: `id=GM-0016` layer=`core` status=`done`
- contractRefs（Back）: `core.sanguo.economy.year.price.adjusted`, `core.sanguo.player.eliminated`, `core.sanguo.city.toll.paid`
- contractRefs（Gameplay）: `core.sanguo.economy.year.price.adjusted`, `core.sanguo.player.eliminated`, `core.sanguo.city.toll.paid`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task16YearEndPriceTests.cs`

### 任务 17: 实现回合循环
- 母表状态: `done`
- 后端视图: `id=SG-0017` layer=`core` status=`done`
- 玩法视图: `id=GM-0017` layer=`core` status=`done`
- contractRefs（Back）: `core.sanguo.game.turn.advanced`, `core.sanguo.player.eliminated`
- contractRefs（Gameplay）: `core.sanguo.game.turn.advanced`, `core.sanguo.player.eliminated`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task17TurnTests.cs`, `Game.Core.Tests/Domain/MoneyTests.cs`, `Game.Core.Tests/Domain/SanguoBoardStateTests.cs`, `Tests.Godot/tests/Scenes/Sanguo/test_sanguo_board_view_token_move.gd`, `Tests.Godot/tests/UI/test_hud_updates_on_events.gd`

### 任务 18: 实现存档功能
- 母表状态: `deferred`
- 后端视图: `id=SG-0018` layer=`core` status=`deferred`
- 玩法视图: `id=GM-0018` layer=`core` status=`deferred`
- contractRefs（Back）: `core.sanguo.game.saved`, `core.sanguo.game.loaded`
- contractRefs（Gameplay）: `core.sanguo.game.saved`, `core.sanguo.game.loaded`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task18CoreAssemblyDependencyRulesTests.cs`, `Game.Core.Tests/Utilities/SecureSavePathPolicyTests.cs`, `Game.Core.Tests/Services/SanguoSaveLoadServiceTests.cs`, `Game.Core.Tests/Domain/SanguoSaveLoadEventsTests.cs`, `Tests.Godot/tests/Adapters/test_data_store_adapter.gd`

### 任务 19: 实现UI事件提示
- 母表状态: `done`
- 后端视图: `id=SG-0019` layer=`adapter` status=`done`
- 玩法视图: `id=GM-0019` layer=`adapter` status=`done`
- contractRefs（Back）: `core.sanguo.board.token.moved`, `core.sanguo.city.bought`, `core.sanguo.city.toll.paid`, `core.sanguo.economy.month.settled`, `core.sanguo.economy.season.event.applied`, `core.sanguo.game.ended`
- contractRefs（Gameplay）: `core.sanguo.board.token.moved`, `core.sanguo.city.bought`, `core.sanguo.city.toll.paid`, `core.sanguo.economy.month.settled`, `core.sanguo.economy.season.event.applied`, `core.sanguo.game.ended`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Tests.Godot/tests/UI/test_hud_scene.gd`, `Tests.Godot/tests/UI/test_hud_updates_on_events.gd`

### 任务 20: 实现UI资金显示
- 母表状态: `done`
- 后端视图: `id=SG-0020` layer=`adapter` status=`done`
- 玩法视图: `id=GM-0020` layer=`adapter` status=`done`
- contractRefs（Back）: `core.sanguo.player.state.changed`
- contractRefs（Gameplay）: `core.sanguo.player.state.changed`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Tests.Godot/tests/UI/test_hud_scene.gd`, `Tests.Godot/tests/UI/test_hud_updates_on_events.gd`

### 任务 21: 实现UI日期显示
- 母表状态: `done`
- 后端视图: `id=SG-0021` layer=`adapter` status=`done`
- 玩法视图: `id=GM-0021` layer=`adapter` status=`done`
- contractRefs（Back）: `core.sanguo.game.turn.advanced`
- contractRefs（Gameplay）: `core.sanguo.game.turn.advanced`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Tests.Godot/tests/UI/test_hud_scene.gd`, `Tests.Godot/tests/UI/test_hud_updates_on_events.gd`, `Tests.Godot/tests/UI/test_hud_date_display_reflects_latest_date.gd`

### 任务 22: 实现UI骰子结果显示
- 母表状态: `done`
- 后端视图: `id=SG-0022` layer=`adapter` status=`done`
- 玩法视图: `id=GM-0022` layer=`adapter` status=`done`
- contractRefs（Back）: `core.sanguo.dice.rolled`
- contractRefs（Gameplay）: `core.sanguo.dice.rolled`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Tests.Godot/tests/UI/test_hud_scene.gd`, `Tests.Godot/tests/UI/test_hud_updates_on_events.gd`

### 任务 23: 实现UI城池状态显示
- 母表状态: `done`
- 后端视图: `id=SG-0023` layer=`adapter` status=`done`
- 玩法视图: `id=GM-0023` layer=`adapter` status=`done`
- contractRefs（Back）: `core.sanguo.city.bought`, `core.sanguo.city.toll.paid`, `core.sanguo.economy.season.event.applied`
- contractRefs（Gameplay）: `core.sanguo.city.bought`, `core.sanguo.city.toll.paid`, `core.sanguo.economy.season.event.applied`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Tests.Godot/tests/Scenes/Sanguo/test_sanguo_city_ownership_status_display.gd`

### 任务 24: 实现UI事件日志
- 母表状态: `deferred`
- 后端视图: `id=SG-0024` layer=`adapter` status=`deferred`
- 玩法视图: `id=GM-0024` layer=`adapter` status=`deferred`
- contractRefs（Back）: `core.sanguo.board.token.moved`, `core.sanguo.dice.rolled`, `core.sanguo.city.bought`, `core.sanguo.city.toll.paid`, `core.sanguo.economy.month.settled`, `core.sanguo.economy.season.event.applied`, `core.sanguo.economy.year.price.adjusted`, `core.sanguo.game.turn.advanced`, `core.sanguo.game.ended`
- contractRefs（Gameplay）: `core.sanguo.board.token.moved`, `core.sanguo.dice.rolled`, `core.sanguo.city.bought`, `core.sanguo.city.toll.paid`, `core.sanguo.economy.month.settled`, `core.sanguo.economy.season.event.applied`, `core.sanguo.economy.year.price.adjusted`, `core.sanguo.game.turn.advanced`, `core.sanguo.game.ended`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Tests.Godot/tests/UI/test_hud_scene.gd`, `Tests.Godot/tests/UI/test_hud_updates_on_events.gd`

### 任务 25: 实现AI策略优化
- 母表状态: `done`
- 后端视图: `id=SG-0025` layer=`core` status=`done`
- 玩法视图: `id=GM-0025` layer=`core` status=`done`
- contractRefs（Back）: `core.sanguo.ai.decision.made`
- contractRefs（Gameplay）: `core.sanguo.ai.decision.made`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task25AiTests.cs`

### 任务 26: 实现游戏结束条件
- 母表状态: `done`
- 后端视图: `id=SG-0026` layer=`core` status=`done`
- 玩法视图: （无）
- contractRefs（Back）: `core.sanguo.game.ended`, `core.sanguo.player.eliminated`, `core.sanguo.city.toll.paid`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Utilities/NoGodotDependencyTests.cs`, `Game.Core.Tests/Services/PlayerEliminationTests.cs`

### 任务 27: 实现音效和音乐
- 母表状态: `deferred`
- 后端视图: `id=SG-0027` layer=`adapter` status=`deferred`
- 玩法视图: （无）
- contractRefs（Back）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Tests.Godot/tests/Adapters/Config/test_audio_player_adapter_nodes.gd`, `Tests.Godot/tests/Scenes/Sanguo/test_sanguo_main_music_autoplays.gd`, `Tests.Godot/tests/UI/test_hud_plays_sfx_on_action.gd`, `Tests.Godot/tests/UI/test_hud_sfx_does_not_stop_music.gd`

### 任务 28: 实现游戏主菜单
- 母表状态: `done`
- 后端视图: `id=SG-0028` layer=`adapter` status=`done`
- 玩法视图: （无）
- contractRefs（Back）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Tests.Godot/tests/UI/test_main_menu_scene.gd`, `Tests.Godot/tests/UI/test_main_menu_events.gd`, `Tests.Godot/tests/UI/test_main_menu_load_play_quit_routing.gd`, `Tests.Godot/tests/UI/test_main_menu_quit_button.gd`, `Tests.Godot/tests/Scenes/Smoke/test_menu_quit_is_consumed_by_game_loop.gd`, `Tests.Godot/tests/Scenes/Smoke/test_menu_play_starts_game_loop.gd`, `Tests.Godot/tests/Scenes/Smoke/test_menu_play_start_failure_shows_error.gd`

### 任务 29: 实现游戏设置菜单
- 母表状态: `deferred`
- 后端视图: `id=SG-0029` layer=`adapter` status=`deferred`
- 玩法视图: （无）
- contractRefs（Back）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Tests.Godot/tests/UI/test_settings_panel_scene.gd`, `Tests.Godot/tests/UI/test_settings_panel_logic.gd`, `Tests.Godot/tests/UI/test_settings_panel_closepanel.gd`, `Tests.Godot/tests/UI/test_settings_panel_applies_audio_volume.gd`, `Tests.Godot/tests/UI/test_settings_panel_applies_window_resolution.gd`, `Tests.Godot/tests/UI/test_settings_panel_invalid_resolution_fallback.gd`, `Tests.Godot/tests/UI/test_settings_panel_invalid_volume_clamped.gd`, `Tests.Godot/tests/UI/test_main_menu_settings_opens_settings_panel.gd`

### 任务 30: 实现游戏帮助和教程
- 母表状态: `done`
- 后端视图: `id=SG-0030` layer=`adapter` status=`done`
- 玩法视图: （无）
- contractRefs（Back）: `core.sanguo.dice.rolled`, `core.sanguo.board.token.moved`, `core.sanguo.city.bought`, `core.sanguo.city.toll.paid`, `core.sanguo.economy.month.settled`, `core.sanguo.economy.season.event.applied`, `core.sanguo.economy.year.price.adjusted`, `core.sanguo.game.turn.advanced`, `core.sanguo.game.ended`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Tests.Godot/tests/Scenes/Sanguo/test_sanguo_help_ui_loads_headless.gd`, `Tests.Godot/tests/UI/test_help_tutorial_basic_interactions.gd`, `Tests.Godot/tests/UI/test_help_tutorial_uses_project_theme.gd`, `Tests.Godot/tests/UI/test_help_tutorial_localized_content_non_empty.gd`, `Tests.Godot/tests/UI/test_help_tutorial_toggle_and_navigation.gd`

### 任务 31: 在 Game.Core 落地性能追踪库并接入 CI 性能门禁
- 母表状态: `deferred`
- 后端视图: `id=SG-0031` layer=`core` status=`deferred`
- 玩法视图: （无）
- contractRefs（Back）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task31PerformanceGateTests.cs`

### 任务 32: Observability Autoload 与 Sentry Release Health Gate
- 母表状态: `deferred`
- 后端视图: `id=SG-0032` layer=`adapter` status=`deferred`
- 玩法视图: （无）
- contractRefs（Back）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task32RequirementsTests.cs`, `Tests.Godot/tests/Adapters/Db/test_db_handle_release.gd`, `Game.Core.Tests/Domain/ValueObjects/HealthTests.cs`

### 任务 33: Python 构建驱动脚本与 Windows Release Workflow 整合
- 母表状态: `deferred`
- 后端视图: `id=SG-0033` layer=`ci` status=`deferred`
- 玩法视图: （无）
- contractRefs（Back）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task33WindowsBuildArtifactsTests.cs`, `Game.Core.Tests/Tasks/Task33WindowsReleaseWorkflowTests.cs`, `Game.Core.Tests/Tasks/Task33BuildMetadataDocsTests.cs`, `Game.Core.Tests/Tasks/Task33SmokeExeValidationTests.cs`, `Game.Core.Tests/Tasks/Task33MigrationDocsPresenceTests.cs`, `Game.Core.Tests/Tasks/Task33BuildWindowsCliContractTests.cs`

### 任务 34: 分阶段发布（Canary/Stable）与回滚脚本骨架
- 母表状态: `deferred`
- 后端视图: `id=SG-0034` layer=`ci` status=`deferred`
- 玩法视图: （无）
- contractRefs（Back）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task34RequirementsTests.cs`, `Game.Core.Tests/Domain/ValueObjects/HealthTests.cs`, `Game.Core.Tests/Tasks/Task34StagedReleaseTests.cs`, `Game.Core.Tests/Tasks/Task34RollbackTests.cs`

### 任务 35: 项目级功能验收与文档整合骨架
- 母表状态: `deferred`
- 后端视图: `id=SG-0035` layer=`docs` status=`deferred`
- 玩法视图: （无）
- contractRefs（Back）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task35RequirementsTests.cs`, `Game.Core.Tests/Tasks/Task35ProjectDocumentationTemplatesTests.cs`, `Game.Core.Tests/Tasks/Task35ProjectDocumentationIndexGuidanceTests.cs`, `Game.Core.Tests/Tasks/Task35TemplateNeutralityGuardTests.cs`, `Game.Core.Tests/Tasks/Task35MigrationDocsReferenceCoverageTests.cs`, `Game.Core.Tests/Tasks/Task35PerformanceBaselineTemplateTests.cs`

### 任务 36: 事件命名统一迁移（game.* → core.*.*）
- 母表状态: `deferred`
- 后端视图: `id=SG-0036` layer=`core` status=`deferred`
- 玩法视图: （无）
- contractRefs（Back）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task36EventTests.cs`, `Tests.Godot/tests/Scenes/Sanguo/test_sanguo_event_task36.gd`, `Game.Core.Tests/Domain/CityTests.cs`

### 任务 37: Game.Core Observability 客户端与结构化日志
- 母表状态: `deferred`
- 后端视图: `id=SG-0037` layer=`core` status=`deferred`
- 玩法视图: （无）
- contractRefs（Back）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task37LoggingTests.cs`, `Game.Core.Tests/Domain/CityTests.cs`

### 任务 38: 代码重复率与圈复杂度门禁
- 母表状态: `deferred`
- 后端视图: `id=SG-0038` layer=`ci` status=`deferred`
- 玩法视图: （无）
- contractRefs（Back）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task38GateTests.cs`

### 任务 39: 性能 P95 与审计 JSONL 校验
- 母表状态: `done`
- 后端视图: `id=SG-0039` layer=`ci` status=`done`
- 玩法视图: （无）
- contractRefs（Back）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task39AuditPerformanceTests.cs`

### 任务 40: Signal 健康度验证与安全相关测试门禁
- 母表状态: `deferred`
- 后端视图: `id=SG-0040` layer=`adapter` status=`deferred`
- 玩法视图: （无）
- contractRefs（Back）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Tests.Godot/tests/Scenes/Sanguo/test_sanguo_securitygate_task40.gd`, `Game.Core.Tests/Tasks/Task40SecurityGateTests.cs`, `Game.Core.Tests/Tasks/Task40SignalHealthGateTests.cs`, `Tests.Godot/tests/Integration/Security/test_security_http_block_signal.gd`

### 任务 41: 性能报告与历史追踪（reports/performance/**）
- 母表状态: `deferred`
- 后端视图: `id=SG-0041` layer=`ci` status=`deferred`
- 玩法视图: （无）
- contractRefs（Back）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task41PerformanceTests.cs`

### 任务 42: 独立性能门禁 CI 工作流（performance-gates.yml）
- 母表状态: `deferred`
- 后端视图: `id=SG-0042` layer=`ci` status=`deferred`
- 玩法视图: （无）
- contractRefs（Back）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task42PerformanceGateTests.cs`

### 任务 43: 代码签名与安全分发
- 母表状态: `deferred`
- 后端视图: `id=SG-0043` layer=`ci` status=`deferred`
- 玩法视图: （无）
- contractRefs（Back）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task43SecurityTests.cs`, `Game.Core.Tests/Tasks/Task43CodeSigningPipelineTests.cs`, `Game.Core.Tests/Tasks/Task43CodeSigningAuditTrailTests.cs`

### 任务 44: 导出预设与多配置支持
- 母表状态: `deferred`
- 后端视图: `id=SG-0044` layer=`adapter` status=`deferred`
- 玩法视图: （无）
- contractRefs（Back）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task44RequirementsTests.cs`, `Game.Core.Tests/Tasks/Task44ExportPresetsTests.cs`, `Game.Core.Tests/Tasks/Task44BuildScriptPresetSelectionTests.cs`, `Game.Core.Tests/Tasks/Task44CiExportReleaseJobTests.cs`, `Game.Core.Tests/Tasks/Task44ExportDocsReferencesTests.cs`

### 任务 45: 架构依赖护栏与依赖图校验骨架
- 母表状态: `deferred`
- 后端视图: `id=SG-0045` layer=`ci` status=`deferred`
- 玩法视图: （无）
- contractRefs（Back）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task45RequirementsTests.cs`, `Game.Core.Tests/Tasks/Task45DependencyGuardTests.cs`, `Game.Core.Tests/Tasks/Task45DependencyGuardGateModeTests.cs`, `Game.Core.Tests/Tasks/Task45DependencyGuardOutputArtifactsTests.cs`

### 任务 46: Python 版 headless smoke 封装与 strict 模式开关
- 母表状态: `done`
- 后端视图: `id=SG-0046` layer=`ci` status=`done`
- 玩法视图: （无）
- contractRefs（Back）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task46HeadlessSmokeScriptTests.cs`, `Game.Core.Tests/Tasks/Task46HeadlessSmokeNonStrictTests.cs`, `Game.Core.Tests/Tasks/Task46HeadlessSmokeStrictModeTests.cs`, `Game.Core.Tests/Tasks/Task46HeadlessSmokeCiExampleTests.cs`

### 任务 47: 扩展 quality_gates.py 覆盖率阈值与 GdUnit4 集成
- 母表状态: `done`
- 后端视图: `id=SG-0047` layer=`ci` status=`done`
- 玩法视图: （无）
- contractRefs（Back）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task47QualityGatesCoverageSummaryTests.cs`, `Game.Core.Tests/Tasks/Task47QualityGatesGdUnitAggregationTests.cs`, `Tests.Godot/tests/Integration/test_quality_gates_gdunit_adapters_security_aggregation.gd`, `Tests.Godot/tests/Scenes/Smoke/test_task47_main_scene_smoke_wrapper.gd`, `Game.Core.Tests/Tasks/Task47QualityGatesDocumentationRefsTests.cs`

### 任务 48: Godot 安全适配层增强：外链白名单、文件访问与 OS.execute 守卫
- 母表状态: `deferred`
- 后端视图: `id=SG-0048` layer=`adapter` status=`deferred`
- 玩法视图: （无）
- contractRefs（Back）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task48SecurityTests.cs`, `Tests.Godot/tests/Integration/Security/test_task48_security_http_wrapper.gd`

### 任务 49: Headless smoke strict 稳健化：防 marker 假阳性（smoke session 可自退出）
- 母表状态: `done`
- 后端视图: `id=SG-0049` layer=`ci` status=`done`
- 玩法视图: （无）
- contractRefs（Back）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task49HeadlessSmokeHardeningTests.cs`

### 任务 50: Spine: GameStartConfig 与可复现开局输入
- 母表状态: `deferred`
- 后端视图: `id=SG-0050` layer=`core` status=`deferred`
- 玩法视图: `id=GM-0050` layer=`core` status=`deferred`
- contractRefs（Back）: `core.sanguo.game.started`
- contractRefs（Gameplay）: `core.sanguo.game.started`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-t50-game-start-config.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task50GameStartConfigTests.cs`, `Tests.Godot/tests/UI/test_task50_new_game_setup_flow.gd`

### 任务 51: Spine: 倍率合成规则与 applied_multipliers 事件快照
- 母表状态: `deferred`
- 后端视图: `id=SG-0051` layer=`core` status=`deferred`
- 玩法视图: `id=GM-0051` layer=`core` status=`deferred`
- contractRefs（Back）: `core.sanguo.city.bought`, `core.sanguo.city.toll.paid`, `core.sanguo.economy.month.settled`, `core.sanguo.economy.season.event.applied`, `core.sanguo.economy.year.price.adjusted`
- contractRefs（Gameplay）: `core.sanguo.city.bought`, `core.sanguo.city.toll.paid`, `core.sanguo.economy.month.settled`, `core.sanguo.economy.season.event.applied`, `core.sanguo.economy.year.price.adjusted`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-t51-economy-multipliers-and-applied-multipliers.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task51MultiplierCompositionTests.cs`, `Game.Core.Tests/Tasks/Task51AppliedMultipliersPayloadTests.cs`, `Tests.Godot/tests/Integration/test_task51_ui_does_not_compute_money.gd`

### 任务 52: Spine: 回合窗口锁死（BeforeRoll 行动卡 0/1）与事件触发顺序
- 母表状态: `deferred`
- 后端视图: `id=SG-0052` layer=`core` status=`deferred`
- 玩法视图: `id=GM-0052` layer=`core` status=`deferred`
- contractRefs（Back）: `core.sanguo.game.turn.started`, `core.sanguo.action_card.played`, `core.sanguo.dice.rolled`, `core.sanguo.game.turn.advanced`
- contractRefs（Gameplay）: `core.sanguo.game.turn.started`, `core.sanguo.action_card.played`, `core.sanguo.dice.rolled`, `core.sanguo.game.turn.advanced`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-t52-turn-window-and-event-ordering.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task52TurnPhaseWindowTests.cs`, `Game.Core.Tests/Tasks/Task52EventTriggerOrderTests.cs`, `Game.Core.Tests/Tasks/Task52OutOfOrderEventRegressionTests.cs`

### 任务 53: 模块: 地图配置（多文件）与 Tile 语义
- 母表状态: `deferred`
- 后端视图: `id=SG-0053` layer=`core` status=`deferred`
- 玩法视图: `id=GM-0053` layer=`core` status=`deferred`
- contractRefs（Back）: （空）
- contractRefs（Gameplay）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-t53-map-config.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task53MapConfigParsingTests.cs`, `Game.Core.Tests/Tasks/Task53MapConfigValidationTests.cs`, `Tests.Godot/tests/Scenes/test_task53_map_renders_tile_names.gd`

### 任务 54: 模块: 新游戏配置界面（地图/人数/资金档/全局事件间隔/选角）
- 母表状态: `deferred`
- 后端视图: `id=SG-0054` layer=`adapter` status=`deferred`
- 玩法视图: `id=GM-0054` layer=`adapter` status=`deferred`
- contractRefs（Back）: `core.sanguo.game.started`
- contractRefs（Gameplay）: `core.sanguo.game.started`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-t54-new-game-menu.md`
- test_refs（Back）: `Tests.Godot/tests/UI/test_task54_new_game_setup_ui.gd`, `Game.Core.Tests/Tasks/Task54RoleAssignmentUniquenessTests.cs`, `Tests.Godot/tests/UI/test_task54_hud_shows_name_money_portrait_only.gd`

### 任务 55: 模块: 角色配置（6角色）与初始资金口径
- 母表状态: `deferred`
- 后端视图: `id=SG-0055` layer=`core` status=`deferred`
- 玩法视图: `id=GM-0055` layer=`core` status=`deferred`
- contractRefs（Back）: `core.sanguo.game.started`, `core.sanguo.city.toll.paid`
- contractRefs（Gameplay）: `core.sanguo.game.started`, `core.sanguo.city.toll.paid`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-t55-characters.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task55CharacterConfigParsingTests.cs`, `Game.Core.Tests/Tasks/Task55StartingMoneyComputationTests.cs`, `Game.Core.Tests/Tasks/Task55CharacterMultipliersAppliedTests.cs`

### 任务 56: 模块: 随机事件池（事件格 + 每N回合全局事件）
- 母表状态: `deferred`
- 后端视图: `id=SG-0056` layer=`core` status=`deferred`
- 玩法视图: `id=GM-0056` layer=`core` status=`deferred`
- contractRefs（Back）: `core.sanguo.random_event.applied`
- contractRefs（Gameplay）: `core.sanguo.random_event.applied`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-t56-random-events.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task56RandomEventDeterminismTests.cs`, `Game.Core.Tests/Tasks/Task56EventMultiplierTests.cs`, `Tests.Godot/tests/Integration/test_task56_event_tile_triggers_ui_notification.gd`

### 任务 57: 模块: 行动卡（BeforeRoll）止损版
- 母表状态: `deferred`
- 后端视图: `id=SG-0057` layer=`core` status=`deferred`
- 玩法视图: `id=GM-0057` layer=`core` status=`deferred`
- contractRefs（Back）: `core.sanguo.action_card.played`
- contractRefs（Gameplay）: `core.sanguo.action_card.played`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-t57-action-cards.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task57ActionCardPolicyTests.cs`, `Game.Core.Tests/Tasks/Task57ActionCardWindowTests.cs`, `Tests.Godot/tests/UI/test_task57_action_card_before_roll_flow.gd`

### 任务 58: 模块: 建筑扩展（买地后建造类型）
- 母表状态: `deferred`
- 后端视图: `id=SG-0058` layer=`core` status=`deferred`
- 玩法视图: `id=GM-0058` layer=`core` status=`deferred`
- contractRefs（Back）: `core.sanguo.building.built`
- contractRefs（Gameplay）: `core.sanguo.building.built`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-t58-buildings.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task58BuildingConfigAndEffectsTests.cs`, `Game.Core.Tests/Tasks/Task58BuildingBuildWindowTests.cs`, `Tests.Godot/tests/UI/test_task58_city_actions_build_and_owner_label.gd`

### 任务 59: 模块: 战斗（PVE）触发与回主循环
- 母表状态: `deferred`
- 后端视图: `id=SG-0059` layer=`core` status=`deferred`
- 玩法视图: `id=GM-0059` layer=`core` status=`deferred`
- contractRefs（Back）: `core.sanguo.combat.started`, `core.sanguo.combat.ended`
- contractRefs（Gameplay）: `core.sanguo.combat.started`, `core.sanguo.combat.ended`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-t59-combat-pve.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task59CombatTriggerAndReturnTests.cs`, `Game.Core.Tests/Tasks/Task59CombatDeterminismTests.cs`, `Tests.Godot/tests/Scenes/test_task59_pve_combat_scene_roundtrip.gd`

### 任务 60: 模块: 每局胜利与结算界面
- 母表状态: `deferred`
- 后端视图: `id=SG-0060` layer=`adapter` status=`deferred`
- 玩法视图: `id=GM-0060` layer=`adapter` status=`deferred`
- contractRefs（Back）: `core.sanguo.game.ended`
- contractRefs（Gameplay）: `core.sanguo.game.ended`
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-t60-game-end-and-settlement.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task60GameEndEventContractTests.cs`, `Tests.Godot/tests/UI/test_task60_game_end_summary_ui.gd`

### 任务 61: 模块: AI 最小确定性策略（止损版）
- 母表状态: `deferred`
- 后端视图: `id=SG-0061` layer=`core` status=`deferred`
- 玩法视图: `id=GM-0061` layer=`core` status=`deferred`
- contractRefs（Back）: （空）
- contractRefs（Gameplay）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-t61-ai-minimal-deterministic.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task61AiDeterministicStrategyTests.cs`

### 任务 62: 模块: 宝物系统（relics）止损版
- 母表状态: `deferred`
- 后端视图: `id=SG-0062` layer=`core` status=`deferred`
- 玩法视图: `id=GM-0062` layer=`core` status=`deferred`
- contractRefs（Back）: （空）
- contractRefs（Gameplay）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-t62-relics.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task62RelicsTests.cs`

### 任务 63: 模块: 全局事件触发机制（RoundNumber）
- 母表状态: `deferred`
- 后端视图: `id=SG-0063` layer=`core` status=`deferred`
- 玩法视图: `id=GM-0063` layer=`core` status=`deferred`
- contractRefs（Back）: （空）
- contractRefs（Gameplay）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-t63-global-events.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task63GlobalEventsTests.cs`

### 任务 64: 模块: 州郡（regions）配置与全占增益
- 母表状态: `deferred`
- 后端视图: `id=SG-0064` layer=`core` status=`deferred`
- 玩法视图: `id=GM-0064` layer=`core` status=`deferred`
- contractRefs（Back）: （空）
- contractRefs（Gameplay）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-t64-regions.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task64RegionsTests.cs`

### 任务 65: 模块: 州郡连协收费（经济型止损版）
- 母表状态: `deferred`
- 后端视图: `id=SG-0065` layer=`core` status=`deferred`
- 玩法视图: `id=GM-0065` layer=`core` status=`deferred`
- contractRefs（Back）: （空）
- contractRefs（Gameplay）: （空）
- overlay_refs（Back）: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`, `docs/architecture/overlays/PRD-SANGUO-T2/08/08-t65-regions-mechanics.md`
- test_refs（Back）: `Game.Core.Tests/Tasks/Task65RegionSynergyTollTests.cs`
