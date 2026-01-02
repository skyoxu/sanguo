---
PRD-ID: PRD-SANGUO-T2
Title: 08-功能纵切-T2-三国大富翁闭环
Arch-Refs:
  - CH01
  - CH03
---

# 08-功能纵切-T2-三国大富翁闭环

## 8.1 范围与上下文

- 目标：实现基于三国地理的“大富翁”式 T2 最小可玩闭环。  
- PRD 来源：`.taskmaster/docs/prd.txt` 中 T2 阶段「最小可玩闭环」PRD。  
- 关联 ADR：  
  - ADR-0018：Godot+C# 技术栈与运行时承载  
  - ADR-0005：质量门禁与测试覆盖口径  
  - ADR-0006：数据存储（SQLite 与存档策略）  
  - ADR-0015：性能预算与门禁  
  - ADR-0024：Sanguo 模板系谱与继承边界  
- 关联章节：CH01（目标与范围）、CH04（系统上下文与事件流）、CH05（数据模型与存储端口）、CH06（运行时视图与循环）、CH09（性能与容量）。

本纵切面只描述「功能闭环」与任务映射，不在此处重复任何阈值或策略细节；安全、可观测性与质量门禁仍以 CH02/CH03 与相关 ADR 为单一事实来源。

## 8.2 实体与事件（引用型）

实体层次（引用 PRD 与 Game.Core 设计）：
- 棋盘（Board）：承载所有城池位置与环形路线索引。  
- 城池（City）：包含名称、所属州郡、基础价格、基础过路费、基础收益系数。  
- 玩家（Player）：包含资金、当前位置索引、已拥有城池列表。  
- 回合（Turn）：描述当前行动玩家与当前日期（年/月/日）。  
- 经济环境（EconomyContext）：记录当前季度事件与年度地价系数。  

事件命名遵循 `${DOMAIN_PREFIX}.<entity>.<action>` 规则，仅在此引用，不在本文中定义具体契约载体；契约 SSoT 落盘到 `Game.Core/Contracts/Sanguo/**`。示例（非完整列表）：

- `core.board.token.moved` —— 玩家或 AI 的棋子在棋盘上移动到新位置。  
- `core.city.bought` —— 玩家购买城池成功，所有权发生变更。  
- `core.city.toll.paid` —— 玩家在他人城池停留并支付过路费。  
- `core.economy.month.settled` —— 月末结算完成，所有玩家资金按城池收益更新。  
- `core.economy.season.event.applied` —— 季度环境事件应用到一组城池或区域。  
- `core.economy.year.price.adjusted` —— 年度地价调整应用到所有城池。  
- `core.game.turn.advanced` —— 回合结束并推进到下一玩家/下一日期节点。  

具体字段与约束必须在 Contracts 层定义，并由 CH05/ADR-0006/ADR-0018 统一约束。

## 8.3 Taskmaster 任务映射

本纵切面与 Taskmaster 任务的关系如下（仅列出 T2 核心闭环相关任务）：

- 框架与棋盘
  - Task 1：设置 Godot 项目（Game.Godot 基础工程与 C# 支持）。  
  - Task 2：创建环形地图数据结构（Board / 城池索引）。  
  - Task 3：实现城池类（City 实体与价格/收益字段）。  
  - Task 4：实现玩家类（Player 状态与资产）。  
  - Task 5：实现骰子机制（随机步数，引用 ADR-0005 的随机性与可测试性口径）。  

- 回合与时间轴
  - Task 6：实现回合管理器（TurnManager，管理当前玩家与日期）。  
  - Task 16：实现年度地价调整（Year 调整经济环境）。  
  - Task 17：实现回合循环（Game Loop：玩家/AI 轮流行动→推进日/月/季/年）。  

- 经济与事件
  - Task 7：实现经济结算管理器（月末收益结算）。  
  - Task 8：实现季度环境事件（季节性收益修正）。  
  - Task 12：实现土地购买逻辑（City 所有权转移）。  
  - Task 13：实现过路费支付逻辑（Toll 计算与资金转移）。  
  - Task 14：实现月末收益结算（与 Task 7 协同覆盖 PRD 中的月度结算）。  
  - Task 15：实现季度环境事件（与 Task 8 协同覆盖季度事件）。  

- UI 与可见性（核心 HUD）
  - Task 9：设计 UI 界面（棋盘 HUD、资金、日期、事件提示等）。  
  - Task 19：实现 UI 事件提示。  
  - Task 20：实现 UI 资金显示。  
  - Task 21：实现 UI 日期显示。  
  - Task 22：实现 UI 骰子结果显示。  
  - Task 23：实现 UI 城池状态显示。  
  - Task 24：实现 UI 事件日志。  

