---
GDD-ID: GDD-SANGUO-UI-WIRING-V1
Title: Sanguo Chapter 7 UI Wiring Board
Status: Draft
Owner: codex
Last Updated: 2026-05-05
Encoding: UTF-8
Applies-To:
  - .taskmaster/tasks/tasks.json
  - docs/gdd/ui-gdd-flow.md
ADR-Refs:
  - ADR-0005
  - ADR-0011
  - ADR-0018
  - ADR-0015
  - ADR-0020
  - ADR-0021
  - ADR-0024
  - ADR-0025
  - ADR-0026
  - ADR-0028
  - ADR-0022
  - ADR-0030
Test-Refs:
  - Tests.Godot/tests/Scenes/Smoke/test_main_scene_smoke.gd
  - Game.Core.Tests/Tasks/Task1EnvironmentEvidencePersistenceTests.cs
  - Game.Core.Tests/Tasks/Task1WindowsPlatformGateTests.cs
  - Game.Core.Tests/Tasks/Task1ToolchainVersionChecksTests.cs
  - Game.Core.Tests/Domain/ValueObjects/CircularMapPositionTests.cs
  - Game.Core.Tests/Domain/CityTests.cs
  - Game.Core.Tests/Domain/SanguoPlayerTests.cs
  - Game.Core.Tests/Services/SanguoDiceServiceTests.cs
---

# Sanguo Chapter 7 UI Wiring Board

## 1. Design Goals

### 1.1 Experience Pillars
- Stable entry: startup, continue, and runtime entry must be explicit and recoverable.
- Readable loop: phase, pressure, resources, HP, prompts, and outcomes must be understandable from the UI alone.
- Explainable systems: config, governance, save, migration, and audit state must have visible ownership instead of hiding in logs.
- Deterministic recovery: failure, invalid action, persistence, and fallback states must be reproducible and visible.

### 1.2 Target Use
- Provide one governed planning surface for all currently completed task capabilities.
- Keep Chapter 7 focused on player-facing or operator-facing surface ownership before polish-only work.

## 2. Core Player Loop

1. Launch or continue from a stable entry surface.
2. Enter the runtime loop with readable phase, timing, pressure, and survival state.
3. Interact with combat, economy, progression, and meta systems through governed surfaces.
4. Resolve win, loss, save/load, config-governance, and migration outcomes with visible feedback.

## 3. Completed Capability Inventory

