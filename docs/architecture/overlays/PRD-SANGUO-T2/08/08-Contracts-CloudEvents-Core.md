---
PRD-ID: PRD-SANGUO-T2
Title: CloudEvents Core 口径（EventType 常量化与关联字段）
ADR-Refs:
  - ADR-0004
  - ADR-0005
  - ADR-0020
  - ADR-0021
Arch-Refs:
  - CH01
  - CH03
Test-Refs:
  - Game.Core.Tests/Domain/SanguoContractsTests.cs
Contracts-Refs:
  - Game.Core/Contracts/Sanguo/BoardEvents.cs
  - Game.Core/Contracts/Sanguo/GameEvents.cs
  - Game.Core/Contracts/Sanguo/EconomyEvents.cs
  - Game.Core/Contracts/Sanguo/PlayerAndAiEvents.cs
Status: Accepted
---

本页定义 T2 功能纵切中“领域事件类型与关联字段”的统一口径，确保事件命名、字段形状与测试引用保持一致（仅引用 ADR 口径，不复制阈值/策略）。

## EventType 常量化（必须）

- 每个领域事件必须定义 `public const string EventType = "..."`。
- EventType 必须满足 ADR-0004 命名规范（本仓库 T2 统一使用 `core.sanguo.*` 前缀）。
- 事件类型的断言必须在 xUnit 中覆盖（至少覆盖关键闭环事件的 EventType 值）。

示例（引用）：`Game.Core/Contracts/Sanguo/**` 中每个事件 record 的 `EventType` 常量。

## 关联字段（推荐一致化）

为保证可回放、可追踪与排障一致性，T2 领域事件建议统一携带以下字段（按实际事件场景取舍，但在 Contracts 中必须明确）：

- `OccurredAt`：发生时间（UTC，`DateTimeOffset`）。
- `CorrelationId`：同一用户动作/同一回合链路的关联 ID。
- `CausationId`：上游触发事件 ID（可空）。

## 验收要点（就地）

- `Game.Core.Tests/Domain/SanguoContractsTests.cs` 至少验证关键事件的 `EventType` 常量值不漂移。
