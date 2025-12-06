---
adr: ADR-0015
title: Addendum — Performance Budgets for Godot Runtime
date: 2025-11-08
status: Active
scope: Windows-only runtime, Godot 4.5 (.NET)
---

# Addendum to ADR-0015: Performance Budgets (Godot Alignment)

## Context
Replace web-centric budgets with Godot runtime KPIs and CI-friendly sampling.

## Budgets (initial)
- Frame time (P95): ≤ 16.7 ms (60 FPS) on target hardware; spikes ≤ 33 ms.
- Scene switch (cold): P95 ≤ 500 ms for main scenes; warm ≤ 200 ms.
- Asset load (cold): P95 ≤ 800 ms per pack; warm ≤ 300 ms.
- Memory (steady): ≤ 500 MB; leak rate ≤ 5 MB over 10 minutes idle.

## Execution
- Gather via Godot Profiler + custom metrics (GDScript/C#) in headless runs.
- Emit JSON to `logs/YYYYMMDD/perf/perf.json`; gate reads P95s and compares baseline.

## Gate Policy
- Dev/CI soft gate: warn on regression >10%.
- Pre-release hard gate: fail on exceeding budgets or >5% regression vs baseline.

