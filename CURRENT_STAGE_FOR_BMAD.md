# 当前阶段游戏实现快照（供 BMAD 下一阶段 PRD）

- 生成日期：2026-03-10
- 数据来源：`.taskmaster/tasks/tasks.json`、`.taskmaster/tasks/tasks_back.json`、`.taskmaster/tasks/tasks_gameplay.json`
- 状态口径：**`tasks.json` 是唯一 SSOT**；任务视图状态不用于完成度判断，仅用于补充 `test_refs`。
- 代码取证范围：`Game.Core/**`、`Game.Godot/Scripts/**`、`Game.Core.Tests/**`、`Tests.Godot/tests/**`

## 1. 阶段结论（面向 PRD 规划）

- 当前仓库已完成“可玩主循环 + 数据驱动骨架 + 质量门禁基础”。
- 游戏从“主菜单 -> 新游戏配置 -> 回合推进 -> 经济/事件/AI/战斗分支 -> 结算”具备可执行链路。
- 事件契约、UI解释链、日志与门禁脚本已具备，适合进入“内容规模化 + 新手体验收口 + 数值护栏强化”的下一阶段 PRD。

## 2. done 任务统计（SSOT = tasks.json）

- `tasks.json` done 数量：**39**
- done 任务列表：`T1, T2, T3, T4, T5, T6, T7, T8, T9, T10, T11, T12, T13, T14, T15, T16, T17, T19, T20, T21, T22, T23, T25, T26, T28, T30, T39, T46, T47, T49, T50, T52, T53, T54, T55, T56, T57, T59, T61`
- 任务视图中的状态字段不参与阶段完成度结论。

## 3. 当前代码逻辑下的已完成功能（按模块）

### A. 可运行骨架与核心回合主循环

- 关联任务：`T1, T2, T3, T4, T5, T6, T10, T17, T22`
- 功能细节：
  - Godot + C# 工程可启动，主循环控制器已接入场景。
  - 环形棋盘、玩家、城池、骰子与回合推进形成闭环。
  - 掷骰、移动、回合推进等核心事件可被 UI 消费。
- 关键实现文件：
  - `Game.Godot/Scripts/Sanguo/SanguoGameLoopController.cs`
  - `Game.Core/Services/SanguoTurnManager.cs`
  - `Game.Core/Domain/SanguoBoardState.cs`
  - `Game.Core/Services/SanguoDiceService.cs`
- 关键测试文件：
  - `Game.Core.Tests/Tasks/Task17TurnTests.cs`
  - `Tests.Godot/tests/Scenes/Sanguo/test_sanguo_game_loop_dice_flow.gd`

### B. 经济系统与结算规则

- 关联任务：`T7, T12, T13, T14, T15, T16, T20`
- 功能细节：
  - 购买、过路费、月末收益、季度事件、年度地价调整均有实现。
  - 经济事件支持 AppliedMultipliers 载荷，便于解释与回放。
  - 资金和日期已在 HUD 呈现。
- 关键实现文件：
  - `Game.Core/Services/SanguoEconomyManager.cs`
  - `Game.Core/Contracts/Sanguo/EconomyEvents.cs`
  - `Game.Core/Contracts/Sanguo/AppliedMultipliers.cs`
  - `Game.Godot/Scripts/UI/HUD.cs`
- 关键测试文件：
  - `Game.Core.Tests/Tasks/Task14MonthEndSettlementTests.cs`
  - `Game.Core.Tests/Tasks/Task15QuarterEventTests.cs`
  - `Game.Core.Tests/Tasks/Task16YearEndPriceTests.cs`
  - `Game.Core.Tests/Tasks/Task51AppliedMultipliersPayloadTests.cs`

### C. 事件总线、契约与 UI 解释链

- 关联任务：`T8, T19, T21, T23, T50, T54`
- 功能细节：
  - 事件总线与事件常量在 Game.Core/Contracts 统一。
  - UI 具备事件 DTO 映射、解释服务、日志面板、结果弹窗。
  - 新游戏配置界面作为开局入口，产出 GameStartConfig。
