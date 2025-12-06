# Phase 18: Staged Release & Canary Strategy（模板最小集）
## Goals

- Keep Windows-only packaging simple and repeatable with staged rollout.
- Use quality gate + smoke as go/no-go, optional perf budget.

---

## Template Landing（Windows-only）

- Quality Gate（pre-release check）
  - `./scripts/ci/quality_gate.ps1 -GodotBin "$env:GODOT_BIN" -WithExport -PerfP95Ms 20`
  - Steps：dotnet tests → GdUnit4 tests → headless smoke → export → EXE smoke → perf budget（可选）
- Artifacts
  - EXE：`build/Game.exe`
  - Logs：`logs/ci/YYYYMMDD-HHMMSS/**`
- Release Notes（模板）
  - 生成：`./scripts/ci/generate_release_notes.ps1 -Output docs/release/RELEASE_NOTES-<date>.md`
  - 参考：`docs/release/RELEASE_NOTES_TEMPLATE.md`

---

## Canary（特性旗标最小策略）

- FeatureFlags（可选 Autoload）：`Game.Godot/Scripts/Config/FeatureFlags.cs`
  - 配置文件：`user://config/features.json`（例：`{"demo_screens": true}`）
  - 环境变量覆盖：`FEATURE_<NAME>=1|0`
- 建议：将风险点用 Flag 包裹；先在 QA/内测群体启用，再逐步放开。

### FeatureFlags 快速指引 / Quickstart（Windows-only）

- 启用方式（环境变量优先生效）
  - 单项：`setx FEATURE_demo_screens 1`
  - 多项：`setx GAME_FEATURES "demo_screens,perf_overlay"`
- 配置文件位置：`user://config/features.json`（示例：`{"demo_screens": true}`）
- 代码示例（C#）：
  - `if (FeatureFlags.IsEnabled("demo_screens")) { /* 启用演示界面 */ }`
- 常见用途：
  - 保护实验性 UI/导航路径；
  - 控制性能 HUD、观测开关；
  - 渐进放量（Canary）与回滚开关。

---

## CI / Actions（Windows）

- 质量门禁：`.github/workflows/windows-quality-gate.yml`（手动触发）
- 发行（示例）：`.github/workflows/windows-release.yml`（手动导出 + 上传 EXE Artifact）

---

## Notes

- Windows-only 模板不包含商店分发；假定人工或内部分发渠道。
- 代码签名建议单独配置，在导出后执行签名脚本。

