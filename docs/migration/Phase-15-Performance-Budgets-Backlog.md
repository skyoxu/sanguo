# Phase 15 Backlog — 性能预算与门禁增强

> 状态：Backlog（非当前模板 DoD，按需渐进启用）
> 目的：承接 Phase-15-Performance-Budgets-and-Gates.md 中尚未在当前 Godot+C# 模板落地的性能预算与门禁蓝图，避免“文档超前、实现滞后”，同时为后续项目提供性能优化路线图。
> 相关 ADR：ADR-0015（性能预算与门禁）、ADR-0005（质量门禁）、Phase-12（Headless 烟测）、Phase-13（quality_gates 脚本）

---

## B1：Game.Core 性能库（PerformanceTracker.cs 等）

- 现状：
  - 当前模板仅在 Godot 侧提供 `Game.Godot/Scripts/Perf/PerformanceTracker.cs`，采集帧时间并输出 `[PERF] ... p95_ms=...` 与 `user://logs/perf/perf.json`；
  - Phase‑15 文档中的 `Game.Core/Performance/PerformanceTracker.cs`、`PerformanceMetrics.cs`、`QueryPerformanceTracker.cs` 仍停留在蓝图阶段，用于描述理想的 C# 性能库形态。
- 蓝图目标：
  - 在 Game.Core 层实现纯 C# 的性能追踪库：
    - 支持任意指标的 Start/End/RecordMeasure；
    - 计算 P50/P95/P99、平均值、最大值等；
    - 生成 JSON 报告，可供 Godot/CI/外部工具消费；
    - 提供 QueryPerformanceTracker 封装 DB 查询/命令的计时。
- 建议实现方式：
  - 参考 Phase‑15 文档中给出的 PerformanceTracker/PerformanceMetrics/QueryPerformanceTracker 示例，将其落地到 `Game.Core/Performance/**`；
  - 与 Godot 侧 `Scripts/Perf/PerformanceTracker.cs` 保持概念一致，但避免直接依赖 Godot API，以便在 xUnit 环境下单测。
- 优先级：P2（适合在有明确性能需求的业务项目中启用，模板阶段可不强制）。

---

## B2：跨场景性能基准与 Python 聚合脚本

- 现状：
  - 现有门禁仅针对单一 `[PERF] ... p95_ms=...` 控制台标记，结合 `check_perf_budget.ps1` 对最近一段帧时间的 P95 做预算检查；
  - Phase‑15 蓝图中的 baseline JSON（`benchmarks/*.json`）、`PerformanceGates.cs`（Godot 侧门禁组件）、`performance_gates.py` 聚合脚本以及基准建立脚本（例如 `scripts/ci/establish_baseline.sh` 或 PowerShell 变体）尚未落地。
- 蓝图目标：
  - 为首屏、菜单、游戏场景、DB 查询等关键路径建立基准文件（基线 JSON），并在 CI 中对比当前运行结果：
    - 支持容忍度（tolerance%）配置，避免微小波动导致频繁失败；
    - 在 Markdown/JSON 报告中清晰标出超出阈值的指标。
- 建议实现方式：
  - 新增 Python 脚本 `scripts/python/performance_gates.py`：
    - 读取 baseline 与 current JSON 文件（如 `benchmarks/startup.json`、`benchmarks/menu.json` 等），计算偏差；
    - 输出人类可读的差异报告，并通过 exit code 暴露 PASS/FAIL 给 CI；
  - 在 Godot 侧补充 `PerformanceGates.cs`（或等价 GDScript 组件），作为在场景内加载/校验基准的门禁入口；
  - 提供一个基准建立脚本（如 `scripts/ci/establish_baseline.sh` 或 PowerShell 版本），用于在受控环境下生成 `benchmarks/*.json` 初始基准；
  - 在 Phase‑15 文档中补充 Godot+C# 变体示例命令，说明如何生成 current-run 数据与 baseline。
- 优先级：P2–P3（适合有长期性能目标的项目，模板阶段可暂存为设计）。

