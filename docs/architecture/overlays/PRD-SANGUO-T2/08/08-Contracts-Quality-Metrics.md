---
PRD-ID: PRD-SANGUO-T2
Title: 质量指标与门禁引用（Quality Metrics）
ADR-Refs:
  - ADR-0005
  - ADR-0015
  - ADR-0020
  - ADR-0025
Arch-Refs:
  - CH01
  - CH03
Test-Refs:
  - scripts/python/run_dotnet.py
  - scripts/python/task_links_validate.py
  - scripts/python/validate_contracts.py
Status: Accepted
---

本页登记 T2 功能纵切涉及的“质量指标与门禁”引用入口（只引用 ADR 口径，不复制阈值/策略），用于让任务/实现/CI 在同一口径下收敛。

## 质量门禁入口（Windows）

- 编译门禁（警告视为错误）：`dotnet build GodotGame.csproj -warnaserror`
- 单测与覆盖率：`dotnet test --collect:"XPlat Code Coverage"` 或 `py -3 scripts/python/run_dotnet.py --solution Game.sln --configuration Debug`
- 任务追溯（ADR/CH/Overlay/Test-Refs）：`py -3 scripts/python/task_links_validate.py`
- 契约 ↔ Overlay 对齐：`py -3 scripts/python/validate_contracts.py`
- 文档编码巡检（UTF-8/无语义乱码/无 Emoji）：`py -3 scripts/ci/check_encoding_issues.py`

## 验收要点（就地）

- 上述命令可在本机 Windows 环境跑通，且关键输出落盘到 `logs/`（详见 AGENTS.md 6.3）。