- AI 与结束条件
  - Task 11：实现 AI 行为（简单贪心策略，预留状态机接口）。  
  - Task 25：实现 AI 策略优化（后续优化与复杂策略试验）。  
  - Task 26：实现游戏结束条件（如破产、回合数上限、累计资产目标等）。  

这些任务共同构成 T2 阶段「掷骰子 → 移动 → 买地/付费 → 月末结算 → 季度事件 → 年度地价 → 回合推进」的完整功能闭环。

## 8.4 测试与验收（引用型）

测试策略遵循 `docs/testing-framework.md` 与 ADR-0005/ADR-0020 口径，不在本节重复阈值与具体门禁，仅给出引用与占位：

- 核心逻辑（Game.Core，xUnit）  
  - GameLoop 与时间轴：`Game.Core.Tests/Domain/GameLoopTests.cs`（占位路径）  
  - 经济结算与地价调整：`Game.Core.Tests/Domain/EconomyTests.cs`（占位路径）  
  - 城池与玩家资产变更：`Game.Core.Tests/Domain/CityAndPlayerTests.cs`（占位路径）  
  - AI 行为与策略：`Game.Core.Tests/Domain/AiBehaviorTests.cs`（占位路径）  

- 场景与 UI（Tests.Godot，GdUnit4）  
  - T2 主场景加载与 HUD 可见性：`Tests.Godot/tests/Scenes/Smoke/test_t2_main_scene.gd`（占位路径）  
  - 棋子移动与事件提示：`Tests.Godot/tests/Scenes/Smoke/test_t2_token_and_events.gd`（占位路径）  

- Test-Refs（Taskmaster 回链示例）  
  - Task 17（回合循环）：应在 tasks_back.json / tasks_gameplay.json 中引用 GameLoopTests 与主场景 Smoke 测试。  
  - Task 7/8/14/15（经济与事件）：应在任务视图中引用 EconomyTests 与相关 Smoke 测试。  
  - Task 11/25（AI）：应在任务视图中引用 AiBehaviorTests 与针对极端场景的回合模拟用例。  

> 最终实现时，必须确保上述占位路径与实际测试文件保持一致，并通过 `task-links-validate.py` 等脚本完成 ADR/CH/Overlay/Test-Refs 的自动校验。

## 8.5 契约与文件路径映射（引用型）

本节仅作为“事件名 → 契约类型 → 文件路径”的索引，真正的 SSoT 仍为 C# 契约文件本身与 ADR/测试代码。

### 8.5.1 棋盘与掷骰

- 事件名：`core.sanguo.board.token.moved`  
  - 触发时机：玩家或 AI 棋子根据骰子结果在棋盘上移动到新格子时。  
  - 字段摘要：`GameId, PlayerId, FromIndex, ToIndex, Steps, PassedStart, OccurredAt, CorrelationId, CausationId`。  
  - 契约文件：`Game.Core/Contracts/Sanguo/BoardEvents.cs` 中 `SanguoTokenMoved`。

- 事件名：`core.sanguo.dice.rolled`  
  - 触发时机：玩家或 AI 掷骰子产生点数时。  
  - 字段摘要：`GameId, PlayerId, Value, OccurredAt, CorrelationId, CausationId`。  
  - 契约文件：`Game.Core/Contracts/Sanguo/BoardEvents.cs` 中 `SanguoDiceRolled`。

### 8.5.2 经济与城池

- 事件名：`core.sanguo.economy.month.settled`  
  - 触发时机：每月末完成所有玩家收益结算后。  
  - 字段摘要：`GameId, Year, Month, PlayerSettlements[], OccurredAt, CorrelationId, CausationId`。  
  - 契约文件：`Game.Core/Contracts/Sanguo/EconomyEvents.cs` 中 `SanguoMonthSettled`。

- 事件名：`core.sanguo.economy.season.event.applied`  
  - 触发时机：季度环境事件被评估并应用到目标区域/城池时。  
  - 字段摘要：`GameId, Year, Season, AffectedRegionIds[], YieldMultiplier, OccurredAt, CorrelationId, CausationId`。  
  - 契约文件：`Game.Core/Contracts/Sanguo/EconomyEvents.cs` 中 `SanguoSeasonEventApplied`。

- 事件名：`core.sanguo.economy.year.price.adjusted`  
  - 触发时机：年度地价调整逻辑执行并写回城池价格时。  
  - 字段摘要：`GameId, Year, CityId, OldPrice, NewPrice, OccurredAt, CorrelationId, CausationId`。  
  - 契约文件：`Game.Core/Contracts/Sanguo/EconomyEvents.cs` 中 `SanguoYearPriceAdjusted`。

