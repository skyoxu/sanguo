---
adr: ADR-0005
title: Addendum — Quality Gates for Godot + C#
date: 2025-11-08
status: Active
scope: Windows-only CI, Godot 4.5 (.NET)
---

# ADR-0005 补充：Godot+C# 质量门禁对齐

## Context

模板从旧的 Web/LegacyDesktopShell 工具链迁移到 Godot+C# 后，质量门禁需要以 **.NET 单测 + Godot headless/场景测试** 为主，同时保持“单入口编排、工件可追溯、Windows 兼容”。

## Decisions

- 单元测试（领域层）：`dotnet test` + coverlet（XPlat Code Coverage）；覆盖率门禁口径为 lines ≥ 90%、branches ≥ 85%（详见 `docs/testing-framework.md`）。
- 场景测试（引擎层）：GdUnit4 headless；非 0 退出码视为失败；JUnit/XML 与摘要写入 `logs/e2e/**`。
- 单入口（Windows）：PowerShell 入口 `scripts/ci/quality_gate.ps1`，Python 入口 `scripts/python/quality_gates.py`；两者保持同一门禁集合。
- 工件：门禁/测试输出统一落盘 `logs/**`（目录口径见 `docs/testing-framework.md`）。

## Commands（示例）

- `dotnet test --collect:\"XPlat Code Coverage\"`
- `py -3 scripts/python/run_gdunit.py --godot-bin \"%GODOT_BIN%\" --project Tests.Godot --add tests/Security/Hard`
- `pwsh -File scripts/ci/quality_gate.ps1 -GodotBin \"%GODOT_BIN%\"`

## Verification

- CI 中可看到：覆盖率摘要 + GdUnit4 pass/fail + 对应 `logs/**` 工件。

