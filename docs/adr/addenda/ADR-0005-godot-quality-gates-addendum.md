---
adr: ADR-0005
title: Addendum — Quality Gates for Godot+C# Stack
date: 2025-11-08
status: Active
scope: Windows-only CI, Godot 4.5 (.NET)
---

# Addendum to ADR-0005: Quality Gates (Godot Alignment)

## Context
Move from Electron/Vitest/Playwright gates to Godot+C# (xUnit + GdUnit4) while preserving single-entry orchestration and artifact collection.

## Decisions
- Unit tests: `dotnet test` with coverlet; enforce Lines ≥ 90%, Branches ≥ 85%.
- Scene tests: run via GdUnit4 CLI; treat non-zero exit as failure; collect HTML/JUnit under `reports/`.
- Single entrypoint (Windows): a `guard:ci` task (PowerShell/NPM) orchestrates build, unit, scene, duplication (jscpd), and dependency audit.
- Logs: write consolidated artifacts/logs to `logs/YYYYMMDD/{unit|scene|e2e|perf}/`.
- Gate policy: fail-fast on coverage/scene regression; performance gates per ADR-0015 addendum.

## Commands (examples)
- `dotnet test --collect:"XPlat Code Coverage"`
- `"%GODOT_BIN%" --path . -s -d res://addons/gdUnit4/bin/GdUnitCmdTool.gd -a res://tests`
- `jscpd --pattern "**/*.{cs,gd}" --threshold 3`

## Verification
- CI shows coverage summary + GdUnit4 pass/fail; artifacts uploaded from `reports/` and `logs/`.