- 关键实现文件：
  - `Game.Core/Services/EventBus.cs`
  - `Game.Core/Contracts/EventTypes.cs`
  - `Game.Godot/Scripts/UI/EventExplainService.cs`
  - `Game.Godot/Scripts/UI/HudEventDtoMapper.cs`
  - `Game.Godot/Scripts/UI/MainMenu.cs`
- 关键测试文件：
  - `Game.Core.Tests/Tasks/Task50GameStartConfigTests.cs`
  - `Tests.Godot/tests/UI/test_task50_new_game_menu_started_event_payload.gd`
  - `Tests.Godot/tests/UI/Task54/test_task54_new_game_setup_constraints_and_start.gd`
  - `Tests.Godot/tests/UI/test_event_log_summary_localized.gd`

### D. AI 决策与自动推进

- 关联任务：`T11, T25, T61`
- 功能细节：
  - AI 已从基础行为升级到可复盘的确定性策略。
  - AI 与玩家共用主循环事件管线。
  - AI 选择、执行与稳定性已有测试。
- 关键实现文件：
  - `Game.Core/Services/DefaultSanguoAiDecisionPolicy.cs`
  - `Game.Core/Services/SanguoAiDeterministicDecisionApi.cs`
  - `Game.Core/Services/SanguoAiState.cs`
- 关键测试文件：
  - `Game.Core.Tests/Tasks/Task25AiTests.cs`
  - `Game.Core.Tests/Tasks/Task61AiDeterministicStrategyTests.cs`
  - `Game.Core.Tests/Services/SanguoAiExecutionTests.cs`

### E. 内容数据驱动（地图/角色/随机事件/卡牌/战斗）

- 关联任务：`T52, T53, T55, T56, T57, T59`
- 功能细节：
  - BeforeRoll 行动窗口与事件触发顺序规则已落地。
  - 地图定义与校验器、角色/随机事件/卡牌目录与加载器已存在。
  - PVE 战斗分支可进入并返回主循环。
- 关键实现文件：
  - `Game.Core/Contracts/Sanguo/SanguoMapDefinitionV2.cs`
  - `Game.Core/Contracts/Sanguo/SanguoEventOrderingRules.cs`
  - `Game.Core/Services/Sanguo/SanguoMapsCatalogLoader.cs`
  - `Game.Core/Services/Sanguo/SanguoRandomEventsCatalogLoader.cs`
  - `Game.Core/Services/Sanguo/SanguoCombatResolver.cs`
  - `Game.Godot/Scripts/Sanguo/SanguoBattleView.cs`
- 关键测试文件：
  - `Game.Core.Tests/Tasks/Task52TurnPhaseWindowTests.cs`
  - `Game.Core.Tests/Tasks/Task53MapConfigValidationTests.cs`
  - `Game.Core.Tests/Tasks/Task56RandomEventDeterminismTests.cs`
  - `Game.Core.Tests/Tasks/Task57ActionCardWindowTests.cs`
  - `Game.Core.Tests/Tasks/Task59CombatTriggerAndReturnTests.cs`
  - `Tests.Godot/tests/Scenes/Sanguo/test_task59_sanguo_battle_roundtrip_returns_to_map.gd`

### F. 质量门禁与可观测性基础

- 关联任务：`T39, T46, T47, T49`
- 功能细节：
  - quality_gates.py 已聚合构建、覆盖率、GdUnit、smoke、性能、审计。
  - headless smoke strict 与 marker 假阳性止损能力已接入。
  - 性能 P95 与 security-audit.jsonl 校验链已接通。
- 关键实现文件：
  - `scripts/python/quality_gates.py`
  - `scripts/python/smoke_headless.py`
  - `scripts/python/validate_perf.py`
  - `scripts/python/validate_audit_logs.py`
- 关键测试文件：
  - `Game.Core.Tests/Tasks/Task39AuditPerformanceTests.cs`
  - `Game.Core.Tests/Tasks/Task46HeadlessSmokeStrictModeTests.cs`
  - `Game.Core.Tests/Tasks/Task47QualityGatesGdUnitAggregationTests.cs`
  - `Game.Core.Tests/Tasks/Task49HeadlessSmokeHardeningTests.cs`

## 4. done 任务描述与测试映射（逐任务）

