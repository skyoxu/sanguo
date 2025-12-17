---
ADR-ID: ADR-0005
title: 质量门禁（Windows-only）- Godot + C# 统一入口
status: Accepted
decision-time: '2025-12-16'
deciders: [架构团队, 开发团队]
archRefs: [CH07, CH09]
verification:
  - path: scripts/ci/quality_gate.ps1
    assert: Single entrypoint runs hard gates and writes artifacts under logs/**
  - path: scripts/python/quality_gates.py
    assert: CI-aligned orchestration (dotnet + selfcheck + encoding; optional gdunit/smoke)
  - path: scripts/ci/check_perf_budget.ps1
    assert: Parses [PERF] p95_ms from headless.log and enforces threshold when enabled
impact-scope:
  - Game.Core/
  - Game.Godot/
  - Tests.Godot/
  - scripts/
  - .github/workflows/
tech-tags: [quality-gates, windows, godot, csharp, dotnet, xunit, gdunit4, perf, encoding]
depends-on: [ADR-0011, ADR-0018, ADR-0019, ADR-0003, ADR-0015, ADR-0025, ADR-0020]
depended-by: [ADR-0008]
supersedes: []
---

# ADR-0005: 质量门禁（Godot + C#）

## Context

模板必须做到“复制即可跑 CI”：一旦门禁分散在多个脚本/文档/人工习惯中，就会出现口径漂移、重复执行与无法取证的问题。需要一个 Windows 友好的单入口，统一编排最小硬门禁，并将所有产物归档到 `logs/**`。

## Decision

### 1) 单入口（Windows）

- PowerShell 入口：`scripts/ci/quality_gate.ps1`
  - 作为本地/CI 的首选入口；可选启用导出/EXE 冒烟/性能门禁。
- Python 编排入口：`scripts/python/quality_gates.py`
  - 作为门禁编排的可扩展入口（默认对齐 CI 的最小集合）。

### 2) 最小硬门禁集合（默认）

- dotnet：编译与单元测试（xUnit）
- Godot：headless self-check（启动 + 关键 Autoload 兜底）

### 3) 可选硬门禁（按需启用）

- GdUnit4 小集（安全/关键装配）：`--gdunit-hard`
- Headless smoke（严格模式 marker/DB）：`--smoke`
- 性能 P95 门禁：`-PerfP95Ms <ms>`（阈值口径见 ADR-0015）

### 4) 软门禁（不阻断，但必须产出工件）

- 编码/文档清洁：`scripts/python/check_encoding.py`
- 契约引用对齐：`scripts/python/validate_contracts.py`

### 5) 工件（统一落盘）

- 单元测试：`logs/unit/<YYYY-MM-DD>/`
- 引擎/场景：`logs/e2e/<YYYY-MM-DD>/`
- CI 汇总与扫描：`logs/ci/<YYYY-MM-DD>/`

## Verification

本地最小验收（PowerShell）：

```powershell
pwsh -File scripts/ci/quality_gate.ps1 -GodotBin "$env:GODOT_BIN"
```

CI 侧应能在 `logs/**` 中找到对应摘要与日志文件；失败时可直接定位到具体 gate 的输出。

## Consequences

- 正向：门禁入口统一、Windows 兼容、失败可定位、产物可回溯。
- 代价：需要保持“单入口优先”的纪律，避免把门禁逻辑散落到工作流脚本或文档示例中。

