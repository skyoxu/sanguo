# Windows‑only 快速指引补充 / Quickstart Addendum

## 导出模板安装 / Install Export Templates
- 路径 / Path: Editor → Export → Manage Export Templates
- 选择与当前 Godot 版本完全匹配的官方模板（.NET/mono 版）。
- 验证 / Verify: Project → Export 能选择 “Windows Desktop”，导出不再提示缺少模板。

## 常见错误速查 / Troubleshooting
- 未安装 Export Templates → 导出时报 “no export templates installed”。按上节安装模板。
- 未设置 `GODOT_BIN` → 脚本找不到 Godot。设置：`$env:GODOT_BIN = 'C:\Godot\Godot_v4.5.1-stable_mono_win64.exe'`（按实际版本替换）。
- Godot .NET SDK 版本不匹配 → 若出现 “Godot.NET.Sdk not found / incompatible”，将 `GodotGame.csproj` 的 `Sdk="Godot.NET.Sdk/<version>"` 与安装的 Godot .NET 版本对齐（例如 4.5.x）。
- Headless 模式 UI/音频不稳定 → 仅跑 DataStore/ResourceLoader/EventBus 等无 UI/音频依赖的测试。