- 事件名：`core.sanguo.city.bought`  
  - 触发时机：玩家成功购买城池、所有权发生变更时。  
  - 字段摘要：`GameId, BuyerId, CityId, Price, OccurredAt, CorrelationId, CausationId`。  
  - 契约文件：`Game.Core/Contracts/Sanguo/EconomyEvents.cs` 中 `SanguoCityBought`。

- 事件名：`core.sanguo.city.toll.paid`  
  - 触发时机：玩家停留在他人城池并支付过路费时。  
  - 字段摘要：`GameId, PayerId, OwnerId, CityId, Amount, OccurredAt, CorrelationId, CausationId`。  
  - 契约文件：`Game.Core/Contracts/Sanguo/EconomyEvents.cs` 中 `SanguoCityTollPaid`。

### 8.5.3 回合与存档

- 事件名：`core.sanguo.game.turn.started`  
  - 触发时机：某一回合开始时。  
  - 字段摘要：`GameId, TurnNumber, ActivePlayerId, Year, Month, Day, OccurredAt, CorrelationId, CausationId`。  
  - 契约文件：`Game.Core/Contracts/Sanguo/GameEvents.cs` 中 `SanguoGameTurnStarted`。

- 事件名：`core.sanguo.game.turn.ended`  
  - 触发时机：当前回合结束时。  
  - 字段摘要：`GameId, TurnNumber, ActivePlayerId, OccurredAt, CorrelationId, CausationId`。  
  - 契约文件：`Game.Core/Contracts/Sanguo/GameEvents.cs` 中 `SanguoGameTurnEnded`。

- 事件名：`core.sanguo.game.turn.advanced`  
  - 触发时机：回合循环推进到下一回合（并可能推进日期）时。  
  - 字段摘要：`GameId, TurnNumber, ActivePlayerId, Year, Month, Day, OccurredAt, CorrelationId, CausationId`。  
  - 契约文件：`Game.Core/Contracts/Sanguo/GameEvents.cs` 中 `SanguoGameTurnAdvanced`。

- 事件名：`core.sanguo.game.saved`  
  - 触发时机：游戏存档成功时。  
  - 字段摘要：`GameId, SaveSlotId, OccurredAt, CorrelationId, CausationId`。  
  - 契约文件：`Game.Core/Contracts/Sanguo/GameEvents.cs` 中 `SanguoGameSaved`。

- 事件名：`core.sanguo.game.loaded`  
  - 触发时机：从存档加载游戏成功时。  
  - 字段摘要：`GameId, SaveSlotId, OccurredAt, CorrelationId, CausationId`。  
  - 契约文件：`Game.Core/Contracts/Sanguo/GameEvents.cs` 中 `SanguoGameLoaded`。

- 事件名：`core.sanguo.game.ended`  
  - 触发时机：游戏满足结束条件（破产、回合数上限或目标资产达成等）时。  
  - 字段摘要：`GameId, EndReason, OccurredAt, CorrelationId, CausationId`。  
  - 契约文件：`Game.Core/Contracts/Sanguo/GameEvents.cs` 中 `SanguoGameEnded`。

### 8.5.4 玩家与 AI

- 事件名：`core.sanguo.player.state.changed`  
  - 触发时机：玩家资金、位置或资产发生变更时。  
  - 字段摘要：`GameId, PlayerId, Money, PositionIndex, OccurredAt, CorrelationId, CausationId`。  
  - 契约文件：`Game.Core/Contracts/Sanguo/PlayerAndAiEvents.cs` 中 `SanguoPlayerStateChanged`。

- 事件名：`core.sanguo.ai.decision.made`  
  - 触发时机：AI 对当前局面作出决策（买地/放弃等）时。  
  - 字段摘要：`GameId, AiPlayerId, DecisionType, TargetCityId, OccurredAt, CorrelationId, CausationId`。  
  - 契约文件：`Game.Core/Contracts/Sanguo/PlayerAndAiEvents.cs` 中 `SanguoAiDecisionMade`。

> 最终代码落地时，如需新增事件类型，必须同时更新：  
> 1）本节映射表；2）对应 C# 契约文件；3）tasks_back.json / tasks_gameplay.json 中的 `contractRefs`；并通过相关 Python 校验脚本完成回链校验。

## Test-Refs

- `Tests.Godot/tests/Scenes/Sanguo/test_sanguo_board_view_token_move.gd`
