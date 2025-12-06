# Phase 6 Quickstart — Windows-only DB Setup

## 目标 / Goal
- 在 Windows 环境为 Godot + C# 项目就绪 SQLite 存储，配合 Phase 6 数据层迁移方案。

## 步骤 / Steps
- 安装 godot-sqlite 插件：将官方插件放入 `addons/godot-sqlite/`，在 Godot Editor → Project → Plugins 启用。
- 推荐的数据库路径：`user://data/game.db`（首次运行不存在则创建并执行 schema）。
- 初始化 Schema：使用 `scripts/db/schema.sql` 作为建表脚本（包含 `users/saves/statistics/schema_version/achievements/settings`）。
- 性能/安全建议：`PRAGMA foreign_keys=ON; PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL`。

## 代码接入 / Code Integration（后续）
- 适配器：`Game.Godot/Adapters/SqliteDataStore.cs`（当前为占位；启用插件后对接 API）。
- 端口：`Game.Core/Ports/ISqlDatabase.cs`（Open/Close/Execute/Query/Tx）。
- Autoload：不强制；建议由场景入口或服务定位器按需创建并保持存活。

## 注意 / Notes
- 本方案为 Windows-only；保持与 Editor 的 .NET 版本一致（例如 `GodotGame.csproj` 目标 SDK 与 Godot 4.5 .NET 对齐）。
- 若未安装插件，适配器会抛出 `NotSupportedException`，属于预期的占位保护。

## 导出注意事项 / Export Notes

- 插件优先：存在 `addons/godot-sqlite` 且启用时，运行/导出使用插件后端；控制台日志含 `[DB] backend=plugin`。
- 托管后备：无插件时，使用 Microsoft.Data.Sqlite；控制台日志含 `[DB] backend=managed`。
- e_sqlite3：托管后备导出 EXE 需包含本机库，工程已添加 `SQLitePCLRaw.bundle_e_sqlite3`，通常无需额外操作。
- 导出脚本：`scripts/ci/export_windows.ps1` 会提示所用后端；若导出失败，请先在 Editor 安装 Export Templates。

## 日志观察 / Logging

- 启动时 `Main.gd` 输出：`[DB] opened at user://data/game.db`（成功）或 `open failed: <LastError>`（失败）。
- 适配器在 Open 时输出后端：`[DB] backend=plugin (godot-sqlite)` 或 `[DB] backend=managed (Microsoft.Data.Sqlite)`。

## Backend 选择 / Backend Override

- 环境变量 `GODOT_DB_BACKEND` 可覆盖后端选择：`plugin`（仅插件）/ `managed`（仅托管）/ 未设置（插件优先）。
- 仅插件模式：若未安装 `addons/godot-sqlite`，将抛出错误（便于在 CI 中强制校验）。
- 默认（推荐）：插件优先，未安装插件时自动回退到 Microsoft.Data.Sqlite。

