# ADR-0020: Contracts 存放位置标准化（SSoT = `Game.Core/Contracts/**`）

- Status: Accepted
- Date: 2025-12-02
- Related: ADR-0004（事件与命名）、ADR-0018（分层与发布）、ADR-0019（安全基线）

## Context

在模板演进过程中，契约（Domain Events / DTOs / Ports 类型等）容易被分散到不同目录，导致：

- “哪一份才是权威口径”不清晰（SSoT 漂移）
- 命名空间与引用混乱，增加编译/重构成本
- 文档/Overlay 08 与代码无法稳定对齐

## Decision

### 1) 单一事实来源（SSoT）

所有契约文件必须存放在：

- `Game.Core/Contracts/**`

并保持：

- 不依赖 Godot API（Core 可毫秒级单测）
- 命名空间以 `Game.Core.Contracts.<Module>` 为前缀

示例（C#）：

```csharp
namespace Game.Core.Contracts.Guild;

/// <summary>
/// Domain event: core.guild.member.joined
/// </summary>
public sealed record GuildMemberJoined(
    string UserId,
    string GuildId,
    DateTimeOffset JoinedAt,
    string Role
)
{
    public const string EventType = "core.guild.member.joined";
}
```

### 2) 禁止位置（Forbidden）

以下目录禁止新增/存放 Contracts：

- `Game.Godot/**`（适配层不得定义契约）
- `Tests.Godot/**`（测试不得成为口径来源）
- `Scenes/**` 或 `.tscn` 资源目录（UI/装配层不得定义契约）
- `scripts/**`（脚本工具目录不得承载 Contracts SSoT）

## Verification（可执行校验）

- Overlay 文档引用校验（CI/本地均可）：
  - `py -3 scripts/python/validate_contracts.py`
  - 规则：Overlay 08 文档中用反引号引用 `Game.Core/Contracts/...cs` 时，文件必须真实存在。
- 单元测试（领域层）：对关键契约常量/默认值做最小断言（见 `docs/testing-framework.md`）。

## Consequences

- 正向：Contracts SSoT 清晰；Core 层保持纯净；文档与代码可稳定对齐；迁移/重构成本下降。
- 代价：需要持续纪律（PR 检查/脚本校验）避免回流到非 SSoT 目录。

