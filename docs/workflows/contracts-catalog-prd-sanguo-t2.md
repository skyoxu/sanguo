# T2 契约目录（按类别 + 按任务映射）

本文件为派生文档：从现有代码与任务视图中提取“当前仓库已落盘的契约”，用于在开始新任务前快速对齐。

## 来源（SSoT 引用）
- PRD：`.taskmaster/docs/prd.txt`
- Overlay：`C:/buildgame/sanguo/docs/architecture/overlays/PRD-SANGUO-T2/08/08-Contracts-CloudEvent.md`
- Overlay：`C:/buildgame/sanguo/docs/architecture/overlays/PRD-SANGUO-T2/08/08-Contracts-CloudEvents-Core.md`
- Overlay：`C:/buildgame/sanguo/docs/architecture/overlays/PRD-SANGUO-T2/08/08-Contracts-Sanguo-GameLoop-Events.md`
- Overlay：`C:/buildgame/sanguo/docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- Overlay：`C:/buildgame/sanguo/docs/architecture/overlays/PRD-SANGUO-T2/08/08-t2-city-ownership-model.md`
- Contracts（代码）：`Game.Core/Contracts/**`
- 任务视图（SSoT for contractRefs）：`.taskmaster/tasks/tasks_back.json`、`.taskmaster/tasks/tasks_gameplay.json`

## CloudEvents 对齐（最小子集）

DomainEvent 字段映射：`SpecVersion→specversion`、`Type→type`、`Source→source`、`Id→id`、`Timestamp→time`、`DataContentType→datacontenttype`、`Data→data`（并用 `IEventData` 限制载荷类型面）。

## 领域事件（Domain Events）

> 规则：每个事件必须包含 `public const string EventType`（见 Overlay：CloudEvents Core 口径）。

### `GuildMemberJoined.cs`
- `core.guild.member.joined` → `GuildMemberJoined`（`C:/buildgame/sanguo/Game.Core/Contracts/Guild/GuildMemberJoined.cs`）

### `BoardEvents.cs`
- `core.sanguo.board.token.moved` → `SanguoTokenMoved`（`C:/buildgame/sanguo/Game.Core/Contracts/Sanguo/BoardEvents.cs`）
- `core.sanguo.dice.rolled` → `SanguoDiceRolled`（`C:/buildgame/sanguo/Game.Core/Contracts/Sanguo/BoardEvents.cs`）

### `EconomyEvents.cs`
- `core.sanguo.city.bought` → `SanguoCityBought`（`C:/buildgame/sanguo/Game.Core/Contracts/Sanguo/EconomyEvents.cs`）
- `core.sanguo.city.toll.paid` → `SanguoCityTollPaid`（`C:/buildgame/sanguo/Game.Core/Contracts/Sanguo/EconomyEvents.cs`）
- `core.sanguo.economy.month.settled` → `SanguoMonthSettled`（`C:/buildgame/sanguo/Game.Core/Contracts/Sanguo/EconomyEvents.cs`）
- `core.sanguo.economy.season.event.applied` → `SanguoSeasonEventApplied`（`C:/buildgame/sanguo/Game.Core/Contracts/Sanguo/EconomyEvents.cs`）
- `core.sanguo.economy.year.price.adjusted` → `SanguoYearPriceAdjusted`（`C:/buildgame/sanguo/Game.Core/Contracts/Sanguo/EconomyEvents.cs`）

### `GameEvents.cs`
- `core.sanguo.game.ended` → `SanguoGameEnded`（`C:/buildgame/sanguo/Game.Core/Contracts/Sanguo/GameEvents.cs`）
- `core.sanguo.game.loaded` → `SanguoGameLoaded`（`C:/buildgame/sanguo/Game.Core/Contracts/Sanguo/GameEvents.cs`）
- `core.sanguo.game.saved` → `SanguoGameSaved`（`C:/buildgame/sanguo/Game.Core/Contracts/Sanguo/GameEvents.cs`）
- `core.sanguo.game.turn.advanced` → `SanguoGameTurnAdvanced`（`C:/buildgame/sanguo/Game.Core/Contracts/Sanguo/GameEvents.cs`）
- `core.sanguo.game.turn.ended` → `SanguoGameTurnEnded`（`C:/buildgame/sanguo/Game.Core/Contracts/Sanguo/GameEvents.cs`）
- `core.sanguo.game.turn.started` → `SanguoGameTurnStarted`（`C:/buildgame/sanguo/Game.Core/Contracts/Sanguo/GameEvents.cs`）

### `PlayerAndAiEvents.cs`
- `core.sanguo.ai.decision.made` → `SanguoAiDecisionMade`（`C:/buildgame/sanguo/Game.Core/Contracts/Sanguo/PlayerAndAiEvents.cs`）
- `core.sanguo.player.state.changed` → `SanguoPlayerStateChanged`（`C:/buildgame/sanguo/Game.Core/Contracts/Sanguo/PlayerAndAiEvents.cs`）

## 接口契约（Interfaces）

### 事件与游戏闭环核心
- `IEventBus`（`C:/buildgame/sanguo/Game.Core/Services/EventBus.cs`）
- `IEventData`（`C:/buildgame/sanguo/Game.Core/Contracts/IEventData.cs`）
- `IRandomNumberGenerator`（`C:/buildgame/sanguo/Game.Core/Utilities/IRandomNumberGenerator.cs`）
- `ISanguoAiDecisionPolicy`（`C:/buildgame/sanguo/Game.Core/Services/ISanguoAiDecisionPolicy.cs`）
- `ISanguoPlayerView`（`C:/buildgame/sanguo/Game.Core/Domain/ISanguoPlayerView.cs`）
- `IScoreService`（`C:/buildgame/sanguo/Game.Core/Services/IScoreService.cs`）

### Ports（Core→Adapters）
- `IAudioPlayer`（`C:/buildgame/sanguo/Game.Core/Ports/IAudioPlayer.cs`）
- `IDataStore`（`C:/buildgame/sanguo/Game.Core/Ports/IDataStore.cs`）
- `IErrorReporter`（`C:/buildgame/sanguo/Game.Core/Ports/IErrorReporter.cs`）
- `IInput`（`C:/buildgame/sanguo/Game.Core/Ports/IInput.cs`）
- `ILogger`（`C:/buildgame/sanguo/Game.Core/Ports/ILogger.cs`）
- `IResourceLoader`（`C:/buildgame/sanguo/Game.Core/Ports/IResourceLoader.cs`）
- `ISqlDatabase`（`C:/buildgame/sanguo/Game.Core/Ports/ISqlDatabase.cs`）
- `ITime`（`C:/buildgame/sanguo/Game.Core/Ports/ITime.cs`）

### Repositories（持久化抽象）
- `IAchievementRepository`（`C:/buildgame/sanguo/Game.Core/Repositories/IAchievementRepository.cs`）
- `IInventoryRepository`（`C:/buildgame/sanguo/Game.Core/Repositories/IInventoryRepository.cs`）
- `ISaveGameRepository`（`C:/buildgame/sanguo/Game.Core/Repositories/ISaveGameRepository.cs`）
- `IUserRepository`（`C:/buildgame/sanguo/Game.Core/Repositories/IUserRepository.cs`）

## 按任务映射（每个任务需要哪些事件/DTO/接口）

> 说明：`contractRefs` 只记录“本任务关心的领域事件（EventType）”，DTO/接口为基于事件集的推导，用于开发时对齐依赖。

### Task 1: 设置Godot项目
- Master(tasks.json)：status=`done`
  - ADR：`ADR-0005`, `ADR-0011`, `ADR-0018`
  - Arch：`CH01`, `CH06`, `CH07`, `CH10`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0001` layer=`infra` status=`pending`
  - 领域事件（contractRefs）：(空)
  - DTO：(空)
  - 接口：(空)
  - ADR：`ADR-0005`, `ADR-0011`, `ADR-0018`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Tests.Godot/tests/Scenes/Smoke/test_main_scene_smoke.gd`
- GM(tasks_gameplay)：`GM-0001` layer=`infra` status=`pending`
  - 领域事件（contractRefs）：(空)
  - DTO：(空)
  - 接口：(空)
  - ADR：`ADR-0005`, `ADR-0011`, `ADR-0018`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Tests.Godot/tests/Scenes/Smoke/test_main_scene_smoke.gd`

### Task 2: 创建环形地图数据结构
- Master(tasks.json)：status=`done`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Arch：`CH01`, `CH04`, `CH05`, `CH06`, `CH07`, `CH09`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0002` layer=`core` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.board.token.moved`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Domain/ValueObjects/CircularMapPositionTests.cs`
- GM(tasks_gameplay)：`GM-0002` layer=`core` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.board.token.moved`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Domain/ValueObjects/CircularMapPositionTests.cs`

### Task 3: 实现城池类
- Master(tasks.json)：status=`done`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Arch：`CH01`, `CH04`, `CH05`, `CH06`, `CH07`, `CH09`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0003` layer=`core` status=`pending`
  - 领域事件（contractRefs）：(空)
  - DTO：(空)
  - 接口：(空)
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Domain/CityTests.cs`
- GM(tasks_gameplay)：`GM-0003` layer=`core` status=`pending`
  - 领域事件（contractRefs）：(空)
  - DTO：(空)
  - 接口：(空)
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Domain/CityTests.cs`

### Task 4: 实现玩家类
- Master(tasks.json)：status=`done`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Arch：`CH01`, `CH04`, `CH05`, `CH06`, `CH07`, `CH09`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0004` layer=`core` status=`pending`
  - 领域事件（contractRefs）：(空)
  - DTO：(空)
  - 接口：(空)
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Domain/SanguoPlayerTests.cs`
- GM(tasks_gameplay)：`GM-0004` layer=`core` status=`pending`
  - 领域事件（contractRefs）：(空)
  - DTO：(空)
  - 接口：(空)
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Domain/SanguoPlayerTests.cs`

### Task 5: 实现骰子机制
- Master(tasks.json)：status=`done`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Arch：`CH01`, `CH04`, `CH05`, `CH06`, `CH07`, `CH09`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0005` layer=`core` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.dice.rolled`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`, `Game.Core.Utilities.IRandomNumberGenerator`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Services/SanguoDiceServiceTests.cs`
- GM(tasks_gameplay)：`GM-0005` layer=`core` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.dice.rolled`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`, `Game.Core.Utilities.IRandomNumberGenerator`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Services/SanguoDiceServiceTests.cs`

### Task 6: 实现回合管理器
- Master(tasks.json)：status=`done`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Arch：`CH01`, `CH04`, `CH05`, `CH06`, `CH07`, `CH09`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0006` layer=`core` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.game.turn.started`, `core.sanguo.game.turn.ended`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Services/SanguoTurnManagerTests.cs`
- GM(tasks_gameplay)：`GM-0006` layer=`core` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.game.turn.started`, `core.sanguo.game.turn.ended`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Services/SanguoTurnManagerTests.cs`

### Task 7: 实现经济结算管理器
- Master(tasks.json)：status=`done`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Arch：`CH01`, `CH04`, `CH05`, `CH06`, `CH07`, `CH09`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0007` layer=`core` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.economy.month.settled`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`, `Game.Core.Contracts.Sanguo.PlayerSettlement`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Services/SanguoEconomyManagerTests.cs`
- GM(tasks_gameplay)：`GM-0007` layer=`core` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.economy.month.settled`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`, `Game.Core.Contracts.Sanguo.PlayerSettlement`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Services/SanguoEconomyManagerTests.cs`

### Task 8: 实现事件管理器
- Master(tasks.json)：status=`done`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`, `ADR-0026`
  - Arch：`CH01`, `CH04`, `CH05`, `CH06`, `CH07`, `CH09`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0008` layer=`core` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.economy.season.event.applied`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`, `ADR-0026`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Services/EventBusTests.cs`
- GM(tasks_gameplay)：`GM-0008` layer=`core` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.economy.season.event.applied`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`, `ADR-0026`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Services/EventBusTests.cs`

### Task 9: 设计UI界面
- Master(tasks.json)：status=`done`
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0022`
  - Arch：`CH01`, `CH04`, `CH06`, `CH07`, `CH10`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0009` layer=`ui` status=`pending`
  - 领域事件（contractRefs）：(空)
  - DTO：(空)
  - 接口：(空)
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0022`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Tests.Godot/tests/UI/test_hud_scene.gd`, `Tests.Godot/tests/UI/test_hud_updates_on_events.gd`, `Game.Core.Tests/Domain/SanguoPlayerViewTests.cs`, `Game.Core.Tests/Tasks/Task9UiBoundaryTests.cs`
- GM(tasks_gameplay)：`GM-0009` layer=`ui` status=`pending`
  - 领域事件（contractRefs）：(空)
  - DTO：(空)
  - 接口：(空)
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0022`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Tests.Godot/tests/UI/test_hud_scene.gd`, `Tests.Godot/tests/UI/test_hud_updates_on_events.gd`, `Game.Core.Tests/Domain/SanguoPlayerViewTests.cs`, `Game.Core.Tests/Tasks/Task9UiBoundaryTests.cs`

### Task 10: 实现玩家棋子移动
- Master(tasks.json)：status=`done`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Arch：`CH01`, `CH04`, `CH05`, `CH06`, `CH07`, `CH09`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0010` layer=`core` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.board.token.moved`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Tests.Godot/tests/Scenes/Sanguo/test_sanguo_board_view_token_move.gd`
- GM(tasks_gameplay)：`GM-0010` layer=`core` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.board.token.moved`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Tests.Godot/tests/Scenes/Sanguo/test_sanguo_board_view_token_move.gd`

### Task 11: 实现AI行为
- Master(tasks.json)：status=`done`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Arch：`CH01`, `CH04`, `CH05`, `CH06`, `CH07`, `CH09`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0011` layer=`core` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.ai.decision.made`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Domain.ISanguoPlayerView`, `Game.Core.Services.IEventBus`, `Game.Core.Services.ISanguoAiDecisionPolicy`, `Game.Core.Utilities.IRandomNumberGenerator`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Services/SanguoAiBehaviorTests.cs`, `Game.Core.Tests/Services/SanguoAiExecutionTests.cs`, `Game.Core.Tests/Domain/SanguoPlayerViewTests.cs`
- GM(tasks_gameplay)：`GM-0011` layer=`core` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.ai.decision.made`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Domain.ISanguoPlayerView`, `Game.Core.Services.IEventBus`, `Game.Core.Services.ISanguoAiDecisionPolicy`, `Game.Core.Utilities.IRandomNumberGenerator`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Services/SanguoAiBehaviorTests.cs`, `Game.Core.Tests/Services/SanguoAiExecutionTests.cs`, `Game.Core.Tests/Domain/SanguoPlayerViewTests.cs`

### Task 12: 实现土地购买逻辑
- Master(tasks.json)：status=`done`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`, `ADR-0027`
  - Arch：`CH01`, `CH04`, `CH05`, `CH06`, `CH07`, `CH09`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0012` layer=`core` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.city.bought`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`, `ADR-0027`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Domain/SanguoPlayerTests.cs`, `Game.Core.Tests/Domain/CityTests.cs`, `Game.Core.Tests/Domain/SanguoBoardStateTests.cs`
- GM(tasks_gameplay)：`GM-0012` layer=`core` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.city.bought`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`, `ADR-0027`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Domain/SanguoPlayerTests.cs`, `Game.Core.Tests/Domain/CityTests.cs`, `Game.Core.Tests/Domain/SanguoBoardStateTests.cs`

### Task 13: 实现过路费支付逻辑
- Master(tasks.json)：status=`done`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Arch：`CH01`, `CH04`, `CH05`, `CH06`, `CH07`, `CH09`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0013` layer=`core` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.city.toll.paid`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Services/SanguoEconomyManagerTests.cs`
- GM(tasks_gameplay)：`GM-0013` layer=`core` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.city.toll.paid`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Services/SanguoEconomyManagerTests.cs`

### Task 14: 实现月末收益结算
- Master(tasks.json)：status=`done`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Arch：`CH01`, `CH04`, `CH05`, `CH06`, `CH07`, `CH09`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0014` layer=`core` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.economy.month.settled`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`, `Game.Core.Contracts.Sanguo.PlayerSettlement`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Tasks/Task14MonthEndSettlementTests.cs`
- GM(tasks_gameplay)：`GM-0014` layer=`core` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.economy.month.settled`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`, `Game.Core.Contracts.Sanguo.PlayerSettlement`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Tasks/Task14MonthEndSettlementTests.cs`

### Task 15: 实现季度环境事件
- Master(tasks.json)：status=`pending`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Arch：`CH01`, `CH04`, `CH05`, `CH06`, `CH07`, `CH09`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0015` layer=`core` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.economy.season.event.applied`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Tasks/Task15QuarterEventTests.cs`, `Game.Core.Tests/Services/QuarterlyEnvironmentEventTests.cs`
- GM(tasks_gameplay)：`GM-0015` layer=`core` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.economy.season.event.applied`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Tasks/Task15QuarterEventTests.cs`, `Game.Core.Tests/Services/QuarterlyEnvironmentEventTests.cs`

### Task 16: 实现年度地价调整
- Master(tasks.json)：status=`pending`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Arch：`CH01`, `CH04`, `CH05`, `CH06`, `CH07`, `CH09`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0016` layer=`core` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.economy.year.price.adjusted`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Tasks/Task16YearEndPriceTests.cs`, `Game.Core.Tests/Domain/MoneyTests.cs`
- GM(tasks_gameplay)：`GM-0016` layer=`core` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.economy.year.price.adjusted`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Tasks/Task16YearEndPriceTests.cs`, `Game.Core.Tests/Domain/MoneyTests.cs`

### Task 17: 实现回合循环
- Master(tasks.json)：status=`pending`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Arch：`CH01`, `CH04`, `CH05`, `CH06`, `CH07`, `CH09`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0017` layer=`core` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.game.turn.advanced`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Tasks/Task17TurnTests.cs`, `Game.Core.Tests/Domain/MoneyTests.cs`, `Game.Core.Tests/Domain/SanguoBoardStateTests.cs`
- GM(tasks_gameplay)：`GM-0017` layer=`core` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.game.turn.advanced`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Tasks/Task17TurnTests.cs`, `Game.Core.Tests/Domain/MoneyTests.cs`, `Game.Core.Tests/Domain/SanguoBoardStateTests.cs`

### Task 18: 实现存档功能
- Master(tasks.json)：status=`deferred`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Arch：`CH01`, `CH04`, `CH05`, `CH06`, `CH07`, `CH09`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0018` layer=`core` status=`deferred`
  - 领域事件（contractRefs）：`core.sanguo.game.saved`, `core.sanguo.game.loaded`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Tasks/Task18RequirementsTests.cs`, `Game.Core.Tests/Tasks/Task18CoreAssemblyDependencyRulesTests.cs`, `Game.Core.Tests/Utilities/SecureSavePathPolicyTests.cs`, `Game.Core.Tests/Services/SanguoSaveLoadServiceTests.cs`, `Game.Core.Tests/Domain/SanguoSaveLoadEventsTests.cs`
- GM(tasks_gameplay)：`GM-0018` layer=`core` status=`deferred`
  - 领域事件（contractRefs）：`core.sanguo.game.saved`, `core.sanguo.game.loaded`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Tasks/Task18RequirementsTests.cs`, `Game.Core.Tests/Tasks/Task18CoreAssemblyDependencyRulesTests.cs`, `Game.Core.Tests/Utilities/SecureSavePathPolicyTests.cs`, `Game.Core.Tests/Services/SanguoSaveLoadServiceTests.cs`, `Game.Core.Tests/Domain/SanguoSaveLoadEventsTests.cs`

### Task 19: 实现UI事件提示
- Master(tasks.json)：status=`pending`
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0022`
  - Arch：`CH01`, `CH04`, `CH06`, `CH07`, `CH10`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0019` layer=`ui` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.board.token.moved`, `core.sanguo.city.bought`, `core.sanguo.city.toll.paid`, `core.sanguo.economy.month.settled`, `core.sanguo.economy.season.event.applied`, `core.sanguo.game.ended`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`, `Game.Core.Contracts.Sanguo.PlayerSettlement`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0022`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Tests.Godot/tests/Scenes/Sanguo/test_sanguo_event_task19.gd`, `Tests.Godot/tests/UI/test_hud_scene.gd`, `Tests.Godot/tests/UI/test_hud_updates_on_events.gd`
- GM(tasks_gameplay)：`GM-0019` layer=`ui` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.board.token.moved`, `core.sanguo.city.bought`, `core.sanguo.city.toll.paid`, `core.sanguo.economy.month.settled`, `core.sanguo.economy.season.event.applied`, `core.sanguo.game.ended`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`, `Game.Core.Contracts.Sanguo.PlayerSettlement`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0022`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Tests.Godot/tests/Scenes/Sanguo/test_sanguo_event_task19.gd`, `Tests.Godot/tests/UI/test_hud_scene.gd`, `Tests.Godot/tests/UI/test_hud_updates_on_events.gd`

### Task 20: 实现UI资金显示
- Master(tasks.json)：status=`pending`
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0022`
  - Arch：`CH01`, `CH04`, `CH06`, `CH07`, `CH10`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0020` layer=`ui` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.player.state.changed`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0022`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Tests.Godot/tests/Scenes/Sanguo/test_sanguo_ui_task20.gd`, `Tests.Godot/tests/UI/test_hud_scene.gd`, `Tests.Godot/tests/UI/test_hud_updates_on_events.gd`
- GM(tasks_gameplay)：`GM-0020` layer=`ui` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.player.state.changed`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0022`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Tests.Godot/tests/Scenes/Sanguo/test_sanguo_ui_task20.gd`, `Tests.Godot/tests/UI/test_hud_scene.gd`, `Tests.Godot/tests/UI/test_hud_updates_on_events.gd`

### Task 21: 实现UI日期显示
- Master(tasks.json)：status=`pending`
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0022`
  - Arch：`CH01`, `CH04`, `CH06`, `CH07`, `CH10`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0021` layer=`ui` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.game.turn.advanced`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0022`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Tests.Godot/tests/Scenes/Sanguo/test_sanguo_ui_task21.gd`, `Tests.Godot/tests/UI/test_hud_scene.gd`, `Tests.Godot/tests/UI/A11y/test_button_invokable.gd`, `Tests.Godot/tests/UI/test_hud_updates_on_events.gd`, `Tests.Godot/tests/UI/test_hud_date_display_reflects_latest_date.gd`
- GM(tasks_gameplay)：`GM-0021` layer=`ui` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.game.turn.advanced`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0022`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Tests.Godot/tests/Scenes/Sanguo/test_sanguo_ui_task21.gd`, `Tests.Godot/tests/UI/test_hud_scene.gd`, `Tests.Godot/tests/UI/A11y/test_button_invokable.gd`, `Tests.Godot/tests/UI/test_hud_updates_on_events.gd`, `Tests.Godot/tests/UI/test_hud_date_display_reflects_latest_date.gd`

### Task 22: 实现UI骰子结果显示
- Master(tasks.json)：status=`done`
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0022`
  - Arch：`CH01`, `CH04`, `CH06`, `CH07`, `CH10`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0022` layer=`ui` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.dice.rolled`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`, `Game.Core.Utilities.IRandomNumberGenerator`
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0022`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Tests.Godot/tests/UI/test_hud_scene.gd`, `Tests.Godot/tests/UI/test_hud_updates_on_events.gd`
- GM(tasks_gameplay)：`GM-0022` layer=`ui` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.dice.rolled`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`, `Game.Core.Utilities.IRandomNumberGenerator`
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0022`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Tests.Godot/tests/UI/test_hud_scene.gd`, `Tests.Godot/tests/UI/test_hud_updates_on_events.gd`

### Task 23: 实现UI城池状态显示
- Master(tasks.json)：status=`pending`
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0022`
  - Arch：`CH01`, `CH04`, `CH06`, `CH07`, `CH10`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0023` layer=`ui` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.city.bought`, `core.sanguo.city.toll.paid`, `core.sanguo.economy.season.event.applied`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0022`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Tests.Godot/tests/Scenes/Sanguo/test_sanguo_city_task23.gd`, `Tests.Godot/tests/UI/A11y/test_button_invokable.gd`, `Tests.Godot/tests/Scenes/Sanguo/test_sanguo_city_ownership_status_display.gd`
- GM(tasks_gameplay)：`GM-0023` layer=`ui` status=`pending`
  - 领域事件（contractRefs）：`core.sanguo.city.bought`, `core.sanguo.city.toll.paid`, `core.sanguo.economy.season.event.applied`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0022`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Tests.Godot/tests/Scenes/Sanguo/test_sanguo_city_task23.gd`, `Tests.Godot/tests/UI/A11y/test_button_invokable.gd`, `Tests.Godot/tests/Scenes/Sanguo/test_sanguo_city_ownership_status_display.gd`

### Task 24: 实现UI事件日志
- Master(tasks.json)：status=`deferred`
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0022`
  - Arch：`CH01`, `CH04`, `CH06`, `CH07`, `CH10`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0024` layer=`ui` status=`deferred`
  - 领域事件（contractRefs）：`core.sanguo.board.token.moved`, `core.sanguo.city.bought`, `core.sanguo.city.toll.paid`, `core.sanguo.economy.month.settled`, `core.sanguo.economy.season.event.applied`, `core.sanguo.economy.year.price.adjusted`, `core.sanguo.game.ended`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`, `Game.Core.Contracts.Sanguo.PlayerSettlement`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0022`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Tests.Godot/tests/Scenes/Sanguo/test_sanguo_eventlogging_task24.gd`, `Tests.Godot/tests/UI/test_hud_scene.gd`, `Tests.Godot/tests/UI/test_hud_updates_on_events.gd`, `Tests.Godot/tests/UI/A11y/test_button_invokable.gd`
- GM(tasks_gameplay)：`GM-0024` layer=`ui` status=`deferred`
  - 领域事件（contractRefs）：`core.sanguo.board.token.moved`, `core.sanguo.city.bought`, `core.sanguo.city.toll.paid`, `core.sanguo.economy.month.settled`, `core.sanguo.economy.season.event.applied`, `core.sanguo.economy.year.price.adjusted`, `core.sanguo.game.ended`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`, `Game.Core.Contracts.Sanguo.PlayerSettlement`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0022`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Tests.Godot/tests/Scenes/Sanguo/test_sanguo_eventlogging_task24.gd`, `Tests.Godot/tests/UI/test_hud_scene.gd`, `Tests.Godot/tests/UI/test_hud_updates_on_events.gd`, `Tests.Godot/tests/UI/A11y/test_button_invokable.gd`

### Task 25: 实现AI策略优化
- Master(tasks.json)：status=`deferred`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Arch：`CH01`, `CH04`, `CH05`, `CH06`, `CH07`, `CH09`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0025` layer=`core` status=`deferred`
  - 领域事件（contractRefs）：`core.sanguo.ai.decision.made`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Domain.ISanguoPlayerView`, `Game.Core.Services.IEventBus`, `Game.Core.Services.ISanguoAiDecisionPolicy`, `Game.Core.Utilities.IRandomNumberGenerator`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Tasks/Task25AiTests.cs`
- GM(tasks_gameplay)：缺失

### Task 26: 实现游戏结束条件
- Master(tasks.json)：status=`deferred`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Arch：`CH01`, `CH04`, `CH05`, `CH06`, `CH07`, `CH09`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0026` layer=`core` status=`deferred`
  - 领域事件（contractRefs）：`core.sanguo.game.ended`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0020`, `ADR-0021`, `ADR-0024`, `ADR-0025`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Tasks/Task26RequirementsTests.cs`, `Game.Core.Tests/Utilities/NoGodotDependencyTests.cs`, `Game.Core.Tests/Services/PlayerEliminationTests.cs`
- GM(tasks_gameplay)：缺失

### Task 27: 实现音效和音乐
- Master(tasks.json)：status=`deferred`
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0022`
  - Arch：`CH01`, `CH04`, `CH06`, `CH07`, `CH10`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0027` layer=`ui` status=`deferred`
  - 领域事件（contractRefs）：(空)
  - DTO：(空)
  - 接口：(空)
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0022`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Tests.Godot/tests/Adapters/test_audio_player_adapter_nodes.gd`, `Tests.Godot/tests/UI/test_settings_panel_applies_audio_volume.gd`, `Tests.Godot/tests/UI/test_settings_panel_logic.gd`, `Tests.Godot/tests/Scenes/Sanguo/test_sanguo_main_music_autoplays.gd`, `Tests.Godot/tests/UI/test_hud_plays_sfx_on_action.gd`, `Tests.Godot/tests/UI/test_hud_sfx_does_not_stop_music.gd`
- GM(tasks_gameplay)：缺失

### Task 28: 实现游戏主菜单
- Master(tasks.json)：status=`deferred`
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0022`
  - Arch：`CH01`, `CH04`, `CH06`, `CH07`, `CH10`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0028` layer=`ui` status=`deferred`
  - 领域事件（contractRefs）：(空)
  - DTO：(空)
  - 接口：(空)
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0022`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Tests.Godot/tests/UI/test_main_menu_scene.gd`, `Tests.Godot/tests/UI/test_main_menu_events.gd`, `Tests.Godot/tests/UI/test_main_menu_settings_button.gd`, `Tests.Godot/tests/UI/test_main_menu_load_play_quit_routing.gd`
- GM(tasks_gameplay)：缺失

### Task 29: 实现游戏设置菜单
- Master(tasks.json)：status=`deferred`
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0022`
  - Arch：`CH01`, `CH04`, `CH06`, `CH07`, `CH10`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0029` layer=`ui` status=`deferred`
  - 领域事件（contractRefs）：(空)
  - DTO：(空)
  - 接口：(空)
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0022`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Tests.Godot/tests/UI/test_settings_panel_scene.gd`, `Tests.Godot/tests/UI/test_settings_panel_logic.gd`, `Tests.Godot/tests/UI/test_settings_panel_closepanel.gd`, `Tests.Godot/tests/UI/test_settings_panel_applies_audio_volume.gd`, `Tests.Godot/tests/UI/test_settings_panel_applies_window_resolution.gd`, `Tests.Godot/tests/UI/test_settings_panel_invalid_resolution_fallback.gd`, `Tests.Godot/tests/UI/test_settings_panel_invalid_volume_clamped.gd`
- GM(tasks_gameplay)：缺失

### Task 30: 实现游戏帮助和教程
- Master(tasks.json)：status=`deferred`
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0022`
  - Arch：`CH01`, `CH04`, `CH06`, `CH07`, `CH10`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0030` layer=`ui` status=`deferred`
  - 领域事件（contractRefs）：`core.sanguo.dice.rolled`, `core.sanguo.board.token.moved`, `core.sanguo.city.bought`, `core.sanguo.city.toll.paid`, `core.sanguo.economy.month.settled`, `core.sanguo.economy.season.event.applied`, `core.sanguo.economy.year.price.adjusted`, `core.sanguo.game.turn.advanced`, `core.sanguo.game.ended`
  - DTO：`Game.Core.Contracts.IEventData`, `Game.Core.Contracts.JsonElementEventData`, `Game.Core.Contracts.RawJsonEventData`, `Game.Core.Contracts.Sanguo.PlayerSettlement`
  - 接口：`Game.Core.Contracts.DomainEvent`, `Game.Core.Services.IEventBus`, `Game.Core.Utilities.IRandomNumberGenerator`
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0022`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Tests.Godot/tests/Scenes/Sanguo/test_sanguo_ui_task30.gd`, `Tests.Godot/tests/Scenes/Sanguo/test_sanguo_help_ui_loads_headless.gd`, `Tests.Godot/tests/UI/test_help_tutorial_basic_interactions.gd`, `Tests.Godot/tests/UI/test_help_tutorial_uses_project_theme.gd`, `Tests.Godot/tests/Integration/test_help_tutorial_localized_content_non_empty.gd`, `Tests.Godot/tests/UI/test_help_tutorial_toggle_and_navigation.gd`, `Tests.Godot/tests/Integration/test_help_feedback_persists_to_user_storage.gd`
- GM(tasks_gameplay)：缺失

### Task 31: 在 Game.Core 落地性能追踪库并接入 CI 性能门禁
- Master(tasks.json)：status=`deferred`
  - ADR：`ADR-0015`, `ADR-0005`, `ADR-0018`
  - Arch：`CH01`, `CH06`, `CH07`, `CH09`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
- SG(tasks_back)：`SG-0031` layer=`core` status=`deferred`
  - 领域事件（contractRefs）：(空)
  - DTO：(空)
  - 接口：(空)
  - ADR：`ADR-0015`, `ADR-0005`, `ADR-0018`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
  - Test-Refs：`Game.Core.Tests/Tasks/Task31PerformanceGateTests.cs`
- GM(tasks_gameplay)：缺失

### Task 32: Observability Autoload 与 Sentry Release Health Gate
- Master(tasks.json)：status=`deferred`
  - ADR：`ADR-0003`, `ADR-0005`, `ADR-0015`, `ADR-0018`
  - Arch：`CH01`, `CH03`, `CH06`, `CH07`, `CH09`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
- SG(tasks_back)：`SG-0032` layer=`adapter` status=`deferred`
  - 领域事件（contractRefs）：(空)
  - DTO：(空)
  - 接口：(空)
  - ADR：`ADR-0003`, `ADR-0005`, `ADR-0015`, `ADR-0018`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
  - Test-Refs：`Game.Core.Tests/Tasks/Task32RequirementsTests.cs`, `Tests.Godot/tests/Adapters/Db/test_db_handle_release.gd`, `Game.Core.Tests/Domain/ValueObjects/HealthTests.cs`
- GM(tasks_gameplay)：缺失

### Task 33: Python 构建驱动脚本与 Windows Release Workflow 整合
- Master(tasks.json)：status=`deferred`
  - ADR：`ADR-0008`, `ADR-0011`, `ADR-0003`, `ADR-0015`
  - Arch：`CH03`, `CH07`, `CH09`, `CH10`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
- SG(tasks_back)：`SG-0033` layer=`ci` status=`deferred`
  - 领域事件（contractRefs）：(空)
  - DTO：(空)
  - 接口：(空)
  - ADR：`ADR-0008`, `ADR-0011`, `ADR-0003`, `ADR-0015`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
  - Test-Refs：`Tests.Godot/tests/Scenes/Sanguo/test_sanguo_requirements_task33.gd`, `Game.Core.Tests/Tasks/Task33RequirementsTests.cs`, `Game.Core.Tests/Tasks/Task33WindowsReleaseWorkflowTests.cs`, `Game.Core.Tests/Tasks/Task33BuildMetadataDocsTests.cs`, `Game.Core.Tests/Tasks/Task33SmokeExeValidationTests.cs`, `Game.Core.Tests/Tasks/Task33MigrationDocsPresenceTests.cs`, `Game.Core.Tests/Tasks/Task33WindowsBuildArtifactsTests.cs`, `Game.Core.Tests/Tasks/Task33BuildWindowsCliContractTests.cs`
- GM(tasks_gameplay)：缺失

### Task 34: 分阶段发布（Canary/Stable）与回滚脚本骨架
- Master(tasks.json)：status=`deferred`
  - ADR：`ADR-0003`, `ADR-0005`, `ADR-0015`
  - Arch：`CH03`, `CH07`, `CH09`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
- SG(tasks_back)：`SG-0034` layer=`ci` status=`deferred`
  - 领域事件（contractRefs）：(空)
  - DTO：(空)
  - 接口：(空)
  - ADR：`ADR-0003`, `ADR-0005`, `ADR-0015`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
  - Test-Refs：`Game.Core.Tests/Tasks/Task34RequirementsTests.cs`, `Game.Core.Tests/Domain/ValueObjects/HealthTests.cs`, `Game.Core.Tests/Tasks/Task34StagedReleaseTests.cs`, `Game.Core.Tests/Tasks/Task34RollbackTests.cs`
- GM(tasks_gameplay)：缺失

### Task 35: 项目级功能验收与文档整合骨架
- Master(tasks.json)：status=`deferred`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0003`
  - Arch：`CH03`, `CH07`, `CH09`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
- SG(tasks_back)：`SG-0035` layer=`docs` status=`deferred`
  - 领域事件（contractRefs）：(空)
  - DTO：(空)
  - 接口：(空)
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0003`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
  - Test-Refs：`Game.Core.Tests/Tasks/Task35RequirementsTests.cs`, `Game.Core.Tests/Tasks/Task35ProjectDocumentationTemplatesTests.cs`, `Game.Core.Tests/Tasks/Task35ProjectDocumentationIndexGuidanceTests.cs`, `Game.Core.Tests/Tasks/Task35TemplateNeutralityGuardTests.cs`, `Game.Core.Tests/Tasks/Task35MigrationDocsReferenceCoverageTests.cs`, `Game.Core.Tests/Tasks/Task35PerformanceBaselineTemplateTests.cs`
- GM(tasks_gameplay)：缺失

### Task 36: 事件命名统一迁移（game.* → core.*.*）
- Master(tasks.json)：status=`deferred`
  - ADR：`ADR-0004`, `ADR-0006`, `ADR-0018`, `ADR-0023`
  - Arch：`CH01`, `CH04`, `CH05`, `CH06`, `CH07`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
- SG(tasks_back)：`SG-0036` layer=`core` status=`deferred`
  - 领域事件（contractRefs）：(空)
  - DTO：(空)
  - 接口：(空)
  - ADR：`ADR-0004`, `ADR-0006`, `ADR-0018`, `ADR-0023`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-feature-slice-t2-monopoly-loop.md`
  - Test-Refs：`Game.Core.Tests/Tasks/Task36EventTests.cs`, `Tests.Godot/tests/Scenes/Sanguo/test_sanguo_event_task36.gd`, `Game.Core.Tests/Domain/CityTests.cs`
- GM(tasks_gameplay)：缺失

### Task 37: Game.Core Observability 客户端与结构化日志
- Master(tasks.json)：status=`deferred`
  - ADR：`ADR-0003`, `ADR-0005`, `ADR-0015`, `ADR-0018`
  - Arch：`CH01`, `CH03`, `CH06`, `CH07`, `CH09`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
- SG(tasks_back)：`SG-0037` layer=`core` status=`deferred`
  - 领域事件（contractRefs）：(空)
  - DTO：(空)
  - 接口：(空)
  - ADR：`ADR-0003`, `ADR-0005`, `ADR-0015`, `ADR-0018`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
  - Test-Refs：`Game.Core.Tests/Tasks/Task37LoggingTests.cs`, `Game.Core.Tests/Domain/CityTests.cs`
- GM(tasks_gameplay)：缺失

### Task 38: 代码重复率与圈复杂度门禁
- Master(tasks.json)：status=`deferred`
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0024`
  - Arch：`CH01`, `CH06`, `CH07`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
- SG(tasks_back)：`SG-0038` layer=`ci` status=`deferred`
  - 领域事件（contractRefs）：(空)
  - DTO：(空)
  - 接口：(空)
  - ADR：`ADR-0005`, `ADR-0018`, `ADR-0024`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
  - Test-Refs：`Game.Core.Tests/Tasks/Task38GateTests.cs`
- GM(tasks_gameplay)：缺失

### Task 39: 性能 P95 与审计 JSONL 校验
- Master(tasks.json)：status=`deferred`
  - ADR：`ADR-0015`, `ADR-0005`, `ADR-0019`, `ADR-0018`
  - Arch：`CH01`, `CH02`, `CH06`, `CH07`, `CH09`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
- SG(tasks_back)：`SG-0039` layer=`ci` status=`deferred`
  - 领域事件（contractRefs）：(空)
  - DTO：(空)
  - 接口：(空)
  - ADR：`ADR-0015`, `ADR-0005`, `ADR-0019`, `ADR-0018`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
  - Test-Refs：`Game.Core.Tests/Tasks/Task39AuditPerformanceTests.cs`
- GM(tasks_gameplay)：缺失

### Task 40: Signal 健康度验证与安全相关测试门禁
- Master(tasks.json)：status=`deferred`
  - ADR：`ADR-0019`, `ADR-0004`, `ADR-0005`, `ADR-0018`
  - Arch：`CH01`, `CH02`, `CH04`, `CH06`, `CH07`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
- SG(tasks_back)：`SG-0040` layer=`adapter` status=`deferred`
  - 领域事件（contractRefs）：(空)
  - DTO：(空)
  - 接口：(空)
  - ADR：`ADR-0019`, `ADR-0004`, `ADR-0005`, `ADR-0018`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
  - Test-Refs：`Tests.Godot/tests/Scenes/Sanguo/test_sanguo_securitygate_task40.gd`, `Game.Core.Tests/Tasks/Task40SecurityGateTests.cs`, `Game.Core.Tests/Tasks/Task40SignalHealthGateTests.cs`, `Tests.Godot/tests/Integration/Security/test_security_http_block_signal.gd`
- GM(tasks_gameplay)：缺失

### Task 41: 性能报告与历史追踪（reports/performance/**）
- Master(tasks.json)：status=`deferred`
  - ADR：`ADR-0015`, `ADR-0005`, `ADR-0018`
  - Arch：`CH01`, `CH06`, `CH07`, `CH09`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
- SG(tasks_back)：`SG-0041` layer=`ci` status=`deferred`
  - 领域事件（contractRefs）：(空)
  - DTO：(空)
  - 接口：(空)
  - ADR：`ADR-0015`, `ADR-0005`, `ADR-0018`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
  - Test-Refs：`Game.Core.Tests/Tasks/Task41PerformanceTests.cs`
- GM(tasks_gameplay)：缺失

### Task 42: 独立性能门禁 CI 工作流（performance-gates.yml）
- Master(tasks.json)：status=`deferred`
  - ADR：`ADR-0015`, `ADR-0005`, `ADR-0011`, `ADR-0008`, `ADR-0018`
  - Arch：`CH01`, `CH06`, `CH07`, `CH09`, `CH10`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
- SG(tasks_back)：`SG-0042` layer=`ci` status=`deferred`
  - 领域事件（contractRefs）：(空)
  - DTO：(空)
  - 接口：(空)
  - ADR：`ADR-0015`, `ADR-0005`, `ADR-0011`, `ADR-0008`, `ADR-0018`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
  - Test-Refs：`Game.Core.Tests/Tasks/Task42PerformanceGateTests.cs`
- GM(tasks_gameplay)：缺失

### Task 43: 代码签名与安全分发
- Master(tasks.json)：status=`deferred`
  - ADR：`ADR-0008`, `ADR-0011`, `ADR-0019`, `ADR-0005`, `ADR-0018`
  - Arch：`CH01`, `CH02`, `CH06`, `CH07`, `CH10`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
- SG(tasks_back)：`SG-0043` layer=`ci` status=`deferred`
  - 领域事件（contractRefs）：(空)
  - DTO：(空)
  - 接口：(空)
  - ADR：`ADR-0008`, `ADR-0011`, `ADR-0019`, `ADR-0005`, `ADR-0018`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
  - Test-Refs：`Game.Core.Tests/Tasks/Task43SecurityTests.cs`, `Game.Core.Tests/Tasks/Task43CodeSigningPipelineTests.cs`, `Game.Core.Tests/Tasks/Task43CodeSigningAuditTrailTests.cs`
- GM(tasks_gameplay)：缺失

### Task 44: 导出预设与多配置支持
- Master(tasks.json)：status=`deferred`
  - ADR：`ADR-0011`, `ADR-0018`, `ADR-0005`
  - Arch：`CH01`, `CH06`, `CH07`, `CH10`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
- SG(tasks_back)：`SG-0044` layer=`adapter` status=`deferred`
  - 领域事件（contractRefs）：(空)
  - DTO：(空)
  - 接口：(空)
  - ADR：`ADR-0011`, `ADR-0018`, `ADR-0005`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
  - Test-Refs：`Game.Core.Tests/Tasks/Task44RequirementsTests.cs`, `Game.Core.Tests/Tasks/Task44ExportPresetsTests.cs`, `Game.Core.Tests/Tasks/Task44BuildScriptPresetSelectionTests.cs`, `Game.Core.Tests/Tasks/Task44CiExportReleaseJobTests.cs`, `Game.Core.Tests/Tasks/Task44ExportDocsReferencesTests.cs`
- GM(tasks_gameplay)：缺失

### Task 45: 架构依赖护栏与依赖图校验骨架
- Master(tasks.json)：status=`deferred`
  - ADR：`ADR-0007`, `ADR-0005`, `ADR-0018`
  - Arch：`CH01`, `CH05`, `CH06`, `CH07`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
- SG(tasks_back)：`SG-0045` layer=`ci` status=`deferred`
  - 领域事件（contractRefs）：(空)
  - DTO：(空)
  - 接口：(空)
  - ADR：`ADR-0007`, `ADR-0005`, `ADR-0018`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
  - Test-Refs：`Game.Core.Tests/Tasks/Task45RequirementsTests.cs`, `Game.Core.Tests/Tasks/Task45DependencyGuardTests.cs`, `Game.Core.Tests/Tasks/Task45DependencyGuardGateModeTests.cs`, `Game.Core.Tests/Tasks/Task45DependencyGuardOutputArtifactsTests.cs`
- GM(tasks_gameplay)：缺失

### Task 46: Python 版 headless smoke 封装与 strict 模式开关
- Master(tasks.json)：status=`deferred`
  - ADR：`ADR-0005`, `ADR-0011`, `ADR-0018`, `ADR-0024`
  - Arch：`CH01`, `CH06`, `CH07`, `CH10`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
- SG(tasks_back)：`SG-0046` layer=`ci` status=`deferred`
  - 领域事件（contractRefs）：(空)
  - DTO：(空)
  - 接口：(空)
  - ADR：`ADR-0005`, `ADR-0011`, `ADR-0018`, `ADR-0024`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
  - Test-Refs：`Tests.Godot/tests/Scenes/Sanguo/test_sanguo_requirements_task46.gd`, `Game.Core.Tests/Tasks/Task46RequirementsTests.cs`, `Game.Core.Tests/Tasks/Task46HeadlessSmokeNonStrictTests.cs`, `Game.Core.Tests/Tasks/Task46HeadlessSmokeStrictModeTests.cs`, `Game.Core.Tests/Tasks/Task46HeadlessSmokeCiExampleTests.cs`, `Game.Core.Tests/Tasks/Task46HeadlessSmokeScriptTests.cs`
- GM(tasks_gameplay)：缺失

### Task 47: 扩展 quality_gates.py 覆盖率阈值与 GdUnit4 集成
- Master(tasks.json)：status=`deferred`
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0024`
  - Arch：`CH01`, `CH06`, `CH07`, `CH09`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
- SG(tasks_back)：`SG-0047` layer=`ci` status=`deferred`
  - 领域事件（contractRefs）：(空)
  - DTO：(空)
  - 接口：(空)
  - ADR：`ADR-0005`, `ADR-0015`, `ADR-0018`, `ADR-0024`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
  - Test-Refs：`Game.Core.Tests/Tasks/Task47QualityGatesCoverageSummaryTests.cs`, `Game.Core.Tests/Tasks/Task47QualityGatesGdUnitAggregationTests.cs`, `Tests.Godot/tests/Integration/test_quality_gates_gdunit_adapters_security_aggregation.gd`, `Tests.Godot/tests/Scenes/Smoke/test_main_scene_smoke.gd`, `Game.Core.Tests/Tasks/Task47QualityGatesDocumentationRefsTests.cs`
- GM(tasks_gameplay)：缺失

### Task 48: Godot 安全适配层增强：外链白名单、文件访问与 OS.execute 守卫
- Master(tasks.json)：status=`deferred`
  - ADR：`ADR-0019`, `ADR-0006`, `ADR-0005`, `ADR-0011`
  - Arch：`CH02`, `CH05`, `CH07`, `CH10`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
- SG(tasks_back)：`SG-0048` layer=`adapter` status=`deferred`
  - 领域事件（contractRefs）：(空)
  - DTO：(空)
  - 接口：(空)
  - ADR：`ADR-0019`, `ADR-0006`, `ADR-0005`, `ADR-0011`
  - Overlay：`docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
  - Test-Refs：`Game.Core.Tests/Tasks/Task48SecurityTests.cs`
- GM(tasks_gameplay)：缺失

## contractRefs 现状检查与优化建议

- tasks_back：48 个任务，contractRefs 非空 23 个
- tasks_gameplay：24 个任务，contractRefs 非空 20 个

### 需要人工复核的疑点（启发式）
- Task 36 SG-0036: event-related task has empty contractRefs; verify missing domain events.

### 建议口径（建议固化到工作流，而不是靠记忆）
- `contractRefs` 只允许填 EventType（例如 `core.sanguo.*`），不要混入类名/文件名。
- 优先从 `acceptance[].Refs:` 与 `test_refs` 的实际测试断言中反推该任务关心的事件集合，避免语义漂移。
- 对 UI 任务：`contractRefs` 应覆盖 UI 订阅的事件（日志/提示/状态刷新），并与 GdUnit4 用例保持一致。
