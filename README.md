[![Windows Export Slim](https://github.com/skyoxu/sanguo/actions/workflows/windows-export-slim.yml/badge.svg)](https://github.com/skyoxu/sanguo/actions/workflows/windows-export-slim.yml) [![Windows Release](https://github.com/skyoxu/sanguo/actions/workflows/windows-release.yml/badge.svg)](https://github.com/skyoxu/sanguo/actions/workflows/windows-release.yml) [![Windows Quality Gate](https://github.com/skyoxu/sanguo/actions/workflows/windows-quality-gate.yml/badge.svg)](https://github.com/skyoxu/sanguo/actions/workflows/windows-quality-gate.yml)

# Godot Windows-only Template (C#)

即开即用，可复制的 Godot 4 + .NET（Windows-only）项目模板。


## 3‑Minute From Zero to Export（3 分钟从 0 到导出）

1) 安装 Godot .NET（mono）并设置环境：
   - `setx GODOT_BIN C:\Godot\Godot_v4.5.1-stable_mono_win64.exe`
2) 运行最小测试与冒烟（可选示例）：
   - `./scripts/test.ps1 -GodotBin "$env:GODOT_BIN"`（默认不含示例；`-IncludeDemo` 可启用）
   - `./scripts/ci/smoke_headless.ps1 -GodotBin "$env:GODOT_BIN"`
3) 在 Godot Editor 安装 Export Templates（Windows Desktop）。
4) 导出与运行 EXE：
   - `./scripts/ci/export_windows.ps1 -GodotBin "$env:GODOT_BIN" -Output build\Game.exe`
   - `./scripts/ci/smoke_exe.ps1 -ExePath build\Game.exe`

One‑liner（已在 Editor 安装 Export Templates 后）：
- PowerShell：`$env:GODOT_BIN='C:\\Godot\\Godot_v4.5.1-stable_mono_win64.exe'; ./scripts/ci/export_windows.ps1 -GodotBin "$env:GODOT_BIN" -Output build\Game.exe; ./scripts/ci/smoke_exe.ps1 -ExePath build\Game.exe`

## What You Get（模板内容）
- 适配层 Autoload：EventBus/DataStore/Logger/Audio/Time/Input/SqlDb
- 场景分层：ScreenRoot + Overlays；ScreenNavigator（淡入淡出 + Enter/Exit 钩子）
- 安全基线：仅允许 `res://`/`user://` 读取，启动审计 JSONL，HTTP 验证示例
- 可观测性：本地 JSONL（Security/Sentry 占位），性能指标（[PERF] + perf.json）
- 测试体系：xUnit + GdUnit4（示例默认关闭），一键脚本
- 导出与冒烟：Windows-only 脚本与文档

## Quick Links
- 文档索引：`docs/PROJECT_DOCUMENTATION_INDEX.md`
- Godot+C# 快速开始（sanguo 项目）：`docs/TEMPLATE_GODOT_GETTING_STARTED.md` 
- Windows-only 快速指引：`docs/migration/Phase-17-Windows-Only-Quickstart.md`
- FeatureFlags 快速指引：`docs/migration/Phase-18-Staged-Release-and-Canary-Strategy.md`
- 导出清单：`docs/migration/Phase-17-Export-Checklist.md`
- Headless 冒烟：`docs/migration/Phase-12-Headless-Smoke-Tests.md`
- Actions 快速链路验证（Dry Run）：`.github/workflows/windows-smoke-dry-run.yml`
- 场景设计：`docs/migration/Phase-8-Scene-Design.md`
- 测试体系：`docs/migration/Phase-10-Unit-Tests.md`
- 安全基线：`docs/migration/Phase-14-Godot-Security-Baseline.md`
- 手动发布指引：`docs/release/WINDOWS_MANUAL_RELEASE.md`
- Release/Sentry 软门禁与工作流说明：`docs/workflows/GM-NG-T2-playable-guide.md`

## 代码质量工具

### 测试命名验证脚本

自动验证所有测试方法遵循 PascalCase 命名规范，防止 snake_case 命名回退。

**脚本位置**：`scripts/python/check_test_naming.py`

**使用方法**：
```powershell
# 扫描所有测试文件并验证命名规范
py -3 scripts/python/check_test_naming.py
```