> 说明：状态列只使用 `tasks.json`（SSOT）；测试文件优先来自任务视图 `test_refs`，并补充按任务号自动检索到的测试。

| Task | 标题 | tasks.json状态 | 描述摘要 | 对应测试文件 |
|---|---|---|---|---|
| T1 | 设置Godot项目 | done | 初始化Godot项目并配置C#环境。 | `Tests.Godot/tests/Scenes/Smoke/test_main_scene_smoke.gd`<br>`Game.Core.Tests/Tasks/Task1EnvironmentEvidencePersistenceTests.cs`<br>`Game.Core.Tests/Tasks/Task1WindowsPlatformGateTests.cs`<br>`Game.Core.Tests/Tasks/Task1ToolchainVersionChecksTests.cs`<br>`Game.Core.Tests/Tasks/Task1PreflightEvidenceGuard.cs`<br>`Game.Core.Tests/Tasks/Task1TaskViewsTests.cs` |
| T2 | 创建环形地图数据结构 | done | 设计并实现游戏地图的环形数据结构。 | `Game.Core.Tests/Domain/ValueObjects/CircularMapPositionTests.cs` |
| T3 | 实现城池类 | done | 定义城池的属性和方法。 | `Game.Core.Tests/Domain/CityTests.cs` |
| T4 | 实现玩家类 | done | 定义玩家的属性和基本操作。 | `Game.Core.Tests/Domain/SanguoPlayerTests.cs` |
| T5 | 实现骰子机制 | done | 设计骰子投掷的逻辑。 | `Game.Core.Tests/Services/SanguoDiceServiceTests.cs` |
| T6 | 实现回合管理器 | done | 控制游戏回合的顺序和时间推进。 | `Game.Core.Tests/Services/SanguoTurnManagerTests.cs` |
| T7 | 实现经济结算管理器 | done | 处理月末收益结算和地价调整。 | `Game.Core.Tests/Services/SanguoEconomyManagerTests.cs` |
| T8 | 实现事件管理器 | done | 实现域事件总线（EventBus）与订阅生命周期管理。 | `Game.Core.Tests/Services/EventBusTests.cs` |
| T9 | 设计UI界面 | done | 设计游戏的用户界面。 | `Tests.Godot/tests/UI/test_hud_scene.gd`<br>`Tests.Godot/tests/UI/test_hud_updates_on_events.gd`<br>`Game.Core.Tests/Domain/SanguoPlayerViewTests.cs`<br>`Game.Core.Tests/Tasks/Task9UiBoundaryTests.cs` |
| T10 | 实现玩家棋子移动 | done | 根据骰子结果移动玩家棋子。 | `Tests.Godot/tests/Scenes/Sanguo/test_sanguo_board_view_token_move.gd` |
| T11 | 实现AI行为 | done | 设计AI的基本行动逻辑。 | `Game.Core.Tests/Services/SanguoAiBehaviorTests.cs`<br>`Game.Core.Tests/Services/SanguoAiExecutionTests.cs`<br>`Game.Core.Tests/Domain/SanguoPlayerViewTests.cs` |
| T12 | 实现土地购买逻辑 | done | 处理玩家购买城池的逻辑。 | `Game.Core.Tests/Domain/SanguoPlayerTests.cs`<br>`Game.Core.Tests/Domain/CityTests.cs`<br>`Game.Core.Tests/Domain/SanguoBoardStateTests.cs` |
| T13 | 实现过路费支付逻辑 | done | 处理玩家支付过路费的逻辑。 | `Game.Core.Tests/Services/SanguoEconomyManagerTests.cs` |
| T14 | 实现月末收益结算 | done | 自动结算玩家的月末收益。 | `Game.Core.Tests/Tasks/Task14MonthEndSettlementTests.cs` |
| T15 | 实现季度环境事件 | done | 触发并应用季度环境事件。 | `Game.Core.Tests/Tasks/Task15QuarterEventTests.cs`<br>`Game.Core.Tests/Services/QuarterlyEnvironmentEventTests.cs` |
| T16 | 实现年度地价调整 | done | 每年年初调整城池的地价。 | `Game.Core.Tests/Tasks/Task16YearEndPriceTests.cs` |
| T17 | 实现回合循环 | done | 确保游戏回合循环正常进行。 | `Game.Core.Tests/Tasks/Task17TurnTests.cs`<br>`Game.Core.Tests/Domain/MoneyTests.cs`<br>`Game.Core.Tests/Domain/SanguoBoardStateTests.cs`<br>`Tests.Godot/tests/Scenes/Sanguo/test_sanguo_board_view_token_move.gd`<br>`Tests.Godot/tests/UI/test_hud_updates_on_events.gd` |
| T19 | 实现UI事件提示 | done | 在UI上显示游戏事件提示。 | `Tests.Godot/tests/UI/test_hud_scene.gd`<br>`Tests.Godot/tests/UI/test_hud_updates_on_events.gd` |
| T20 | 实现UI资金显示 | done | 在UI上显示玩家的资金信息。 | `Tests.Godot/tests/UI/test_hud_scene.gd`<br>`Tests.Godot/tests/UI/test_hud_updates_on_events.gd` |
| T21 | 实现UI日期显示 | done | 在UI上显示当前游戏日期。 | `Tests.Godot/tests/UI/test_hud_scene.gd`<br>`Tests.Godot/tests/UI/test_hud_updates_on_events.gd`<br>`Tests.Godot/tests/UI/test_hud_date_display_reflects_latest_date.gd` |
| T22 | 实现UI骰子结果显示 | done | 在UI上显示骰子投掷结果。 | `Tests.Godot/tests/UI/test_hud_scene.gd`<br>`Tests.Godot/tests/UI/test_hud_updates_on_events.gd` |
| T23 | 实现UI城池状态显示 | done | 在UI上显示城池的占有状态。 | `Tests.Godot/tests/Scenes/Sanguo/test_sanguo_city_ownership_status_display.gd` |
| T25 | 实现AI策略优化 | done | 优化AI的决策策略。 | `Game.Core.Tests/Tasks/Task25AiTests.cs` |
| T26 | 实现游戏结束条件 | done | 定义并实现游戏的结束条件。 | `Game.Core.Tests/Utilities/NoGodotDependencyTests.cs`<br>`Game.Core.Tests/Services/PlayerEliminationTests.cs` |
| T28 | 实现游戏主菜单 | done | 设计并实现游戏的主菜单。 | `Tests.Godot/tests/UI/test_main_menu_scene.gd`<br>`Tests.Godot/tests/UI/test_main_menu_events.gd`<br>`Tests.Godot/tests/UI/test_main_menu_load_play_quit_routing.gd`<br>`Tests.Godot/tests/UI/test_main_menu_quit_button.gd`<br>`Tests.Godot/tests/Scenes/Smoke/test_menu_quit_is_consumed_by_game_loop.gd`<br>`Tests.Godot/tests/Scenes/Smoke/test_menu_play_starts_game_loop.gd`<br>... (+1 files) |
| T30 | 实现游戏帮助和教程 | done | 提供游戏的帮助信息和教程。 | `Tests.Godot/tests/Scenes/Sanguo/test_sanguo_help_ui_loads_headless.gd`<br>`Tests.Godot/tests/UI/test_help_tutorial_basic_interactions.gd`<br>`Tests.Godot/tests/UI/test_help_tutorial_uses_project_theme.gd`<br>`Tests.Godot/tests/UI/test_help_tutorial_localized_content_non_empty.gd`<br>`Tests.Godot/tests/UI/test_help_tutorial_toggle_and_navigation.gd` |
| T39 | 性能 P95 与审计 JSONL 校验 | done | 根据 Phase-13-Quality-Gates-Backlog.md B4，将性能 P95 阈值与 security-audit.jsonl 的结构校验纳入 quality_gates.py，实现对 logs/perf/summa... | `Game.Core.Tests/Tasks/Task39AuditPerformanceTests.cs` |
| T46 | Python 版 headless smoke 封装与 strict 模式开关 | done | 根据 Phase-12-Headless-Smoke-Backlog.md B1/B2，在当前 Godot + C# 模板中实现 Python 版 headless smoke 封装脚本（替代/补充 PowerShell 版本），并增... | `Game.Core.Tests/Tasks/Task46HeadlessSmokeScriptTests.cs`<br>`Game.Core.Tests/Tasks/Task46HeadlessSmokeNonStrictTests.cs`<br>`Game.Core.Tests/Tasks/Task46HeadlessSmokeStrictModeTests.cs`<br>`Game.Core.Tests/Tasks/Task46HeadlessSmokeCiExampleTests.cs` |
| T47 | 扩展 quality_gates.py 覆盖率阈值与 GdUnit4 集成 | done | 承接 Phase-13-Quality-Gates-Script.md 与 Backlog：将 xUnit 覆盖率门禁提升到蓝图标准（行≥90%、分支≥85%，可由环境变量覆盖），并把关键 GdUnit4 集合（Adapters+Se... | `Game.Core.Tests/Tasks/Task47QualityGatesCoverageSummaryTests.cs`<br>`Game.Core.Tests/Tasks/Task47QualityGatesGdUnitAggregationTests.cs`<br>`Tests.Godot/tests/Integration/test_quality_gates_gdunit_adapters_security_aggregation.gd`<br>`Tests.Godot/tests/Scenes/Smoke/test_task47_main_scene_smoke_wrapper.gd`<br>`Game.Core.Tests/Tasks/Task47QualityGatesDocumentationRefsTests.cs`<br>`Game.Core.Tests/Tasks/Task47QualityGatesBehaviorTests.cs` |
| T49 | Headless smoke strict 稳健化：防 marker 假阳性（smoke session 可自退出） | done | 针对 headless smoke strict 可能出现的 marker 假阳性（marker 过早打印、异常在 marker 之后发生、或长期运行只能靠 timeout kill 导致无法区分“已就绪但挂死/崩溃”），引入可自退出... | `Game.Core.Tests/Tasks/Task49HeadlessSmokeHardeningTests.cs` |
| T50 | Spine: GameStartConfig 与可复现开局输入 | done | 定义唯一开局配置与可复现输入（地图/人数/初始资金档/全局事件间隔/seed/角色分配全局唯一），并通过事件对外发布。 | `Game.Core.Tests/Tasks/Task50GameStartConfigTests.cs`<br>`Tests.Godot/tests/UI/test_task50_new_game_menu_started_event_payload.gd` |
| T52 | Spine: 回合窗口锁死（BeforeRoll 行动卡 0/1）与事件触发顺序 | done | 锁死 TurnPhase.BeforeRoll 窗口规则（行动卡每回合最多1张）以及事件格与全局事件触发顺序（同一 RandomEventPool）。 | `Game.Core.Tests/Tasks/Task52TurnPhaseWindowTests.cs`<br>`Game.Core.Tests/Tasks/Task52EventTriggerOrderTests.cs`<br>`Game.Core.Tests/Tasks/Task52OutOfOrderEventRegressionTests.cs` |
| T53 | 模块: 地图配置（多文件）与 Tile 语义 | done | 引入地图配置多文件格式，并定义 city/pass/event/empty 等 tile 语义与基础数值来源。 | `Game.Core.Tests/Tasks/Task53MapConfigParsingTests.cs`<br>`Game.Core.Tests/Tasks/Task53MapConfigValidationTests.cs`<br>`Tests.Godot/tests/Scenes/Sanguo/test_task53_sanguo_map_tile_name_fallback.gd` |
| T54 | 模块: 新游戏配置界面（地图/人数/资金档/全局事件间隔/选角） | done | 新增新游戏配置界面，作为唯一开局入口，产出 GameStartConfig 并启动对局。 | `Tests.Godot/tests/UI/Task54/test_task54_new_game_setup_constraints_and_start.gd`<br>`Game.Core.Tests/Tasks/Task54RoleAssignmentUniquenessTests.cs`<br>`Tests.Godot/tests/UI/Task54/test_task54_hud_shows_avatar_name_money_only.gd`<br>`Tests.Godot/tests/UI/Task54/test_task54_flow_requires_new_game_setup_before_game_start.gd`<br>`Tests.Godot/tests/UI/Task54/test_task54_new_game_setup_starts_game_with_selected_players_and_money.gd`<br>`Tests.Godot/tests/UI/Task54/test_task54_global_event_interval_observable_matches_config.gd` |
| T55 | 模块: 角色配置（≥8 角色）与初始资金口径 | done | 完善角色数据为只读配置，并冻结初始资金与经济 steps 口径。 | `Game.Core.Tests/Tasks/Task55CharacterConfigParsingTests.cs`<br>`Game.Core.Tests/Tasks/Task55StartingMoneyComputationTests.cs`<br>`Game.Core.Tests/Tasks/Task55CharacterMultipliersAppliedTests.cs`<br>`Game.Core.Tests/Tasks/Task55CharacterEventSnapshotTests.cs` |
| T56 | 模块: 随机事件池（事件格 + 每N回合全局事件） | done | 引入随机事件池并统一两类触发：事件格触发与每N回合全局触发；要求可复现。 | `Game.Core.Tests/Tasks/Task56RandomEventDeterminismTests.cs`<br>`Game.Core.Tests/Tasks/Task56EventMultiplierTests.cs`<br>`Tests.Godot/tests/UI/test_task56_hud_event_prompt_uses_payload.gd`<br>`Game.Core.Tests/Tasks/Task56RandomEventCoverageTests.cs` |
| T57 | 模块: 行动卡（BeforeRoll）止损版 | done | 引入行动卡卡池：掷骰前可出 0/1 张行动卡影响本回合倍率输入。 | `Game.Core.Tests/Tasks/Task57ActionCardPolicyTests.cs`<br>`Game.Core.Tests/Tasks/Task57ActionCardWindowTests.cs`<br>`Tests.Godot/tests/UI/test_task57_action_card_before_roll_flow.gd`<br>`Tests.Godot/tests/UI/test_task57_before_roll_play_or_skip.gd`<br>`Tests.Godot/tests/UI/test_task57_before_roll_action_card_play_or_skip_flow.gd`<br>`Game.Core.Tests/Tasks/Task57ActionCardOwnershipTransferTests.cs` |
| T59 | 模块: 战斗（PVE）触发与回主循环 | done | 引入 PVE 战斗分支循环：从地图/事件触发进入战斗，结束后回到主循环。 | `Game.Core.Tests/Tasks/Task59CombatTriggerAndReturnTests.cs`<br>`Game.Core.Tests/Tasks/Task59CombatDeterminismTests.cs`<br>`Tests.Godot/tests/Scenes/Sanguo/test_task59_sanguo_battle_roundtrip_returns_to_map.gd` |
| T61 | 模块: AI 最小确定性策略（止损版） | done | 实现 AI 的最小确定性策略：与玩家一致的行动流程、可复盘决策取证、并发/随机止损约束。 | `Game.Core.Tests/Tasks/Task61AiDeterministicStrategyTests.cs` |

