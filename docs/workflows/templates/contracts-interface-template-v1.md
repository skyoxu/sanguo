# Interface Contract Template v1

## 必填项表
| 字段 | 必填 | 规则 |
|---|---|---|
| 文件路径 | 是 | `Game.Core/Contracts/Interfaces/I<Subject>.cs` 或模块目录 |
| 命名空间 | 是 | `namespace Game.Core.Contracts.Interfaces;` 或子模块 |
| 类型声明 | 是 | `public interface I<Subject>` |
| XML Summary | 是 | 说明接口职责和边界 |
| 方法 XML 注释 | 是 | 公共方法建议包含 `<summary>`、`<param>`、`<returns>` |
| 参数/返回类型 | 是 | 使用契约类型或 BCL 类型；禁止 `object`/`dynamic` |
| Godot 依赖 | 否 | 禁止 `using Godot` 与 `Godot.*` |

## C# 最小模板
```csharp
namespace Game.Core.Contracts.Interfaces;

/// <summary>
/// Handles command-driven state transitions.
/// </summary>
public interface I<Subject>
{
    /// <summary>
    /// Execute one deterministic transition.
    /// </summary>
    /// <param name="current">Current state.</param>
    /// <param name="command">Input command.</param>
    /// <returns>Transition result.</returns>
    <ReturnType> Handle(<StateType> current, <CommandType> command);
}
```

