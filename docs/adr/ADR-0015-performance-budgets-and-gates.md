# ADR-0015: 性能预算与门禁（Godot 4.5 + C#）

- Status: Accepted
- Date: 2025-09-12
- Updated: 2025-12-16（合并 Godot 性能预算补充；移除旧运行时遗留口径）
- Deciders: Core Maintainers
- Approver: Architecture Team
- Related: ADR-0003（可观测性与发布健康）、ADR-0005（质量门禁）、ADR-0011（Windows-only）、ADR-0018（Godot 运行时与发布）

## Context

性能预算与门禁若分散在脚本/测试/文档中，会导致口径漂移，无法稳定阻断回归。当前仓库运行时已确认为 **Godot 4.5 + C#/.NET 8（Windows-only）**，因此性能指标与门禁必须以 **Godot 运行时 KPI** 为准，并提供 CI 友好的“最小可执行门禁”。

## Decision

### 1) 预算（初始值）

> 预算是“可调的工程约束”。在 CI 中可用更宽松阈值减少误判，在发布/性能分支中收紧阈值（以基准机为准）。

- 帧时间（主循环，窗口 P95）：CI 建议 ≤ 20ms；目标值 ≤ 16.67ms（60 FPS）。
- 帧时间尖峰（P99 或单帧上限，软约束）：≤ 33ms。
- 场景切换：冷切换 P95 ≤ 500ms；热切换 ≤ 200ms。
- 资源加载（按资源包/批次）：冷加载 P95 ≤ 800ms；热加载 ≤ 300ms。
- 内存（稳态，软约束）：≤ 500MB；空闲 10 分钟泄漏 ≤ 5MB。

### 2) 采样与工件（最小 SSoT）

- 运行时采样器：`Game.Godot/Scripts/Perf/PerformanceTracker.cs`（Autoload）
  - 按窗口采集最近 `WindowFrames`（默认 300 帧）的 `delta`（毫秒）；
  - 定期输出控制台标记：`[PERF] frames=... avg_ms=... p50_ms=... p95_ms=... p99_ms=...`；
  - 写入 `user://logs/perf/perf.json`（仅保存最近一次窗口的统计结果）。
- CI 侧可解析工件：`logs/ci/<YYYYMMDD-HHmmss>/smoke/headless.log`（包含 `[PERF]` 标记）。

### 3) 门禁（最小可执行）

- 门禁脚本：`scripts/ci/check_perf_budget.ps1`
  - 从 `logs/ci/**/headless.log` 解析最近一次 `[PERF]` 标记的 `p95_ms`；
  - 与 `-MaxP95Ms` 比较，输出 `PERF BUDGET PASS/FAIL` 并以退出码 `0/1` 表示结果。
- 门禁入口：`scripts/ci/quality_gate.ps1`
  - 仅在显式传入 `-PerfP95Ms <ms>` 时启用性能门禁；未传入（默认 `0`）则不阻断。

### 4) 约束（防漂移）

- 性能预算只使用 Godot 运行时指标；不再维护旧工具链/旧运行时相关预算与门禁。
- Overlay 08 章不复制阈值，仅引用本 ADR 或 Phase 文档（避免口径漂移）。

## Consequences

- 性能预算与门禁口径收敛到单一 ADR；CI 至少具备一条可执行的帧时间 P95 回归守门。
- 通过 `-PerfP95Ms` 参数显式启用/收紧门禁，降低 CI 环境差异带来的误判风险。
- 后续扩展（启动、内存、场景切换等多指标门禁）应统一收敛到 `docs/migration/Phase-15-Performance-Budgets-Backlog.md` 的增强项。

## Alternatives

- 不设性能门禁（拒绝：无法阻断回归）。
- 仅用平均值断言（拒绝：无法覆盖尾部抖动）。

## References

- `Game.Godot/Scripts/Perf/PerformanceTracker.cs`
- `scripts/ci/check_perf_budget.ps1`
- `scripts/ci/quality_gate.ps1`
- `docs/migration/Phase-15-Performance-Budgets-and-Gates.md`
- `docs/migration/Phase-15-Performance-Budgets-Backlog.md`
