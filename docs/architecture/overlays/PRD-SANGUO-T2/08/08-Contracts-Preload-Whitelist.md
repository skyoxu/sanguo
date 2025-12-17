---
PRD-ID: PRD-SANGUO-T2
Title: 资源加载与外链白名单（Preload/Resource Whitelist）
ADR-Refs:
  - ADR-0019
  - ADR-0005
  - ADR-0020
Arch-Refs:
  - CH01
  - CH03
Test-Refs:
  - scripts/python/godot_selfcheck.py
Contracts-Refs: []
Status: Accepted
---

本页用于登记 T2 功能纵切中“资源加载与外链访问”的白名单口径（引用 ADR，不复制阈值/策略）。

## 范围

- 资源路径：仅允许 `res://`（只读）与 `user://`（读写）。
- 外链/网络：仅 HTTPS + 主机白名单 `ALLOWED_EXTERNAL_HOSTS`；`GD_OFFLINE_MODE=1` 时拒绝所有出网并审计。
- 运行期动态加载外部程序集/脚本：默认禁止（详见 ADR-0019）。

## 纵切落地建议（引用型）

- 资源加载入口集中在适配层（Adapters/Scenes），领域层（Game.Core）不直接访问文件系统与网络。
- 白名单解析与拒绝路径的审计输出统一写入 `logs/ci/<YYYY-MM-DD>/security-audit.jsonl`（字段口径见 AGENTS.md 6.3）。

## 验收要点（就地）

- 工程启动/Autoload 自检可运行并产出日志：`py -3 scripts/python/godot_selfcheck.py run --godot-bin "$env:GODOT_BIN" --build-solutions`
