---
ADR-ID: ADR-0004
title: 事件总线与契约 - CloudEvents 1.0 + IPC通信
status: Accepted
decision-time: '2025-08-17'
deciders: [架构团队, 开发团队]
archRefs: [CH03, CH04, CH05, CH06]
verification:
  - path: src/shared/contracts/events/builder.ts
    assert: CloudEvent includes specversion, id, source, type, time
  - path: tests/unit/contracts/events.spec.ts
    assert: Reject events missing required CloudEvents attributes
  - path: tests/unit/contracts/naming.spec.ts
    assert: Event type naming follows project convention
impact-scope: [src/shared/contracts/events.ts, src/core/events/, electron/ipc/]
tech-tags: [cloudevents, ipc, eventbus, contracts, communication]
depends-on: [ADR-0002]
depended-by: [ADR-0005, ADR-0007]
test-coverage: tests/unit/contracts/events.spec.ts
monitoring-metrics: [event_throughput, ipc_latency, contract_violations]
executable-deliverables:
  - src/shared/contracts/events.ts
  - src/core/events/bus.ts
  - tests/unit/contracts/events.spec.ts
supersedes: []
---

# ADR-0004: 事件总线与契约（CloudEvents 1.0 + IPC）

## Context

主进程、渲染进程、Worker 与 Phaser 场景之间需要稳定、类型安全的事件通信契约；需支持请求/响应与发布/订阅，同时保证可追踪、版本兼容与安全（IPC 白名单）。采用 CloudEvents 1.0 作为统一事件格式。

## Decision

- 使用 CloudEvents 1.0 作为事件规范；必填字段涵盖 `id/source/type/specversion`。
- 事件命名遵循 `<boundedContext>.<entity>.<action>`，并提供类型化 DTO。
- 在 `src/shared/contracts/**` 统一管理事件类型；IPC 白名单与参数校验在 preload 层执行。

## Base 示例占位规范（Windows-only 仓库同样适用）

- Base 文档/契约示例一律使用占位符 `${DOMAIN_PREFIX}`，避免在 Base 中硬编码域前缀：
  - `${DOMAIN_PREFIX}.game.scene_loaded`
  - `${DOMAIN_PREFIX}.system.error_occurred`
- 校验：`validateEventNaming` 先将 `${DOMAIN_PREFIX}` 归一化为占位值后再执行命名正则校验。
- Overlay/实现层绑定具体域前缀，避免口径漂移。

## Godot 变体（Game.Godot + EventBusAdapter）

- 本仓库在 Godot+C# 模板中采用本 ADR 作为事件命名与契约的上位规范，结合以下规则在运行时落地：
  - 事件命名前缀：
    - `ui.menu.<action>`：UI 菜单与按钮命令（如 `ui.menu.start`、`ui.menu.settings`、`ui.menu.quit`）。
    - `screen.<name>.<action>`：Screen 生命周期与关键操作（如 `screen.settings.opened`、`screen.settings.saved`）。
    - `core.<entity>.<action>`：领域事件推荐口径（如 `core.game.started`、`core.score.updated`、`core.player.health.changed`）。
    - `demo.<name>`：仅用于模板示例，实际业务不应新增 `demo.*` 事件。
  - 历史事件名：
    - 旧的 `game.started`、`score.changed` 等事件视为示例/兼容路径，仅在少量演示场景中保留；
    - 新增或重构代码一律使用 `core.*.*` / `ui.menu.*` / `screen.*.*` 三类前缀之一。

- Godot 侧实现：
  - `Game.Core/Contracts/DomainEvent.cs` 定义 CloudEvents 风格的领域事件结构；
  - `Game.Core/Services/EventBus.cs` 提供内存事件总线接口 `IEventBus`；
  - `Game.Godot/Adapters/EventBusAdapter.cs` 作为 Autoload 适配层，将 `DomainEvent` 序列化并通过 `DomainEventEmitted` Signal 暴露给 GDScript。
- 文档与测试对齐：
  - 事件命名与桥接细节的迁移方案见 `docs/migration/Phase-9-Signal-System.md`；
  - 代表性用例通过 xUnit（GameEngineCoreEventTests）与 GdUnit4（Adapters/Integration 小集）验证。

## Verification

- 单元测试：事件必填字段校验、命名规则校验。
- 构建门禁：事件类型必须从 `src/shared/contracts/**` 导入。

## Consequences

- 优点：强类型/可追踪/可演化；契约集中管理。
- 代价：前期定义与迁移成本较高；需严格文档纪律。
