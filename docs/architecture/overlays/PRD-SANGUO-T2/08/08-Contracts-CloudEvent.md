---
PRD-ID: PRD-SANGUO-T2
Title: DomainEvent（CloudEvents-like）契约与字段约束
ADR-Refs:
  - ADR-0004
  - ADR-0005
  - ADR-0019
  - ADR-0020
  - ADR-0021
Arch-Refs:
  - CH01
  - CH03
Test-Refs:
  - Game.Core.Tests/Services/EventBusTests.cs
Contracts-Refs:
  - Game.Core/Contracts/DomainEvent.cs
  - Game.Core/Contracts/IEventData.cs
  - Game.Core/Contracts/JsonEventData.cs
Status: Accepted
---

本页记录本仓库在 T2 功能纵切中使用的“领域事件封装（CloudEvents-like）”契约口径，用于跨层/跨模块通信的一致性约束。

## 适用范围

- 仅用于 Godot + C#（Windows only）项目内的事件封装与字段约定。
- 事件类型命名口径以 ADR-0004 为准；本页不复制阈值/策略，只登记落盘位置与验收要点。

## 契约与落盘位置（SSoT）

- 事件信封（Envelope）：`Game.Core/Contracts/DomainEvent.cs`
- 事件载荷（Payload）类型约束：`Game.Core/Contracts/IEventData.cs`
- 安全载荷实现（JSON 载荷/元素）：`Game.Core/Contracts/JsonEventData.cs`

## 字段约束（与 CloudEvents 1.0 对齐的最小子集）

- `Type`：事件类型（CloudEvents type），必须来自稳定常量/契约（禁止魔法字符串散落）。
- `Source`：事件来源（CloudEvents source），建议使用组件/类名或稳定标识。
- `Id`：事件唯一 ID，统一使用 `Guid.NewGuid().ToString("N")` 生成，避免碰撞与格式漂移。
- `Timestamp`：事件发生时间，统一使用 UTC。
- `Data`：可空；非空时必须实现 `IEventData`（避免 `object/dynamic` 注入面）。

## 验收要点（就地）

- `EventBus` 能发布/订阅 `DomainEvent` 并保持异常可观测（见 `Game.Core.Tests/Services/EventBusTests.cs`）。
- 新增/调整事件载荷时，不得引入 Godot API 类型到 Contracts；仅使用 BCL 类型与 `System.Text.Json`。