## 5. 给 BMAD 下一阶段 PRD 的输入建议

- 以 `tasks.json` 的 done 列表作为已完成边界，直接规划下一阶段 backlog。
- 下一阶段建议以三条主线组织：
  1. **内容规模化**：地图/角色/事件/卡牌/建筑/宝物的批量扩展与字段门禁。
  2. **新手体验闭环**：目标提示、风险提示、奖励反馈、失败引导的统一 UX。
  3. **数值与可解释性收口**：倍率来源可视化、上限/下限护栏、回放可追溯。
- PRD 中请显式引用当前已存在的事件契约与测试资产，优先“扩展已有链路”，避免平行新系统。

## 6. 取证附录（已存在的核心资产）

- 核心契约目录：`Game.Core/Contracts/Sanguo/`
- 主循环控制器：`Game.Godot/Scripts/Sanguo/SanguoGameLoopController.cs`
- UI 解释链：`Game.Godot/Scripts/UI/EventExplainService.cs`、`Game.Godot/Scripts/UI/HudEventDtoMapper.cs`
- 质量门禁入口：`scripts/python/quality_gates.py`
- 验收门禁入口：`scripts/sc/acceptance_check.py`
- Godot 测试目录：`Tests.Godot/tests/`
- Core 单测目录：`Game.Core.Tests/`

