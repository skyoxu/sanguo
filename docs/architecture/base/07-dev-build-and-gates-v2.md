---
title: 07 dev build and gates v2
status: base-SSoT
generated_variant: deep-optimized
ssot_scope: chapter-07-only
reuse_level: base-clean
adr_refs: [ADR-0011, ADR-0018, ADR-0025, ADR-0015, ADR-0019, ADR-0003]
placeholders: Unknown Product, unknown-product, gamedev, dev, 0.0.0, production, dev-team, dev-project
derived_from: 07-dev-build-and-gates-v2.md
last_generated: 2025-12-16
---

# 07 开发、构建与质量门禁（Windows-only）

本章定义“本地与 CI 一致”的最小可执行门禁矩阵：dotnet 编译/单测、Godot headless 冒烟、编码与文档扫描、（可选）导出与性能门禁。阈值与策略以 ADR 为准，本章只描述入口与工件。

## 1) 开发者日常循环（Local Loop）

- 编辑与运行：
  - Godot Editor：F5 运行、F6 运行当前场景
  - C#：`dotnet build` / `dotnet test`
- 推荐先跑最小门禁：
  - `pwsh -File scripts/ci/quality_gate.ps1 -GodotBin "$env:GODOT_BIN"`

## 2) 门禁矩阵（最小可执行）

| Gate | 目的 | 推荐入口（Windows） | 工件落盘 |
| --- | --- | --- | --- |
| Typecheck/Build | 编译失败即止损 | `dotnet build -warnaserror`（由脚本编排） | `logs/ci/<YYYY-MM-DD>/typecheck.log`（如有） |
| Unit (xUnit) | 领域逻辑回归 | `dotnet test --collect:\"XPlat Code Coverage\"`（由脚本编排） | `logs/unit/<YYYY-MM-DD>/` |
| Godot Selfcheck | 引擎启动+关键 Autoload 兜底 | `py -3 scripts/python/godot_selfcheck.py`（由脚本编排） | `logs/e2e/<YYYY-MM-DD>/` |
| Encoding Scan (soft) | 防止文档/脚本乱码漂移 | `py -3 scripts/python/check_encoding.py --since-today` | `logs/ci/<YYYY-MM-DD>/encoding/` |
| Smoke Headless（可选） | 主场景可启动并退出 | `py -3 scripts/python/smoke_headless.py` | `logs/ci/<YYYY-MM-DD>/smoke/` |
| Export + EXE Smoke（可选） | 导出产物可运行 | `pwsh -File scripts/ci/export_windows.ps1` + `smoke_exe.ps1` | `build/**` + `logs/ci/<YYYY-MM-DD>/` |
| Perf P95（可选） | 帧时间回归守门 | `pwsh -File scripts/ci/check_perf_budget.ps1 -MaxP95Ms <ms>` | `logs/ci/<YYYY-MM-DD>/smoke/headless.log` |

## 3) 推荐的一键入口

### 3.1 PowerShell（最贴近 CI）

- 基础门禁：`pwsh -File scripts/ci/quality_gate.ps1 -GodotBin "$env:GODOT_BIN"`
- 含导出+冒烟：`pwsh -File scripts/ci/quality_gate.ps1 -GodotBin "$env:GODOT_BIN" -WithExport`
- 启用性能门禁：`pwsh -File scripts/ci/quality_gate.ps1 -GodotBin "$env:GODOT_BIN" -PerfP95Ms 20`

### 3.2 Python（适合本地编排/扩展）

- `py -3 scripts/python/quality_gates.py all --godot-bin \"$env:GODOT_BIN\" --solution Game.sln --configuration Debug --build-solutions`

## 4) CI 工作流映射（仓库内）

- 质量门禁：`.github/workflows/windows-quality-gate.yml`
- Dry Run / Smoke：`.github/workflows/windows-smoke-dry-run.yml`
- 导出：`.github/workflows/windows-export-slim.yml`
- Release：`.github/workflows/windows-release.yml`、`.github/workflows/windows-release-tag.yml`

## 5) 工件与排障（统一入口）

- 统一目录：`logs/**`
- 优先查看：`logs/ci/<YYYY-MM-DD>/`（门禁编排摘要、编码/文档扫描、Release Health 等）
