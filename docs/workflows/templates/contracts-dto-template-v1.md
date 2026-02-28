# DTO Contract Template v1

## 必填项表
| 字段 | 必填 | 规则 |
|---|---|---|
| 文件路径 | 是 | `Game.Core/Contracts/<Module>/<DtoName>.cs` |
| 命名空间 | 是 | `namespace Game.Core.Contracts.<Module>;` |
| 类型声明 | 是 | `public sealed record <DtoName>(...)`（优先不可变） |
| XML Summary | 是 | 说明 DTO 用途与边界 |
| XML Remarks | 否 | 涉及 ADR/Overlay 时建议补充 |
| 字段类型 | 是 | 明确类型，禁止 `object`/`dynamic` |
| EventType 常量 | 否 | DTO 不要求 `EventType` |
| Godot 依赖 | 否 | 禁止 `using Godot` 与 `Godot.*` |

## C# 最小模板
```csharp
namespace Game.Core.Contracts.<Module>;

/// <summary>
/// DTO for <use case>.
/// </summary>
public sealed record <DtoName>(
    string Id,
    DateTimeOffset UpdatedAt
);
```

