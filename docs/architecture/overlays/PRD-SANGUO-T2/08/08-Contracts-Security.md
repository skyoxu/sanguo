---
PRD-ID: PRD-SANGUO-T2
Title: 安全口径引用（Godot Security Contracts）
ADR-Refs:
  - ADR-0019
  - ADR-0004
  - ADR-0005
  - ADR-0020
Test-Refs:
  - Game.Core.Tests/State/GameStateManagerSecurityTests.cs
  - scripts/ci/check_encoding_issues.py
Status: Accepted
---

本页登记 T2 功能纵切涉及的安全口径引用点（仅引用 ADR，不复制阈值/策略）。

## 核心原则（引用型）

- 文件与路径：只允许 `res://`（只读）与 `user://`（读写）；拒绝绝对路径与越权访问，失败必须审计。
- 外链与网络：仅 HTTPS；主机白名单 `ALLOWED_EXTERNAL_HOSTS`；`GD_OFFLINE_MODE=1` 时拒绝所有出网并审计。
- 事件与载荷：事件封装遵循 ADR-0004；事件载荷必须实现 `IEventData`，避免 `object/dynamic` 注入面。

## T2 已落地的安全单测（领域层）

- `Game.Core.Tests/State/GameStateManagerSecurityTests.cs`
  - 深度嵌套 JSON 的拒绝策略（MaxDepth 生效）
  - 存档字段尺寸上限与校验（标题/截图等）
  - 校验失败时的异常类型与行为一致性

## 文档与工作流护栏

- 文档必须 UTF-8 编码且禁止 Emoji（fixture 文件除外）：`py -3 scripts/ci/check_encoding_issues.py`