---

## B3：性能报告与历史追踪（reports/performance/**）

- 现状：
  - 当前模板只将最近一次 PerfTracker 刷新的统计写入 `user://logs/perf/perf.json`，CI 只关心最新的 `[PERF]` 标记；
  - Phase‑15 文档中提到的 `reports/performance/current-run-report.*`、performance-history.csv 尚未实现。
- 蓝图目标：
  - 为性能测试运行生成 HTML/JSON 报告，便于手动分析与分享；
  - 维护一份历史性能数据（CSV 或 JSON lines），用于观测长期趋势（例如首屏时间、P95 帧时间的变化）。
- 建议实现方式：
  - 在 `performance_gates.py` 或独立脚本中，对 current-run 与 baseline 进行聚合，并生成 `reports/performance/**`；
  - 在 CI 中将这些报告作为 artifact 上传，便于离线分析。
- 优先级：P3（更偏向可观测性与分析，不影响当前门禁基线）。

---

## B4：更细粒度的指标采集（GC 暂停/信号延迟/DB 细项）

- 现状：
  - Phase‑15 KPI 表中定义了 GC 暂停、信号分发延迟、DB 查询延迟等指标；
  - 当前实现主要覆盖“全局帧时间 P95”，上述细粒度指标尚未在代码中实现。
- 蓝图目标：
  - 在 Godot+C# 环境下，选取一小部分可实现且有价值的细粒度指标：
    - 例如：EventBus 信号延迟、特定 DB 查询的平均耗时、关键算法/系统的局部耗时等；
  - 将这些指标与 Game.Core/Performance 库结合，统一输出到 JSON 报告中。
- 建议实现方式：
  - 结合 Phase‑21 性能优化文档，从具体业务 case（如复杂 AI、经济模拟）中选取典型路径，使用 PerformanceTracker 或手写计时器采样；
  - 在 Backlog 中记录每个新增指标的定义与阈值，不一次性覆盖所有 KPI。
- 优先级：P3（需要在性能优化场景中按需启用，模板阶段不强求）。

---

## B5：独立性能门禁 CI 工作流（performance-gates.yml）

- 现状：
  - 目前性能门禁仅作为 Windows CI / Windows Quality Gate 工作流中的可选步骤，通过 `quality_gate.ps1` 调用 `check_perf_budget.ps1`；
  - Phase‑15 蓝图中提到的独立性能门禁工作流（例如 `.github/workflows/performance-gates.yml`）尚未创建。
- 蓝图目标：
  - 为需要更严格性能管控的项目提供一条单独的 CI 工作流：
    - 只运行性能相关脚本（PerfTracker 采集 → performance_gates.py 聚合 → 报告上传）；
    - 不与常规构建/测试步骤混在一起，便于在特定分支或定时任务中执行。
- 建议实现方式：
  - 新增 `.github/workflows/performance-gates.yml`，调用 Godot Headless + PerfTracker 采集 + `scripts/python/performance_gates.py` 判定；
  - 在 Phase‑15 文档中补充工作流示例，并说明如何在项目中启用/禁用该工作流。
- 优先级：P3（适合有独立性能流水线需求的项目，模板阶段可不强制）。

---

## 使用说明

- 对于基于本模板创建的新项目：
  - 优先使用现有的 Godot PerfTracker + `[PERF]` 标记 + `check_perf_budget.ps1` 作为基础性能门禁；
  - 当项目对性能有更高要求时，再按 B1→B2→B3/B4 的顺序逐步启用 Game.Core 性能库、baseline 对比与历史报告。

- 对于模板本身：
  - 当前 Phase 15 仅要求控制台 `[PERF] p95_ms=...` 标记与 `check_perf_budget.ps1` 能够协同工作，提供一条简洁可用的性能回归守门；
  - 本 Backlog 文件用于记录蓝图级性能方案，避免在 Phase 15 内部无限扩展范围，同时为后续性能专项优化预留接口。