| Capability Slice | Audience | Task IDs | Player-Facing Meaning | Primary UI Need |
| --- | --- | --- | --- | --- |
| Entry And Bootstrap | player-facing | T01, T11, T21, T85, T91, T92, T93, T101, T108, T131, T164, T170, T176, T177 | Show canonical startup path, valid continue behavior, and explicit startup failure recovery | MainMenu / Boot Flow |
| Core Loop State And Outcome | player-facing | T03, T07, T08, T09, T10, T18, T19, T23, T24, T63, T78, T104, T106, T119, T120, T137, T141, T142 | Render readable phase, timer, HP, reward, prompt, and win/lose state from runtime events | HUD / Prompt / Outcome Surfaces |
| Combat Pressure And Interaction | player-facing | T02, T04, T05, T06, T20, T22, T53, T59, T109, T126, T134, T146, T178 | Render enemy pressure, targeting, combat outcomes, and camera interaction without hidden state | Combat HUD / Pressure / Camera Feedback |
| Economy Build And Progression | player-facing | T12, T13, T14, T15, T16, T17 | Render deterministic resource, build, queue, upgrade, and progression changes with clear invalid-state feedback | Resource / Build / Progression Panels |
| Meta Systems And Platform | player-facing or mixed | T25, T26, T27, T28, T29, T30, T41, T42, T43, T44, T45, T46, T47, T48, T49, T50, T51, T52, T54, T55, T56, T57, T58, T60, T61, T62, T64, T65, T66, T67, T68, T69, T70, T71, T72, T73, T74, T75, T76, T77, T79, T80, T81, T82, T83, T84, T86, T87, T88, T89, T90, T94, T95, T96, T97, T98, T99, T100, T102, T103, T105, T107, T110, T111, T112, T113, T114, T115, T116, T117, T118, T121, T122, T123, T124, T125, T127, T128, T129, T130, T132, T133, T135, T136, T138, T139, T140, T143, T144, T145, T147, T148, T149, T150, T151, T152, T153, T154, T155, T156, T157, T158, T159, T160, T161, T162, T163, T165, T166, T167, T168, T169, T171, T172, T173, T174, T175, T179, T180, [T194](#task-194-traceability) | Render persistence, localization, audio, performance, and platform status on governed player-visible surfaces | Settings / Save / Meta Surfaces |
| Config Governance And Audit | operator-facing or mixed | T31, T32, T33, T34, T35, T36, T37, T38, T39, T40 | Render active config, schema status, fallback policy, migration status, and audit metadata without relying on logs-only evidence | Config Summary / Audit / Migration Surfaces |

## 4. Flow Recomposition

### Entry And Bootstrap

- T01 `设置Godot项目`
- T11 `实现AI行为`
- T21 `实现UI日期显示`
- T85 `Module: campaign runmode isolation (split from T74)`
- T91 `Module: core assertion gate runner (split from T80)`
- T92 `Module: UI assertion gate runner (split from T80)`
- T93 `Module: campaign run mode and start payload completion`
- T101 `Module: boss dice profile by difficulty and duration target integration pack`
- T108 `Module: campaign AI hard-disable runtime guard completion`
- T131 `Module: boss difficulty profile schema (split from T101)`
- T164 `Module: runtime signal subscription lifecycle guard (split from T158)`
- T170 `Module: campaign contract field harmonization for runtime flows (split from T145)`
- T176 `Wire UI: MainMenu And Boot Flow`
- T177 `Wire UI: Runtime HUD And Outcome Surfaces`
### Core Loop State And Outcome

- T03 `实现城池类`
- T07 `实现经济结算管理器`
- T08 `实现事件管理器`
- T09 `设计UI界面`
- T10 `实现玩家棋子移动`
- T18 `实现存档功能`
- T19 `实现UI事件提示`
- T23 `实现UI城池状态显示`
- T24 `实现UI事件日志`
- T63 `模块: 全局事件触发机制（RoundNumber）`
- T78 `Module: RewardDraftEngine (deterministic 3-choice draft) integration pack`
- T104 `Module: board event auto-trigger and skip restriction guard integration pack`
- T106 `Module: random objective reward source integration integration pack`
- T119 `Module: reward draft candidate determinism (split from T78)`
- T120 `Module: reward draft commit and source tags (split from T78)`
- T137 `Module: event tile auto-trigger enforcement (split from T104)`
- T141 `Module: objective reward source integration (split from T106)`
- T142 `Module: objective reward draft deterministic hook (split from T106)`
### Combat Pressure And Interaction

- T02 `创建环形地图数据结构`
- T04 `实现玩家类`
- T05 `实现骰子机制`
- T06 `实现回合管理器`
- T20 `实现UI资金显示`
- T22 `实现UI骰子结果显示`
- T53 `模块: 地图配置（多文件）与 Tile 语义`
- T59 `模块: 战斗（PVE）触发与回主循环`
- T109 `Module: campaign contracts and DTO mapper completion integration pack`
- T126 `Module: camp durability persistence mapping (split from T97)`
- T134 `Module: boss pressure explain payload mapper (split from T102)`
- T146 `Module: campaign HUD DTO mapper closure (split from T109)`
- T178 `Wire UI: Combat Pressure And Interaction Surfaces`
### Economy Build And Progression

- T12 `实现土地购买逻辑`
- T13 `实现过路费支付逻辑`
- T14 `实现月末收益结算`
- T15 `实现季度环境事件`
- T16 `实现年度地价调整`
- T17 `实现回合循环`
### Meta Systems And Platform

- T25 `实现AI策略优化`
- T26 `实现游戏结束条件`
- T27 `实现音效和音乐`
- T28 `实现游戏主菜单`
- T29 `实现游戏设置菜单`
- T30 `实现游戏帮助和教程`
- T41 `性能报告与历史追踪（reports/performance/**）`
- T42 `独立性能门禁 CI 工作流（performance-gates.yml）`
- T43 `代码签名与安全分发`
- T44 `导出预设与多配置支持`
- T45 `架构依赖护栏与依赖图校验骨架`
- T46 `Python 版 headless smoke 封装与 strict 模式开关`
- T47 `扩展 quality_gates.py 覆盖率阈值与 GdUnit4 集成`
- T48 `Godot 安全适配层增强：外链白名单、文件访问与 OS.execute 守卫`
- T49 `Headless smoke strict 稳健化：防 marker 假阳性（smoke session 可自退出）`
- T50 `Spine: GameStartConfig 与可复现开局输入`
- T51 `Spine: 倍率合成规则与 applied_multipliers 事件快照`
- T52 `Spine: 回合窗口锁死（BeforeRoll 行动卡 0/1）与事件触发顺序`
- T54 `模块: 新游戏配置界面（地图/人数/资金档/全局事件间隔/选角）`
- T55 `模块: 角色配置（≥8 角色）与初始资金口径`
- T56 `模块: 随机事件池（事件格 + 每N回合全局事件）`
- T57 `模块: 行动卡（BeforeRoll）止损版`
- T58 `模块: 建筑扩展（买地后建造类型）`
- T60 `模块: 每局胜利与结算界面`
- T61 `模块: AI 最小确定性策略（止损版）`
- T62 `模块: 宝物系统（relics）止损版`
- T64 `模块: 州郡（regions）配置与全占增益`
- T65 `模块: 州郡连协收费（经济型止损版）`
- T66 `Module: A-006 Forced Challenge Prompt UI Integration Tests`
- T67 `Module: A-007 Forced Challenge Fail-to-Camp UI Integration Tests`
- T68 `Module: HUD explainability integration pack`
- T69 `Module: i18n release/dev exposure policy (A-011/A-012)`
- T70 `Module: replay integrity integration pack`
- T71 `Module: diagnostic payload desensitization and retention window (A-016/A-017) integration pack`
- T72 `Module: audit write fallback and rotation cap (A-018/A-019) integration pack`
- T73 `Module: contract evolution compatibility gate (A-020)`
- T74 `Module: CampaignRuleEngine integration pack`
- T75 `Module: CampLifecycleEngine integration pack`
- T76 `Module: BossPressureEngine integration pack`
- T77 `Module: RandomObjectiveEngine (pace-compensation loop) integration pack`
- T79 `Module: campaign-mode AI hard-disable guard`
- T80 `Module: PRD v3 assertion gate integration pack`
- T81 `Module: popup-log atomic commit (split from T68)`
- T82 `Module: HUD log overflow/windowing (split from T68)`
- T83 `Module: replay trust hash + save_untrusted (split from T70)`
- T84 `Module: replay mismatch mode policy (split from T70)`
- T86 `Module: campaign endgame adjudicator (split from T74)`
- T87 `Module: camp transition + one-action rule (split from T75)`
- T88 `Module: leave-camp save retry + warning (split from T75)`
- T89 `Module: boss pressure timeline (split from T76)`
- T90 `Module: forced challenge preemption (split from T76)`
- T94 `Module: commander roster and strategem pick flow integration pack`
- T95 `Module: campaign HUD parameter panel and i18n`
- T96 `Module: campaign round lifecycle state machine integration pack`
- T97 `Module: camp building slot and durability model integration pack`
- T98 `Module: camp one-action-per-round guard`
- T99 `Module: camp building effects minimum set integration pack`
- T100 `Module: camp durability fatal adjudicator integration pack`
- T102 `Module: boss pressure resolver and explainability payload integration pack`
- T103 `Module: boss reveal delay challenge and hard-cap forcing integration pack`
- T105 `Module: random objective publish-settle timeline closure integration pack`
- T107 `Module: campaign win-lose adjudicator completion integration pack`
- T110 `Module: campaign content-pack schema and gates extension integration pack`
- T111 `Module: PRD v3 business acceptance integration suite integration pack`
- T112 `Module: PRD v3 explainability/replay/i18n hard-gate closure integration pack`
- T113 `Module: diagnostic payload desensitization policy (split from T71)`
- T114 `Module: diagnostic retention window enforcement (split from T71)`
- T115 `Module: audit write fallback path (split from T72)`
- T116 `Module: audit fallback rotation cap (split from T72)`
- T117 `Module: objective generation determinism (split from T77)`
- T118 `Module: objective settlement timeline closure (split from T77)`
- T121 `Module: commander roster lock/open states (split from T94)`
- T122 `Module: active/passive strategem selection guard (split from T94)`
- T123 `Module: camp-pressure-board transition sequencer (split from T96)`
- T124 `Module: round ordering replay-stability checks (split from T96)`
- T125 `Module: camp five-slot durability model (split from T97)`
- T127 `Module: camp building effects set A (split from T99)`
- T128 `Module: camp building effects set B (split from T99)`
- T129 `Module: camp durability fatal preemption rule (split from T100)`
- T130 `Module: camp-fail settlement routing (split from T100)`
- T132 `Module: boss count and duration target validator (split from T101)`
- T133 `Module: boss elite-attack pressure resolver (split from T102)`
- T135 `Module: boss reveal delay pressure stacking (split from T103)`
- T136 `Module: hard-cap forced challenge preemption (split from T103)`
- T138 `Module: skip blocked-reason rule matrix (split from T104)`
- T139 `Module: objective publish-after-boss timing (split from T105)`
- T140 `Module: objective settle and endgame suppression (split from T105)`
- T143 `Module: final-boss victory adjudication branch (split from T107)`
- T144 `Module: camp-failure defeat adjudication branch (split from T107)`
- T145 `Module: campaign contract set completion (split from T109) integration pack`
- T147 `Module: campaign content schema extension (split from T110) integration pack`
- T148 `Module: campaign content quality gates closure (split from T110)`
- T149 `Module: campaign full-loop boss-win scenario (split from T111)`
- T150 `Module: campaign full-loop camp-fail scenario (split from T111)`
- T151 `Module: core assertion hard-gate closure (split from T112) integration pack`
- T152 `Module: UI assertion hard-gate closure (split from T112)`
- T153 `Module: R4 end-to-end explainability and replayability gate`
- T154 `Module: freeze policy guard for non-crash feedback suppression`
- T155 `Module: freeze change-control triplet gate`
- T156 `Module: signal XML documentation completeness gate (PH9-B2)`
- T157 `Module: CI signal compliance workflow hard-gate (PH9-B4) integration pack`
- T158 `Module: GDScript subscription lifecycle leak guard (PH9-B5) integration pack`
- T159 `Module: privacy-compliance document and policy gate (PH16-B4)`
- T160 `Module: logging-guidelines document and lint gate (PH16-B5)`
- T161 `Module: migration compatibility report automation gate (PH20-B3) integration pack`
- T162 `Module: signal compliance aggregator implementation (split from T157)`
- T163 `Module: signal compliance workflow hard-gate wiring (split from T157)`
- T165 `Module: GdUnit signal lifecycle leak fixtures (split from T158)`
- T166 `Module: migration compatibility report generator (split from T161)`
- T167 `Module: migration compatibility completeness validator (split from T161)`
- T168 `Module: migration compatibility CI hard-gate integration (split from T161)`
- T169 `Module: campaign contract additive set and versioning (split from T145)`
- T171 `Module: campaign content schema catalog extension (split from T147)`
- T172 `Module: campaign content cross-table constraints and bump rules (split from T147)`
- T173 `Module: core assertion hard-gate bundle A-013 to A-015 (split from T151)`
- T174 `Module: core assertion hard-gate bundle A-016 to A-019 (split from T151)`
- T175 `Module: core assertion hard-gate A-020 compatibility closure (split from T151)`
- T179 `Wire UI: Economy And Progression Panels`
- T180 `Wire UI: Config Audit And Migration Surfaces`
### Config Governance And Audit

- T31 `在 Game.Core 落地性能追踪库并接入 CI 性能门禁`
- T32 `Observability Autoload 与 Sentry Release Health Gate`
- T33 `Python 构建驱动脚本与 Windows Release Workflow 整合`
- T34 `分阶段发布（Canary/Stable）与回滚脚本骨架`
- T35 `项目级功能验收与文档整合骨架`
- T36 `事件命名统一迁移（game.* → core.*.*）`
- T37 `Game.Core Observability 客户端与结构化日志`
- T38 `代码重复率与圈复杂度门禁`
- T39 `性能 P95 与审计 JSONL 校验`
- T40 `Signal 健康度验证与安全相关测试门禁`

## 5. UI Wiring Matrix

| Feature | UI Surface | Player Action | System Response | Test Refs |
| --- | --- | --- | --- | --- |
| Entry And Bootstrap (T01, T11, T21, T85, T91, T92, T93, T101, T108, T131, T164, T170, T176, T177) | MainMenu / Boot Flow | Launch, continue, retry bootstrap, or enter a run | Show canonical startup path, valid continue behavior, and explicit startup failure recovery | `Tests.Godot/tests/Scenes/Smoke/test_main_scene_smoke.gd`, `Game.Core.Tests/Tasks/Task1EnvironmentEvidencePersistenceTests.cs`, `Game.Core.Tests/Tasks/Task1WindowsPlatformGateTests.cs`, `Game.Core.Tests/Tasks/Task1ToolchainVersionChecksTests.cs` |
| Core Loop State And Outcome (T03, T07, T08, T09, T10, T18, T19, T23, T24, T63, T78, T104, T106, T119, T120, T137, T141, T142) | HUD / Prompt / Outcome Surfaces | Play a run, observe timing, rewards, prompts, and terminal transitions | Render readable phase, timer, HP, reward, prompt, and win/lose state from runtime events | `Game.Core.Tests/Domain/CityTests.cs`, `Game.Core.Tests/Services/SanguoEconomyManagerTests.cs`, `Game.Core.Tests/Services/EventBusTests.cs`, `Tests.Godot/tests/UI/test_hud_scene.gd` |
| Combat Pressure And Interaction (T02, T04, T05, T06, T20, T22, T53, T59, T109, T126, T134, T146, T178) | Combat HUD / Pressure / Camera Feedback | Fight, observe pressure, targeting, pathing, and camera responses | Render enemy pressure, targeting, combat outcomes, and camera interaction without hidden state | `Game.Core.Tests/Domain/ValueObjects/CircularMapPositionTests.cs`, `Game.Core.Tests/Domain/SanguoPlayerTests.cs`, `Game.Core.Tests/Services/SanguoDiceServiceTests.cs`, `Game.Core.Tests/Services/SanguoTurnManagerTests.cs` |
| Economy Build And Progression (T12, T13, T14, T15, T16, T17) | Resource / Build / Progression Panels | Spend resources, place/build, train, upgrade, repair, or pick rewards | Render deterministic resource, build, queue, upgrade, and progression changes with clear invalid-state feedback | `Game.Core.Tests/Domain/SanguoPlayerTests.cs`, `Game.Core.Tests/Domain/CityTests.cs`, `Game.Core.Tests/Domain/SanguoBoardStateTests.cs`, `Game.Core.Tests/Services/SanguoEconomyManagerTests.cs` |
| Meta Systems And Platform (T25, T26, T27, T28, T29, T30, T41, T42, T43, T44, T45, T46, T47, T48, T49, T50, T51, T52, T54, T55, T56, T57, T58, T60, T61, T62, T64, T65, T66, T67, T68, T69, T70, T71, T72, T73, T74, T75, T76, T77, T79, T80, T81, T82, T83, T84, T86, T87, T88, T89, T90, T94, T95, T96, T97, T98, T99, T100, T102, T103, T105, T107, T110, T111, T112, T113, T114, T115, T116, T117, T118, T121, T122, T123, T124, T125, T127, T128, T129, T130, T132, T133, T135, T136, T138, T139, T140, T143, T144, T145, T147, T148, T149, T150, T151, T152, T153, T154, T155, T156, T157, T158, T159, T160, T161, T162, T163, T165, T166, T167, T168, T169, T171, T172, T173, T174, T175, T179, T180, [T194](#task-194-traceability)) | Settings / Save / Meta Surfaces | Save, load, localize, tune audio, or inspect platform/runtime status | Render persistence, localization, audio, performance, and platform status on governed player-visible surfaces | `Game.Core.Tests/Tasks/Task25AiTests.cs`, `Game.Core.Tests/Utilities/NoGodotDependencyTests.cs`, `Game.Core.Tests/Services/PlayerEliminationTests.cs`, `Tests.Godot/tests/Adapters/Config/test_audio_player_adapter_nodes.gd` |
| Config Governance And Audit (T31, T32, T33, T34, T35, T36, T37, T38, T39, T40) | Config Summary / Audit / Migration Surfaces | Inspect config state, validation, governance, migration, and report metadata | Render active config, schema status, fallback policy, migration status, and audit metadata without relying on logs-only evidence | `Game.Core.Tests/Tasks/Task31PerformanceGateTests.cs`, `Game.Core.Tests/Tasks/Task32RequirementsTests.cs`, `Tests.Godot/tests/Adapters/Db/test_db_handle_release.gd`, `Game.Core.Tests/Domain/ValueObjects/HealthTests.cs` |

## 6. Screen And Surface Requirements

### Entry And Bootstrap
- Audience: player-facing.
- Empty state: Save header remains sufficient to explain and reproduce the run context without inspecting transient UI state after save/load.
- Failure state: Campaign runmode isolation must be explicitly defined and verified with observable boundaries: entering campaign runmode applies only the intended isolation behavior, and non-campaign paths must not be isolated by this split.
- Completion result: UI 日期显示应清晰表达年/月/日；当游戏日期连续变化多次时，每一次日期变化都能在可观察层面反映为日期文本的对应更新，并且日期文本始终反映最新游戏日期（不出现回退为旧值或停滞不更新等可观察异常）。

### Core Loop State And Outcome
- Audience: player-facing.
- Empty state: Integration closure must explicitly verify deterministic draft behavior: under the same input conditions and seed, RewardDraftEngine evidence from tasks 119 and 120 must produce repeatable draft outcomes; missing deterministic evidence keeps task 78 open.
- Failure state: Minimum 'important events' set for this task: core.sanguo.dice.rolled + core.sanguo.city.bought; log retains history across hide/show; invalid/malformed JSON payloads do not crash and do not append misleading log entries.
- Completion result: 包含城池占有状态显示的 UI 场景与控件在 headless 冒烟测试中可被实例化并加载完成（无崩溃/无报错），且界面上存在用于呈现“占有状态”的可见元素。

### Combat Pressure And Interaction
- Audience: player-facing.
- Empty state: GdUnit4: Provide and run a scene/UI test that verifies tile name is visible and falls back to nameKey when i18n is missing.
- Failure state: xUnit: tiles[] must be non-empty (length>=1) so that tiles[0] exists; otherwise the map definition is invalid.
- Completion result: xUnit: tiles[] must be non-empty (length>=1) so that tiles[0] exists; otherwise the map definition is invalid.

### Economy Build And Progression
- Audience: player-facing.
- Empty state: show no active economy state until owned runtime data is available.
- Failure state: 回合循环正确处理出局者：已出局 NPC 会从后续轮转中跳过且不再行动；真人玩家一旦出局，回合循环立即停止并触发游戏结束；游戏结束后进一步调用 AdvanceTurn/AdvanceTurnAsync 必须被拒绝（抛出 InvalidOperationException）且不得推进日期/轮转行动者/发布新事件；NPC 出局后其状态锁定，且其已占领城池被释放为无人占领。
- Completion result: player can read deterministic resource and progression outcomes from UI state.

### Meta Systems And Platform
- Audience: player-facing or mixed.
- Empty state: 在 gameplay 流程中，玩家于 TurnPhase.BeforeRoll 阶段每回合最多只能成功打出 1 张行动卡；同回合第二次尝试必须被拒绝且不产生任何 multiplier_step_delta/效果输出，并与 back 视图的窗口锁死语义一致。
- Failure state: 在回合/循环结算时，若真人玩家因资金不足以支付全额过路费而出局（破产结算）：其剩余资金必须转移给收款方，玩家资金归零并标记出局；立即进入 GameOver 且后续回合推进必须被拒绝（再次调用 AdvanceTurnAsync 抛出 InvalidOperationException，且消息包含 "GameOver"）。若 NPC 因资金不足以支付全额过路费而出局：同样进行破产结算后退出本局并从后续轮转中移除（状态锁定，后续不会再成为 ActivePlayerId），其已占领城池状态变更为无人占领。
- Completion result: 开始游戏启动失败时（例如地图配置加载失败），主菜单必须恢复为可交互状态并显示可观测错误提示（例如 StatusLabel 显示“Start failed”），避免出现“菜单消失但游戏未开始”的死路。

### Config Governance And Audit
- Audience: operator-facing or mixed.
- Empty state: show no active run state until runtime data is available.
- Failure state: `quality_gates.py` 在统一门禁流程中读取上述两份报告并应用 Phase-13 约定的阈值规则输出 PASS/FAIL（示例：Dup% ≤ 2%，最大圈复杂度 ≤ 10，平均圈复杂度 ≤ 5）；当任一报告缺失/不可解析/缺少必要字段时必须判定为 FAIL，并输出可定位原因的错误信息。
- Completion result: operator or player can inspect config, validation, migration, and audit state from governed surfaces.

- Operator-facing read surfaces are allowed when player-facing interaction is not appropriate.

## 7. Screen-Level Contracts

### 7.1 MainMenu And Boot Flow
- Covered slice: Entry And Bootstrap.
- Must show: start, continue, retry bootstrap, and platform-start validation state.
- Must not hide: startup failure, continue-gate denial, or export/runtime startup issues behind logs only.
- Validation focus: boot path, continue gate, retry flow, and startup validation evidence.

### 7.2 Runtime HUD And Outcome Surfaces
- Covered slice: Core Loop State And Outcome.
- Must show: phase, timer, HP, prompts, reward entry, invalid-action prompts, speed state, and terminal outcomes.
- Must not hide: terminal or prompt state transitions that occur without visible HUD or outcome feedback.
- Validation focus: HUD state changes, prompts, reward visibility, and win/lose transitions.

### 7.3 Combat Pressure And Interaction Surfaces
- Covered slice: Combat Pressure And Interaction.
- Must show: pressure, spawn cadence, targeting, pathing fallback, combat resolution, and camera interaction state.
- Must not hide: combat pressure or targeting changes that only appear in logs or traces.
- Validation focus: combat feedback, pressure visibility, pathing fallback evidence, and camera interaction smoke checks.

### 7.4 Economy And Progression Panels
- Covered slice: Economy Build And Progression.
- Must show: resource totals, build placement state, queue state, upgrade/repair state, tech state, and progression results.
- Must not hide: invalid spend/build/progression transitions without governed feedback.
- Validation focus: resource determinism, build validation, queue behavior, and progression surface evidence.

### 7.5 Save, Settings, And Meta Surfaces
- Covered slice: Meta Systems And Platform.
- Must show: save/load status, cloud state, localization state, audio state, performance state, and platform/runtime status.
- Must not hide: persistence or settings failures that are only visible in lower-level logs.
- Validation focus: save/load flow, cloud sync, localization/audio controls, and platform status visibility.

### 7.6 Config Audit And Migration Surfaces
- Covered slice: Config Governance And Audit.
- Must show: active config, schema status, fallback status, migration state, config audit metadata, and report metadata.
- Must not hide: validation, fallback, or migration outcomes that do not surface on a governed read surface.
- Validation focus: config validation, governance, migration, and audit metadata evidence.

## 8. Screen State Matrix

| Screen Group | Entry State | Interaction State | Failure State | Recovery / Exit |
| --- | --- | --- | --- | --- |
| MainMenu And Boot Flow | show start, continue, and startup readiness before any run begins. | allow start, continue, retry bootstrap, and acknowledgement of startup state. | show startup failure, continue denial, or runtime-start validation failure explicitly. | retry bootstrap, acknowledge, or return to menu. |
| Runtime HUD And Outcome Surfaces | show no active run state until runtime data is available. | show phase, timer, HP, prompts, reward entry, invalid-action prompts, speed state, and terminal outcomes. | show prompt/terminal failure state instead of leaving the HUD stale or blank. | acknowledge outcome, continue the run, or return to menu. |
| Combat Pressure And Interaction Surfaces | show no active combat state until combat data and camera ownership are ready. | show pressure, targeting, pathing fallback, combat resolution, and camera interaction state. | show blocked targeting, missing path, or hidden pressure failure explicitly. | retry, acknowledge, or return to the governed combat-ready surface. |
| Economy And Progression Panels | show no owned economy state until resource/build/progression data is available. | show resource totals, build placement state, queue state, upgrade/repair state, tech state, and progression results. | show invalid spend/build/progression state without mutating deterministic ownership silently. | acknowledge invalid state, retry the action, or return to menu. |
| Save, Settings, And Meta Surfaces | show no persisted/platform state until save, cloud, or settings services are available. | show save/load status, cloud state, localization state, audio state, performance state, and platform/runtime status. | show persistence or settings failure instead of only writing low-level logs. | retry, acknowledge, or return to menu. |
| Config Audit And Migration Surfaces | show no active run state until config, validation, and migration data is available. | show active config, schema status, fallback status, migration state, config audit metadata, and report metadata. | show validation, fallback, or migration failure on the governed read surface. | retry, acknowledge, or return to menu after review. |

## 9. Scope And Non-Goals

- Chapter 7 covers UI or governed visible-surface ownership for every completed task in `.taskmaster/tasks/tasks.json`.
- It does not require final production polish, animation, skinning, or marketing-grade copy.

### 9.1 In Scope

- Surface ownership for startup, loop, combat, economy, meta, and governance capabilities.
- Empty state, failure state, and completion state for each major slice.
- Task alignment and validation references back to completed backlog items.

### 9.2 Non-Goals
- Final UX polish, visual theming, animation tuning, and cosmetic-only layout work.
- Replacing source-of-truth task status outside `.taskmaster/tasks/tasks.json`.

## 10. Unwired UI Feature List

- Entry And Bootstrap: define concrete scene ownership, empty/failure states, and validation evidence for T01, T11, T21, T85, T91, T92, T93, T101, T108, T131, T164, T170, T176, T177.
- Core Loop State And Outcome: define concrete scene ownership, empty/failure states, and validation evidence for T03, T07, T08, T09, T10, T18, T19, T23, T24, T63, T78, T104, T106, T119, T120, T137, T141, T142.
- Combat Pressure And Interaction: define concrete scene ownership, empty/failure states, and validation evidence for T02, T04, T05, T06, T20, T22, T53, T59, T109, T126, T134, T146, T178.
- Economy Build And Progression: define concrete scene ownership, empty/failure states, and validation evidence for T12, T13, T14, T15, T16, T17.
- Meta Systems And Platform: define concrete scene ownership, empty/failure states, and validation evidence for T25, T26, T27, T28, T29, T30, T41, T42, T43, T44, T45, T46, T47, T48, T49, T50, T51, T52, T54, T55, T56, T57, T58, T60, T61, T62, T64, T65, T66, T67, T68, T69, T70, T71, T72, T73, T74, T75, T76, T77, T79, T80, T81, T82, T83, T84, T86, T87, T88, T89, T90, T94, T95, T96, T97, T98, T99, T100, T102, T103, T105, T107, T110, T111, T112, T113, T114, T115, T116, T117, T118, T121, T122, T123, T124, T125, T127, T128, T129, T130, T132, T133, T135, T136, T138, T139, T140, T143, T144, T145, T147, T148, T149, T150, T151, T152, T153, T154, T155, T156, T157, T158, T159, T160, T161, T162, T163, T165, T166, T167, T168, T169, T171, T172, T173, T174, T175, T179, T180, [T194](#task-194-traceability).
- Config Governance And Audit: define concrete scene ownership, empty/failure states, and validation evidence for T31, T32, T33, T34, T35, T36, T37, T38, T39, T40.

## 11. Next UI Wiring Task Candidates

### Candidate Slice MainMenu And Boot Flow

- Matrix link: `## 5. UI Wiring Matrix row Entry And Bootstrap (T01, T11, T21, T85, T91, T92, T93, T101, T108, T131, T164, T170, T176, T177)`.
- Scope: T01, T11, T21, T85, T91, T92, T93, T101, T108, T131, T164, T170, T176, T177.
- UI entry: MainMenu / Boot Flow.
- Candidate type: task-shaped UI wiring spec.
- Screen group: MainMenu And Boot Flow.
- Player action: Launch, continue, retry bootstrap, or enter a run.
- System response: Show canonical startup path, valid continue behavior, and explicit startup failure recovery.
- Empty state: Save header remains sufficient to explain and reproduce the run context without inspecting transient UI state after save/load.
- Failure state: Campaign runmode isolation must be explicitly defined and verified with observable boundaries: entering campaign runmode applies only the intended isolation behavior, and non-campaign paths must not be isolated by this split.
- Completion result: UI 日期显示应清晰表达年/月/日；当游戏日期连续变化多次时，每一次日期变化都能在可观察层面反映为日期文本的对应更新，并且日期文本始终反映最新游戏日期（不出现回退为旧值或停滞不更新等可观察异常）。
- Requirement IDs: `Add requirement mapping before implementation.`
- Validation artifact targets: `Add artifact target before implementation.`
- Suggested standalone surfaces: `MainMenu`, `BootStatusPanel`, `ContinueGateDialog`.
- Test refs: `Tests.Godot/tests/Scenes/Smoke/test_main_scene_smoke.gd`, `Game.Core.Tests/Tasks/Task1EnvironmentEvidencePersistenceTests.cs`, `Game.Core.Tests/Tasks/Task1WindowsPlatformGateTests.cs`, `Game.Core.Tests/Tasks/Task1ToolchainVersionChecksTests.cs`.
### Candidate Slice Runtime HUD And Outcome Surfaces

- Matrix link: `## 5. UI Wiring Matrix row Core Loop State And Outcome (T03, T07, T08, T09, T10, T18, T19, T23, T24, T63, T78, T104, T106, T119, T120, T137, T141, T142)`.
- Scope: T03, T07, T08, T09, T10, T18, T19, T23, T24, T63, T78, T104, T106, T119, T120, T137, T141, T142.
- UI entry: HUD / Prompt / Outcome Surfaces.
- Candidate type: task-shaped UI wiring spec.
- Screen group: Runtime HUD And Outcome Surfaces.
- Player action: Play a run, observe timing, rewards, prompts, and terminal transitions.
- System response: Render readable phase, timer, HP, reward, prompt, and win/lose state from runtime events.
- Empty state: Integration closure must explicitly verify deterministic draft behavior: under the same input conditions and seed, RewardDraftEngine evidence from tasks 119 and 120 must produce repeatable draft outcomes; missing deterministic evidence keeps task 78 open.
- Failure state: Minimum 'important events' set for this task: core.sanguo.dice.rolled + core.sanguo.city.bought; log retains history across hide/show; invalid/malformed JSON payloads do not crash and do not append misleading log entries.
- Completion result: 包含城池占有状态显示的 UI 场景与控件在 headless 冒烟测试中可被实例化并加载完成（无崩溃/无报错），且界面上存在用于呈现“占有状态”的可见元素。
- Requirement IDs: `Add requirement mapping before implementation.`
- Validation artifact targets: `Add artifact target before implementation.`
- Suggested standalone surfaces: `RuntimeHud`, `OutcomePanel`, `RuntimePromptPanel`.
- Test refs: `Game.Core.Tests/Domain/CityTests.cs`, `Game.Core.Tests/Services/SanguoEconomyManagerTests.cs`, `Game.Core.Tests/Services/EventBusTests.cs`, `Tests.Godot/tests/UI/test_hud_scene.gd`.
### Candidate Slice Combat Pressure And Interaction Surfaces

- Matrix link: `## 5. UI Wiring Matrix row Combat Pressure And Interaction (T02, T04, T05, T06, T20, T22, T53, T59, T109, T126, T134, T146, T178)`.
- Scope: T02, T04, T05, T06, T20, T22, T53, T59, T109, T126, T134, T146, T178.
- UI entry: Combat HUD / Pressure / Camera Feedback.
- Candidate type: task-shaped UI wiring spec.
- Screen group: Combat Pressure And Interaction Surfaces.
- Player action: Fight, observe pressure, targeting, pathing, and camera responses.
- System response: Render enemy pressure, targeting, combat outcomes, and camera interaction without hidden state.
- Empty state: GdUnit4: Provide and run a scene/UI test that verifies tile name is visible and falls back to nameKey when i18n is missing.
- Failure state: xUnit: tiles[] must be non-empty (length>=1) so that tiles[0] exists; otherwise the map definition is invalid.
- Completion result: xUnit: tiles[] must be non-empty (length>=1) so that tiles[0] exists; otherwise the map definition is invalid.
- Requirement IDs: `Add requirement mapping before implementation.`
- Validation artifact targets: `Add artifact target before implementation.`
- Suggested standalone surfaces: `CombatHud`, `PressurePanel`, `CameraControlOverlay`.
- Test refs: `Game.Core.Tests/Domain/ValueObjects/CircularMapPositionTests.cs`, `Game.Core.Tests/Domain/SanguoPlayerTests.cs`, `Game.Core.Tests/Services/SanguoDiceServiceTests.cs`, `Game.Core.Tests/Services/SanguoTurnManagerTests.cs`.
### Candidate Slice Economy And Progression Panels

- Matrix link: `## 5. UI Wiring Matrix row Economy Build And Progression (T12, T13, T14, T15, T16, T17)`.
- Scope: T12, T13, T14, T15, T16, T17.
- UI entry: Resource / Build / Progression Panels.
- Candidate type: task-shaped UI wiring spec.
- Screen group: Economy And Progression Panels.
- Player action: Spend resources, place/build, train, upgrade, repair, or pick rewards.
- System response: Render deterministic resource, build, queue, upgrade, and progression changes with clear invalid-state feedback.
- Empty state: show no active economy state until owned runtime data is available.
- Failure state: 回合循环正确处理出局者：已出局 NPC 会从后续轮转中跳过且不再行动；真人玩家一旦出局，回合循环立即停止并触发游戏结束；游戏结束后进一步调用 AdvanceTurn/AdvanceTurnAsync 必须被拒绝（抛出 InvalidOperationException）且不得推进日期/轮转行动者/发布新事件；NPC 出局后其状态锁定，且其已占领城池被释放为无人占领。
- Completion result: player can read deterministic resource and progression outcomes from UI state.
- Requirement IDs: `Add requirement mapping before implementation.`
- Validation artifact targets: `Add artifact target before implementation.`
- Suggested standalone surfaces: `ResourcePanel`, `BuildPanel`, `ProgressionPanel`.
- Test refs: `Game.Core.Tests/Domain/SanguoPlayerTests.cs`, `Game.Core.Tests/Domain/CityTests.cs`, `Game.Core.Tests/Domain/SanguoBoardStateTests.cs`, `Game.Core.Tests/Services/SanguoEconomyManagerTests.cs`.
### Candidate Slice Save, Settings, And Meta Surfaces

- Matrix link: `## 5. UI Wiring Matrix row Meta Systems And Platform (..., T180, T194)` with shaped spec target `[T194](#task-194-traceability)`.
- Scope: T25, T26, T27, T28, T29, T30, T41, T42, T43, T44, T45, T46, T47, T48, T49, T50, T51, T52, T54, T55, T56, T57, T58, T60, T61, T62, T64, T65, T66, T67, T68, T69, T70, T71, T72, T73, T74, T75, T76, T77, T79, T80, T81, T82, T83, T84, T86, T87, T88, T89, T90, T94, T95, T96, T97, T98, T99, T100, T102, T103, T105, T107, T110, T111, T112, T113, T114, T115, T116, T117, T118, T121, T122, T123, T124, T125, T127, T128, T129, T130, T132, T133, T135, T136, T138, T139, T140, T143, T144, T145, T147, T148, T149, T150, T151, T152, T153, T154, T155, T156, T157, T158, T159, T160, T161, T162, T163, T165, T166, T167, T168, T169, T171, T172, T173, T174, T175, T179, T180, T194.
- UI entry: Settings / Save / Meta Surfaces.
- Candidate type: task-shaped UI wiring spec.
- Screen group: Save, Settings, And Meta Surfaces.
- Player action: Save, load, localize, tune audio, or inspect platform/runtime status.
- System response: Render persistence, localization, audio, performance, and platform status on governed player-visible surfaces.
- Empty state: 在 gameplay 流程中，玩家于 TurnPhase.BeforeRoll 阶段每回合最多只能成功打出 1 张行动卡；同回合第二次尝试必须被拒绝且不产生任何 multiplier_step_delta/效果输出，并与 back 视图的窗口锁死语义一致。
- Failure state: 在回合/循环结算时，若真人玩家因资金不足以支付全额过路费而出局（破产结算）：其剩余资金必须转移给收款方，玩家资金归零并标记出局；立即进入 GameOver 且后续回合推进必须被拒绝（再次调用 AdvanceTurnAsync 抛出 InvalidOperationException，且消息包含 "GameOver"）。若 NPC 因资金不足以支付全额过路费而出局：同样进行破产结算后退出本局并从后续轮转中移除（状态锁定，后续不会再成为 ActivePlayerId），其已占领城池状态变更为无人占领。
- Completion result: 开始游戏启动失败时（例如地图配置加载失败），主菜单必须恢复为可交互状态并显示可观测错误提示（例如 StatusLabel 显示“Start failed”），避免出现“菜单消失但游戏未开始”的死路。
- Requirement IDs: `REQ-5b357e8530f4`, `REQ-509d28ebf0f4`, `REQ-19e5fff8da4f`, `REQ-792bd66bd304`.
- Validation artifact targets: `Tests.Godot/tests/Adapters/Config/test_audio_player_adapter_nodes.gd`, `Tests.Godot/tests/Adapters/Db/test_db_transactions_and_pragmas.gd`, `Tests.Godot/tests/Adapters/Db/test_fk_constraints_and_cascade.gd`, `Tests.Godot/tests/Adapters/Db/test_inventory_merge_and_clear_cross_restart.gd`, `Tests.Godot/tests/Adapters/test_data_store_adapter.gd`, `Tests.Godot/tests/Adapters/test_event_bus_adapter.gd`, `Game.Core.Tests/Utilities/NoGodotDependencyTests.cs`.
- Suggested standalone surfaces: `SettingsMenu`, `SavePanel`, `RunSummaryPanel`.
- Test refs: `Game.Core.Tests/Tasks/Task25AiTests.cs`, `Game.Core.Tests/Utilities/NoGodotDependencyTests.cs`, `Game.Core.Tests/Services/PlayerEliminationTests.cs`, `Tests.Godot/tests/Adapters/Config/test_audio_player_adapter_nodes.gd`.
### Candidate Slice Config Audit And Migration Surfaces

- Matrix link: `## 5. UI Wiring Matrix row Config Governance And Audit (T31, T32, T33, T34, T35, T36, T37, T38, T39, T40)`.
- Scope: T31, T32, T33, T34, T35, T36, T37, T38, T39, T40.
- UI entry: Config Summary / Audit / Migration Surfaces.
- Candidate type: task-shaped UI wiring spec.
- Screen group: Config Audit And Migration Surfaces.
- Player action: Inspect config state, validation, governance, migration, and report metadata.
- System response: Render active config, schema status, fallback policy, migration status, and audit metadata without relying on logs-only evidence.
- Empty state: show no active run state until runtime data is available.
- Failure state: `quality_gates.py` 在统一门禁流程中读取上述两份报告并应用 Phase-13 约定的阈值规则输出 PASS/FAIL（示例：Dup% ≤ 2%，最大圈复杂度 ≤ 10，平均圈复杂度 ≤ 5）；当任一报告缺失/不可解析/缺少必要字段时必须判定为 FAIL，并输出可定位原因的错误信息。
- Completion result: operator or player can inspect config, validation, migration, and audit state from governed surfaces.
- Requirement IDs: `Add requirement mapping before implementation.`
- Validation artifact targets: `Add artifact target before implementation.`
- Suggested standalone surfaces: `ConfigAuditPanel`, `MigrationStatusDialog`, `ReportMetadataPanel`.
- Test refs: `Game.Core.Tests/Tasks/Task31PerformanceGateTests.cs`, `Game.Core.Tests/Tasks/Task32RequirementsTests.cs`, `Tests.Godot/tests/Adapters/Db/test_db_handle_release.gd`, `Game.Core.Tests/Domain/ValueObjects/HealthTests.cs`.

## 12. Copy And Accessibility

- Visible text should remain explicit and actionable.
- Failure messages must tell the player or operator what happened and what to do next.
- Do not rely on color only to convey terminal, invalid, or route-selection state.

## 13. Test And Acceptance

- Chapter 7 validation must keep `## 5. UI Wiring Matrix`, `## 10. Unwired UI Feature List`, and `## 11. Next UI Wiring Task Candidates` intact.
- Evidence should resolve back to xUnit, GdUnit, smoke, or CI outputs already referenced by task views.
- Any new UI slice should add or name a concrete validation path before implementation.


## 14. Task Alignment

- Completed task count currently expected by Chapter 7: 180.
- Chapter 7 uses `.taskmaster/tasks/tasks.json` as the completion-state SSoT.
- View files remain enrichment sources for test refs, acceptance, labels, and contract context.

## 15. Task 187 Traceability

- Task scope chapters: CH01, CH07.
- Governing ADR: ADR-0005.
- Overlay traceability:
  - docs/architecture/overlays/PRD-SANGUO-V4/08/_index.md
  - docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md
  - docs/architecture/overlays/PRD-SANGUO-V3/08/08-business-acceptance-scenarios.md
  - docs/architecture/overlays/PRD-SANGUO-V3/08/ACCEPTANCE_CHECKLIST.md
- Chapter 3.8 validator evidence is required after task-view updates and must remain traceable in CI artifacts.

## 16. Task 194 Traceability

- Matrix row: [Meta Systems And Platform](#5-ui-wiring-matrix).
- Shaped spec link: `[T194](#task-194-traceability)` resolves from the matrix row to this task-specific evidence target.
- Task scope chapters: CH01, CH05, CH06, CH07.
- Governing ADRs: ADR-0007, ADR-0024.
- Requirement IDs: REQ-5b357e8530f4, REQ-509d28ebf0f4, REQ-19e5fff8da4f, REQ-792bd66bd304.
- Overlay traceability:
  - docs/architecture/overlays/PRD-SANGUO-T2/08/08-contracts-taskmap-t50-t65.md
  - docs/architecture/overlays/PRD-SANGUO-T2/08/08-t51-economy-multipliers-and-applied-multipliers.md
  - docs/architecture/overlays/PRD-SANGUO-T2/08/08-t52-turn-window-and-event-ordering.md
  - docs/architecture/overlays/PRD-SANGUO-T2/08/08-t60-game-end-and-settlement.md
- Validation artifact targets:
  - Tests.Godot/tests/Adapters/Config/test_audio_player_adapter_nodes.gd
  - Tests.Godot/tests/Adapters/Db/test_db_transactions_and_pragmas.gd
  - Tests.Godot/tests/Adapters/Db/test_fk_constraints_and_cascade.gd
  - Tests.Godot/tests/Adapters/Db/test_inventory_merge_and_clear_cross_restart.gd
  - Tests.Godot/tests/Adapters/test_data_store_adapter.gd
  - Tests.Godot/tests/Adapters/test_event_bus_adapter.gd
  - Game.Core.Tests/Utilities/NoGodotDependencyTests.cs
  - Tests.Godot/tests/Integration/test_quality_gates_gdunit_adapters_security_aggregation.gd
- Chapter 3 coverage audit and Chapter 3.8 triplet baseline validator evidence must be recorded in `logs/**` after task-view updates.