**输出示例**：
```
# 无违规（返回码 0）
Scanning Game.Core.Tests for test method naming violations...
Test directory: C:\buildgame\sanguo\Game.Core.Tests

[OK] All test methods follow PascalCase naming convention
[OK] No violations found

# 发现违规（返回码 1）
[FAIL] Test naming violations found:

Game.Core.Tests\Services\ExampleTests.cs:
  Line 12: my_test_method (should be PascalCase, found snake_case or other pattern)
  Line 25: another_bad_name (should be PascalCase, found snake_case or other pattern)

Total violations: 2
```

**CI/CD 集成**：
- 脚本在发现违规时返回错误码 1，可直接集成到 CI 流水线
- 推荐在 `git commit` 或 `git push` 前运行此脚本
- 相关 ADR：ADR-0021 (C# Domain Layer Architecture)

**验证规则**：
- 检查所有 `*Tests.cs` 文件
- 验证标记为 `[Fact]` 或 `[Theory]` 的测试方法
- 方法名必须为纯 PascalCase（首字母大写，无下划线）
- 示例：`MyTestMethod()` ✅ | `my_test_method()` ❌

## Notes
- DB 后端：默认插件优先；`GODOT_DB_BACKEND=plugin|managed` 可控。
- 示例 UI/测试：默认关闭；设置 `TEMPLATE_DEMO=1` 启用（Examples/**）。

## 仓库名与内部项目名对应关系（sanguo）

- GitHub 仓库名：`skyoxu/sanguo` —— 对外链接、Actions badge、协作入口统一使用此名，表示“三国”主题的 Windows-only Godot + C# 游戏项目。
- Godot 主工程：`GodotGame.csproj` / `GodotGame.sln` —— 仍沿用从模板仓库 godotgame 继承的主工程命名，CI 构建命令中继续使用 `GodotGame` 作为 Godot .NET 入口工程标识。
- 领域与适配层工程：`Game.Core`、`Game.Godot`、`Game.Core.Tests`、`Game.Godot.Tests` 等 —— 负责领域逻辑、Godot 适配层与对应的 xUnit/GdUnit4 测试工程，命名与 godotgame/newguild 系列保持一致，便于脚本与质量门禁复用。
- 源模板与派生关系约定：文档或脚本中提到 “godotgame” 时，指通用模板仓库；提到 “sanguo” 时，指当前这个以“三国”为主题的派生仓库；提到 `GodotGame` 时，指本仓库内部的 Godot .NET 主工程文件，而不是另一个独立仓库。迁移背景与数据存储/路径安全等口径以 `docs/adr/ADR-0006-data-storage.md` 为准。
- 使用建议：在需要复用模板能力（CI 工作流、质量门禁脚本、Godot 配置）但希望做业务层改造时，优先 fork/克隆 `sanguo` 仓库而不是直接从 `godotgame` 起步，这样可以在保留“三国”游戏骨架的前提下继续享受 Windows-only Godot + C# 模板的更新。

## Feature Flags（特性旗标）
- Autoload：`/root/FeatureFlags`（文件：`Game.Godot/Scripts/Config/FeatureFlags.cs`）
- 环境变量优先生效：
  - 单项：`setx FEATURE_demo_screens 1`
  - 多项：`setx GAME_FEATURES "demo_screens,perf_overlay"`
- 文件配置：`user://config/features.json`（示例：`{"demo_screens": true}`）
- 代码示例：`if (FeatureFlags.IsEnabled("demo_screens")) { /* ... */ }`

## 如何发版（打 tag）
- 确认主分支已包含所需变更：`git status && git push`
- 创建版本标签：`git tag v0.1.1 -m "v0.1.1 release"`
- 推送标签触发发布：`git push origin v0.1.1`
- 工作流：`Windows Release (Tag)` 自动导出并将 `build/Game.exe` 附加到 GitHub Release。
- 如需手动导出：运行 `Windows Release (Manual)` 或 `Windows Export Slim`。

## 自定义应用元数据（图标/公司/描述）
- 文件：`export_presets.cfg` → `[preset.0.options]` 段。
- 关键字段：
  - `application/product_name`（产品名），`application/company_name`（公司名）
  - `application/file_description`（文件描述），`application/*_version`（版本）
  - 图标：`application/icon`（推荐 ICO：`res://icon.ico`；当前为 `res://icon.svg`）
- 修改后，运行 `Windows Export Slim` 或 `Windows Release (Manual)` 验证导出产物。
