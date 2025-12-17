---
title: 08 crosscutting and feature slices.base
status: base-SSoT
adr_refs: [ADR-0018, ADR-0019, ADR-0003, ADR-0004, ADR-0005, ADR-0020, ADR-0025]
placeholders: unknown-app, Unknown Product, unknown-product, ${DOMAIN_PREFIX}, ${PRD_ID}
derived_from: arc42 §8 (crosscutting concepts), C4 (Context/Container) minimal
last_generated: 2025-12-16
---

# 08 跨切面规则与功能纵切（Base 模板）

本章是 Base 的“模板与约束页”：只定义跨切面规则、纵切必备要素与验收形态；任何具体业务内容必须写在 `docs/architecture/overlays/<PRD_ID>/08/`。

## 08.1 原则（Base vs Overlay）

- Base：跨切面规则（安全、可观测、门禁、契约、命名、日志）与模板；禁止出现任何 `PRD_xxx` 实例化内容。
- Overlay 08：以单个特性/用例为单位贯穿 Scenes → Adapters → Core → Storage 的一条链，并提供就地验收与 Test-Refs。

## 08.2 契约（Contracts）规则（SSoT）

### 存放位置

- Contracts 的单一事实来源：`Game.Core/Contracts/**`（见 ADR-0020）。
- 文档中引用 Contracts 时必须使用反引号写明路径，例如：`Game.Core/Contracts/Guild/GuildMemberJoined.cs`。

### 事件命名

- 事件类型命名遵循：`${DOMAIN_PREFIX}.<entity>.<action>`（见 ADR-0004）。
- 推荐前缀：`core.*.*`（领域事件）、`screen.*.*`（屏幕生命周期）、`ui.menu.*`（UI 命令）。

示例（C# 事件契约片段）：

```csharp
namespace Game.Core.Contracts;

public sealed record ExampleEvent(string Id)
{
    public const string EventType = "core.example.created";
}
```

## 08.3 C4 图表模板（Overlay 必填）

### 08.3.1 System Context（模板）

```mermaid
flowchart LR
  actor([User/Actor])
  app[[unknown-app (Godot Game)]]
  slice[[{feature} Slice]]
  telemetry[(Sentry/Logs)]
  storage[(user:// storage)]
  actor -->|interacts with| app
  app -->|invokes| slice
  slice -->|writes| storage
  slice -->|observability| telemetry
```

### 08.3.2 Container（模板：Scenes/Adapters/Core）

```mermaid
flowchart TB
  subgraph App[unknown-app]
    scenes[Scenes (.tscn)]
    adapters[Adapters (Godot API)]
    core[Game.Core (pure C#)]
    ports[(Ports)]
    store[(SQLite/ConfigFile)]
  end
  scenes --> adapters
  adapters --> core
  core --> ports
  ports --> store
```

## 08.4 Overlay 08 的最小验收清单

- [ ] 文档页头含 front-matter，且 `adr_refs` 指向本次变更相关 ADR
- [ ] 至少提供 2 张图：Context + Container（可用 Mermaid）
- [ ] 引用的 Contracts 路径真实存在（`py -3 scripts/python/validate_contracts.py` 可通过）
- [ ] Test-Refs：列出至少 1 个 xUnit 或 1 个 GdUnit4 用例路径（初期可为占位用例，但必须存在文件）
- [ ] 08 正文不复制阈值（阈值只引用 ADR/Base 章节）
