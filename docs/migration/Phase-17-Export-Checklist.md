# Phase 17: Windows-only 导出清单（模板最小集）

> 目标：在 Windows 环境下，以最少步骤导出可运行 EXE，并完成基本冒烟。

## 前置 / Prerequisites
- 设置 `GODOT_BIN` 为 Godot .NET（mono）可执行文件路径。
- 在 Godot Editor 安装 Export Templates（Windows Desktop）。

## 快速步骤 / Quick Steps
- 运行测试（可选示例）：
  - `.\scripts\test.ps1 -GodotBin "$env:GODOT_BIN"`（默认不含示例；加 `-IncludeDemo` 开启）
- 导出 EXE：
  - `.\scripts\ci\export_windows.ps1 -GodotBin "$env:GODOT_BIN" -Output build\Game.exe`
- EXE 冒烟：
  - `.\scripts\ci\smoke_exe.ps1 -ExePath build\Game.exe -TimeoutSec 5`
- Headless 冒烟（不依赖导出）：
  - `.\scripts\ci\smoke_headless.ps1 -GodotBin "$env:GODOT_BIN" -TimeoutSec 5`

### One‑liner（已安装 Export Templates 前提）
- PowerShell：
  - ```powershell
    $env:GODOT_BIN='C:\\Godot\\Godot_v4.5.1-stable_mono_win64.exe'; ./scripts/ci/export_windows.ps1 -GodotBin "$env:GODOT_BIN" -Output build\Game.exe; ./scripts/ci/smoke_exe.ps1 -ExePath build\Game.exe
    ```

## 验证项 / Verification
- 日志标记优先（稳定探针）：`[TEMPLATE_SMOKE_READY]`（Main 场景 `_ready()` 已打印）
- 备选信号：`[DB] opened`（数据库就绪）
- 兜底：若无法采集日志，脚本视为“INCONCLUSIVE”但不阻断导出（模板级宽松标准）

## 模板安装说明 / Notes
- 官方 `export_templates.tpz` 有时包含顶层 `templates/` 目录；本仓库工作流会自动探测并从该目录复制。
- Godot 可能从 `4.5.1.stable` 或 `4.5.1.stable.mono` 目录读取模板；工作流会同时复制到两处（`templates/` 与 `export_templates/`）。
- 若 `--export-release` 失败，导出脚本会自动回退尝试 `--export-debug` 并输出 `--verbose` 日志以便定位问题。

## 环境变量 / Env
- `GODOT_BIN`：指向 Godot .NET（mono）可执行文件。
- `GODOT_DB_BACKEND=plugin|managed`：可控 DB 后端（默认插件优先）。
- `TEMPLATE_DEMO=1`：启用示例 UI 测试/场景（默认关闭）。

## 日志路径 / Logs
- 冒烟/测试日志：`logs/ci/YYYYMMDD-HHMMSS/**`
- 本地观测：
  - 安全基线：`user://logs/security/security-audit.jsonl`
  - 事件占位（Sentry）：`user://logs/sentry/events-YYYYMMDD.jsonl`
  - 性能：`user://logs/perf/perf.json`（控制台含 `[PERF] ... p95_ms=...`）
