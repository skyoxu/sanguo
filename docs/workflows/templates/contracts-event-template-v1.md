# Event Contract Template v1

## 必填项表
| 字段 | 必填 | 规则 |
|---|---|---|
| 文件路径 | 是 | `Game.Core/Contracts/<Module>/<EventName>.cs` |
| 命名空间 | 是 | `namespace Game.Core.Contracts.<Module>;` |
| 类型声明 | 是 | `public sealed record <EventName>(...)` |
| XML Summary | 是 | 说明事件业务语义 |
| XML Remarks | 是 | 引用 ADR 与 Overlay 路径 |
| EventType 常量 | 是 | `public const string EventType = EventTypes.<Name>;` |
| EventType 值 | 是 | 对应 `EventTypes.cs` 且满足 `core.*.*` / `ui.menu.*` / `screen.*.*` |
| 字段类型 | 是 | 明确类型，禁止 `object`/`dynamic` |
| Godot 依赖 | 否 | 禁止 `using Godot` 与 `Godot.*` |

## C# 最小模板
```csharp
namespace Game.Core.Contracts.<Module>;

/// <summary>
/// Domain event: core.<entity>.<action>
/// </summary>
/// <remarks>
/// ADR refs: ADR-0004, ADR-0020.
/// Overlay ref: docs/architecture/overlays/<PRD-ID>/08/08-Contracts-<Module>.md
/// </remarks>
public sealed record <EventName>(
    string RunId,
    DateTimeOffset OccurredAt
)
{
    public const string EventType = EventTypes.<EventTypeName>;
}
```

