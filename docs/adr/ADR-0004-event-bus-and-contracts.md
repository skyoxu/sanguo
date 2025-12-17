---
ADR-ID: ADR-0004
title: 事件总线与契约（CloudEvents 风格）- Godot + C# 变体
status: Accepted
decision-time: '2025-12-16'
deciders: [架构团队, 开发团队]
archRefs: [CH04, CH05, CH06]
verification:
  - path: Game.Core/Contracts/DomainEvent.cs
    assert: DomainEvent contains minimal CloudEvents-like attributes (type/source/id/time/specversion)
  - path: Game.Core/Services/EventBus.cs
    assert: IEventBus + in-memory implementation exist and are unit-testable
  - path: Game.Godot/Adapters/EventBusAdapter.cs
    assert: Adapter emits Godot signal and forwards in-process subscribers
  - path: Game.Core.Tests/Services/EventBusTests.cs
    assert: Publish/subscribe behavior is covered by xUnit
tech-tags: [cloudevents, contracts, eventbus, godot, csharp]
depends-on: [ADR-0020, ADR-0018]
depended-by: [ADR-0005]
supersedes: []
---

# ADR-0004: 事件总线与契约（CloudEvents 风格）

## Context

在 Godot+C# 模板中，场景装配层（Scenes）与领域层（Game.Core）需要一种稳定、可测试、可演化的事件通信方式，同时避免将 Godot API 渗透到 Core。需要统一事件结构与命名规则，并明确契约的 SSoT 存放位置。

## Decision

### 1) 契约结构（Contracts）

- SSoT：`Game.Core/Contracts/**`（见 ADR-0020）
- 事件结构：采用 CloudEvents 1.0 的最小字段集思想（不强依赖具体传输协议），用 `DomainEvent` 表达：
  - `Type`（事件类型）
  - `Source`（来源）
  - `Id`（唯一标识）
  - `Timestamp`（时间）
  - `SpecVersion`（默认 `"1.0"`）
  - `Data`（事件载荷，保持可序列化）

### 2) 命名规则（Event Type）

- 事件类型命名遵循：`${DOMAIN_PREFIX}.<entity>.<action>`
- 推荐前缀（模板口径）：
  - `core.<entity>.<action>`：领域事件
  - `screen.<name>.<action>`：Screen 生命周期
  - `ui.menu.<action>`：UI 命令/交互

### 3) 总线接口与实现

- Core 定义接口：`Game.Core/Services/IEventBus`（文件：`Game.Core/Services/EventBus.cs`）
- 默认实现：`InMemoryEventBus`（用于单测与轻量运行时）
- Godot 适配：`Game.Godot/Adapters/EventBusAdapter.cs`
  - 实现 `IEventBus`
  - 同时通过 Godot Signal（`DomainEventEmitted`）向场景层暴露事件

## Consequences

- 正向：Core 保持纯净可单测；事件结构统一；Scenes 可通过 Signal 订阅而不引入 Core 细节。
- 代价：需要保持契约纪律（禁止在非 SSoT 目录新增事件结构），并为关键事件补齐最小测试。

