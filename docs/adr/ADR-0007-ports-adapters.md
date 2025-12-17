---
ADR-ID: ADR-0007
title: 端口与适配器（Ports & Adapters）- Godot+C# 三层分离
status: Accepted
decision-time: '2025-12-16'
deciders: [架构团队, 开发团队]
archRefs: [CH04, CH05, CH06]
verification:
  - path: Game.Core/
    assert: Core layer stays engine-agnostic (no Godot API references)
  - path: Game.Core/Ports/
    assert: Ports are interfaces used by Core
  - path: Game.Godot/Adapters/
    assert: Adapters implement ports using Godot APIs
tech-tags: [ports-adapters, hexagonal-architecture, godot, csharp, testing]
depends-on: [ADR-0018, ADR-0025]
depended-by: []
supersedes: []
---

# ADR-0007: 端口与适配器（Ports & Adapters）

## Context

Godot 脚本/节点 API 与业务规则混在一起会导致：

- 单元测试必须启动引擎，执行慢且不稳定
- 核心逻辑被引擎类型绑死，难以重构与复用
- 安全/路径/网络等规则无法在领域层统一验证

因此需要一个清晰的边界：领域层只依赖抽象（Ports），引擎层通过适配器实现这些抽象。

## Decision

### 1) 三层分离（落地目录）

- Core（纯 C#，可单测）：`Game.Core/**`
  - Ports：`Game.Core/Ports/**`（接口/抽象）
  - Contracts：`Game.Core/Contracts/**`（事件/DTO，见 ADR-0020）
- Adapters（仅封装 Godot API）：`Game.Godot/Adapters/**`
  - 实现 Ports；负责 `res://`/`user://`、Godot Signals、IO 等具体交互
- Scenes（装配与信号路由）：`.tscn` 资源与 `Game.Godot/Scripts/**`

### 2) 依赖方向（不可回退）

- Core 只能依赖 `System.*` 与自身 Contracts/Ports，不得引用 `Godot.*`。
- Adapters 可以引用 `Godot.*`，并实现 Core 的 Ports。
- Scenes 只做装配/路由，不承载复杂业务逻辑。

## Consequences

- 正向：xUnit 单测保持毫秒级；边界清晰；重构与扩展更稳定。
- 代价：需要维护 Ports/Adapters 的接口设计与实现同步。

