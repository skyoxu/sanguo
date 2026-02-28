# Contracts Template v1

## 1. 目的与范围
- 本文将 `AGENTS.md`、`ADR-0004`、`ADR-0020`、Overlay 08 契约页的规则收敛为一个可执行模板入口。
- SSoT 口径不变：契约代码唯一落盘位置是 `Game.Core/Contracts/**`。
- 适用对象：`Domain Event`、`DTO`、`Interface`。

## 2. 依赖模板
- Event 模板：`docs/workflows/templates/contracts-event-template-v1.md`
- DTO 模板：`docs/workflows/templates/contracts-dto-template-v1.md`
- Interface 模板：`docs/workflows/templates/contracts-interface-template-v1.md`

## 3. 统一硬规则
| 规则 | 要求 |
|---|---|
| 命名空间 | 必须以 `Game.Core.Contracts` 开头 |
| 依赖边界 | 禁止 `Godot.*`；仅允许 BCL + `Game.Core.Contracts.*` |
| XML 注释 | 公共契约类型必须有 `<summary>`；定义 `EventType` 时必须有 `<remarks>` |
| EventType 命名 | 遵循 ADR-0004：`core.*.*` / `ui.menu.*` / `screen.*.*` |
| Overlay 回链 | 每个 `Game.Core/Contracts/*.cs` 必须在 Overlay 08 文档中被反引号路径引用 |
| 文档回链 | 新增契约必须更新对应 Overlay 08 契约段落（事件名、触发时机、字段、文件路径） |

## 4. 执行流程
1. 按契约类型选择三份模板之一。
2. 填写模板中的“必填项表”。
3. 将代码落盘到 `Game.Core/Contracts/<Module>/`。
4. 在 `docs/architecture/overlays/<PRD-ID>/08/` 更新契约条目。
5. 执行校验：`py -3 scripts/python/validate_contracts.py`。

## 5. 最小验证命令（Windows）
```powershell
py -3 scripts/python/validate_contracts.py
dotnet test Game.Core.Tests/Game.Core.Tests.csproj
```

## 6. 失败止损
- 若 `validate_contracts.py` 报 `overlay_backlink_missing`：先补 Overlay 引用，再改代码。
- 若报 `eventtype_issues`：先修正 `EventTypes.cs` 或 `EventType` 常量引用，再继续。
- 若报 `bcl_only_issues`：立即移除 `Godot.*` 或非 BCL 依赖。

