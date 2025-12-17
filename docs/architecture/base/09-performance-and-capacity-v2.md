---
title: 09 performance and capacity v2
status: base-SSoT
adr_refs: [ADR-0015, ADR-0018, ADR-0011, ADR-0003]
placeholders: Unknown Product, ${DOMAIN_PREFIX}
---

# 09 性能与容量（Godot 运行时口径）

本章以 Godot 主循环为中心描述性能与容量的可观测与门禁落点。阈值口径以 ADR-0015 为准；Base 不复制阈值表。

## 1) 指标与预算（引用 ADR-0015）

- 帧时间：以窗口 P95 为最小可执行门禁指标（60 FPS 目标对应 16.67ms）。
- 场景切换/资源加载：以 P95 作为主要回归监测指标（扩展门禁属于增强项）。
- 内存：稳态与泄漏以软约束为主，优先产出可回溯工件。

## 2) 采样与工件（运行时 → CI）

- 运行时采样器（Autoload）：`Game.Godot/Scripts/Perf/PerformanceTracker.cs`
  - 周期性输出控制台标记：`[PERF] frames=... p50_ms=... p95_ms=... p99_ms=...`
  - 写入 `user://logs/perf/perf.json`（保存最近一次窗口统计）
- CI 工件（headless）：`logs/ci/<YYYY-MM-DD>/smoke/headless.log`（包含 `[PERF]` 标记）

## 3) 最小可执行门禁（P95）

- 解析脚本：`scripts/ci/check_perf_budget.ps1`
  - 读取最新的 `headless.log`，解析最后一次 `[PERF]` 的 `p95_ms`
  - 与参数 `-MaxP95Ms` 对比，退出码 `0/1` 表示 PASS/FAIL
- 门禁入口：`scripts/ci/quality_gate.ps1`
  - 仅在显式传入 `-PerfP95Ms <ms>` 时启用性能门禁（默认不阻断）

## 4) 排障建议（最小）

- 先看 `headless.log` 的 `[PERF]` 行是否持续输出且样本数合理（过少样本会导致 P95 无意义）。
- 若性能波动来自冷启动/首次加载：区分冷/热路径并在脚本侧记录预热策略（作为后续增强项）。

