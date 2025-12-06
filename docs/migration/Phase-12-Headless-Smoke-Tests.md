# Phase 12: Headless Smoke Tests / 无界面冒烟

> 目标：提供“导入即跑”的最小冒烟，验证模板在 Windows‑only 环境下可启动、可导出、可加载主场景。

## Headless 运行冒烟

- 命令：`./scripts/ci/smoke_headless.ps1 -GodotBin "$env:GODOT_BIN" [-Scene res://Game.Godot/Scenes/Main.tscn] [-TimeoutSec 5]`
- 判定标准（从高到低）：
  1) 捕获显式标记 `[TEMPLATE_SMOKE_READY]`（优先）；
  2) 捕获数据库就绪 `[DB] opened`；
  3) 否则任意输出即视为通过（模板级宽松判定）。

### GitHub Actions（Dry Run）
- 直接使用工作流：`.github/workflows/windows-smoke-dry-run.yml`
- 步骤：Checkout → Setup .NET → 下载 Godot .NET → 运行 GdUnit4 → Headless 冒烟（无导出）

## 导出 EXE 冒烟（Windows‑only）

1) 导出 EXE：`./scripts/ci/export_windows.ps1 -GodotBin "$env:GODOT_BIN" -Output build\Game.exe`
2) 运行冒烟：`./scripts/ci/smoke_exe.ps1 -ExePath build\Game.exe -TimeoutSec 5`

说明：
- 若使用插件后端（addons/godot-sqlite），请确保编辑器已安装导出模板；托管后备路径会随包带 `e_sqlite3`（模板已配置）。
- 冒烟脚本以“进程可启动 + 有基础输出”为通过标准，适合模板级验证；业务级验证请使用 Phase‑11 的集成测试。

## 提示 / Tips

- 更严格校验：Main 场景 `_ready()` 已打印 `[TEMPLATE_SMOKE_READY]` 探针标记，脚本已内置识别。
- `GODOT_DB_BACKEND=plugin|managed` 可控制 DB 后端；未设置默认为插件优先。
