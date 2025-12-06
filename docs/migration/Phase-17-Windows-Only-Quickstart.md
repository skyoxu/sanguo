# Phase 17 快速上手 — Windows-only（最终交付）

本页提供在 Windows 环境下“本地运行/测试/导出/CI”的最小可行指引，配合 Phase‑16（可观测性）、Phase‑17（构建与导出）、Phase‑18（分阶段发布）形成闭环。

## 1) 本地运行与测试（Windows）
- 环境变量（必要时，确保 .NET CLI 在 PATH 前缀）
  - PowerShell: `$env:Path = "$env:USERPROFILE\.dotnet;" + $env:Path`
- 运行 GdUnit4 测试（headless）
  - `./scripts/ci/run_gdunit_tests.ps1 -GodotBin "$env:GODOT_BIN"`
- 运行演示场景（非 headless）
  - `"$env:GODOT_BIN" --path . --scene "res://Game.Godot/Scenes/Main.tscn"`

## 2) 导出 Windows 可执行
- 预设：`export_presets.cfg` 已包含 “Windows Desktop”，输出 `build/Game.exe`
- 命令：
  - `./scripts/ci/export_windows.ps1 -GodotBin "$env:GODOT_BIN" -Output build\Game.exe`
- 模板：需在 Godot Editor 安装 Windows Export Templates（Editor → Export → Manage Export Templates）

## 3) CI（GitHub Actions / Windows）
- 工作流：`.github/workflows/windows-ci.yml`
- 步骤概览：安装 .NET → 下载 Godot .NET → 运行 GdUnit4 → 导出 .exe → 上传 `build/Game.exe` 与 `logs/ci/**`
- 轻量导出流（可选）：`.github/workflows/windows-export-slim.yml`

## 4) 路径与注意事项
- `user://` 映射：`%APPDATA%\Godot\app_userdata\<项目名>`（项目名来自 `project.godot` 的 `application/config/name`）
- Headless 提示：UI/音频在 headless 下不稳定；优先验证 DataStore/ResourceLoader/Signals
- Autoload 单例：`project.godot` 已注册 `EventBus / DataStore / Logger / Audio / Time / Input`，在场景中可通过 `/root/<Name>` 访问

## 5) 常用命令（Windows-only）
- 测试：`.\scripts\ci\run_gdunit_tests.ps1 -GodotBin "$env:GODOT_BIN"`
- 导出：`.\scripts\ci\export_windows.ps1 -GodotBin "$env:GODOT_BIN" -Output build\Game.exe`
- 烟测（headless）：`.\scripts\ci\smoke_headless.ps1 -GodotBin "$env:GODOT_BIN"`
- 烟测（exe）：`.\scripts\ci\smoke_exe.ps1 -ExePath build\Game.exe`

## 6) 与相关 Phase 的衔接
- Phase‑16（可观测性与发布健康）：建议在构建产物中启用 Sentry Releases + Sessions，CI 校验 Crash‑Free 指标
- Phase‑17（构建与导出）：详见 `Phase-17-Build-System-and-Godot-Export.md` 与 `Phase-17-Export-Checklist.md`，本页为最小跑通版
- Phase‑18（分阶段发布/金丝雀）：结合导出产物与 Release Health，在 Canary/Beta/Stable 分阶段推进

