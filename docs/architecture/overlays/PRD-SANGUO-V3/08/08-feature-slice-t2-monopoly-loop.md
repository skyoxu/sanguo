---
PRD-ID: PRD-SANGUO-V3
Title: V3 战役主循环（兼容文件名）
Status: Draft
ADR-Refs:
  - ADR-0004
  - ADR-0005
Arch-Refs:
  - CH01
  - CH04
  - CH06
Test-Refs:
  - Game.Core.Tests/Tasks/Task52TurnPhaseWindowTests.cs
  - Game.Core.Tests/Tasks/Task60GameEndEventContractTests.cs
---

# V3 战役主循环

> 兼容文件名说明：为降低 `tasks.json / tasks_back.json / tasks_gameplay.json` 的回链迁移成本，本目录沿用一部分旧文件名；文件内容以 V3 战役模式为准。

本页是 V3 战役模式的总览页，对应 traceability matrix 中的主循环 engine blueprint。

## 最小闭环

1. 新游戏选择 `RunMode=Campaign`
2. 进入营地阶段
3. 处理保存重试、Boss 压力/Boss 分支、随机任务发布
4. 进入棋盘阶段
5. 回到营地或触发终局

## Engine 级边界

- `CampaignRuleEngine`
  - 负责 RunMode 分流、胜负条件、规则隔离
- `CampLifecycleEngine`
  - 负责营地内顺序、离营边界、持久告警
- `BossPressureEngine`
  - 负责骰子、揭示、延迟增压、强制挑战
- `RandomObjectiveEngine`
  - 负责发布、结算、跳过
- `RewardDraftEngine`
  - 负责确定性 3 选 1 奖励

## V3 相对 T2 的关键变化

- 主循环不再是单纯“掷骰 -> 移动 -> 买地/付费”
- 进入棋盘前必须经过营地与 Boss 分支
- 游戏结束不再只看旧的淘汰/破产原因

## 对应任务

- T74~T79: engine integration pack
- T153: explainability/replayability gate
- T158/T164/T165: runtime signal subscription lifecycle guard

## Runtime Ownership Detail

| Task | Concern | Current extant EventType set |
|---|---|---|
| T153 | R4 explainability and replayability gate | `core.sanguo.game.started`, `core.sanguo.game.saved`, `core.sanguo.game.loaded`, `core.sanguo.game.turn.advanced`, `core.sanguo.boss.challenge.prompted`, `core.sanguo.random_event.applied`, `core.sanguo.action_card.played`, `core.sanguo.loot.granted`, `core.sanguo.objective.skipped`, `core.sanguo.game.ended`; deterministic scenario gate now binds `contractRefs` to landed replay/explainability runtime events while contract semantics still route through `08-Contracts-Sanguo-GameLoop-Events.md` |
| T158 | GDScript subscription lifecycle leak guard integration pack | `core.sanguo.game.turn.started`, `core.sanguo.game.turn.ended` |
| T164 | runtime signal subscription lifecycle guard | `core.sanguo.game.turn.started`, `core.sanguo.game.turn.ended` |
| T165 | GdUnit signal lifecycle leak fixtures | `core.sanguo.game.turn.started`, `core.sanguo.game.turn.ended` |

## 设计约束

- 逻辑阶段切换必须统一经过 state machine / sequencer
- 运行时信号必须有明确订阅与释放边界，不能靠场景销毁碰运气
- 主循环解释链和 replay 证据必须来自同一条事件序列
