---
PRD-ID: PRD-SANGUO-T2
Title: 三国大富翁闭环事件契约（Sanguo GameLoop Events）
ADR-Refs:
  - ADR-0004
  - ADR-0005
  - ADR-0020
  - ADR-0021
Test-Refs:
  - Game.Core.Tests/Domain/SanguoContractsTests.cs
  - Game.Core.Tests/Domain/SanguoContractInstantiationTests.cs
Contracts-Refs:
  - Game.Core/Contracts/Sanguo/BoardEvents.cs
  - Game.Core/Contracts/Sanguo/GameEvents.cs
  - Game.Core/Contracts/Sanguo/EconomyEvents.cs
  - Game.Core/Contracts/Sanguo/PlayerAndAiEvents.cs
Status: Accepted
---

本页登记 T2 最小可玩闭环中“领域事件契约”的落盘位置与验收口径。事件列表与触发时机的业务含义请以纵切文档为准，本页只负责契约 SSoT 的引用与对齐。

## 契约落盘位置（SSoT）

- 棋盘/移动/掷骰：`Game.Core/Contracts/Sanguo/BoardEvents.cs`
- 回合推进/存档/结束：`Game.Core/Contracts/Sanguo/GameEvents.cs`
- 经济结算/调价/买地/付费：`Game.Core/Contracts/Sanguo/EconomyEvents.cs`
- 玩家状态/AI 决策：`Game.Core/Contracts/Sanguo/PlayerAndAiEvents.cs`

## 与纵切文档的关系（引用）

- 业务闭环与任务映射：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-功能纵切-T2-三国大富翁闭环.md`
- 城池所有权与出局不变式：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-t2-city-ownership-model.md`

## 验收要点（就地）

- EventType 不漂移：`Game.Core.Tests/Domain/SanguoContractsTests.cs`
- 事件 record 可构造且字段语义清晰：`Game.Core.Tests/Domain/SanguoContractInstantiationTests.cs`
