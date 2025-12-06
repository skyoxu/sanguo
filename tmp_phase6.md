# Phase 6 Quickstart 鈥?Windows-only DB Setup

鐩爣/Goal
- 鍦?Windows 鐜涓?Godot + C# 椤圭洰鍑嗗 SQLite 瀛樺偍锛岄伒寰?Phase鈥? 杩佺Щ鏂规銆?
姝ラ/Steps
- 瀹夎 godot-sqlite 鎻掍欢锛氬皢瀹樻柟鎻掍欢鏀惧叆 `addons/godot-sqlite/` 骞跺湪 Godot Editor 鈫?Project 鈫?Plugins 鍚敤銆?- 寤鸿鐨勬暟鎹簱璺緞锛歚user://data/game.db`锛堥娆¤繍琛屾椂鑻ヤ笉瀛樺湪锛屽垱寤哄苟鎵ц schema锛夈€?- 鍒濆鍖?Schema锛氫娇鐢?`scripts/db/schema.sql` 浣滀负寤鸿〃鑴氭湰锛堝寘鍚?users/saves/statistics/schema_version/achievements/settings锛夈€?- 鎬ц兘/瀹夊叏寤鸿锛歚PRAGMA foreign_keys=ON; PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL`銆?
浠ｇ爜鎺ュ叆/Code Integration锛堝悗缁級
- 閫傞厤鍣細`Game.Godot/Adapters/SqliteDataStore.cs`锛堝綋鍓嶄负鍗犱綅锛屽惎鐢ㄦ彃浠跺悗瀵规帴 API锛夈€?- 绔彛锛歚Game.Core/Ports/ISqlDatabase.cs`锛圤pen/Close/Execute/Query/Tx锛夈€?- Autoload锛氫笉寮哄埗锛涘缓璁敱鍦烘櫙鍏ュ彛鎴栨湇鍔″畾浣嶅櫒鎸夐渶鍒涘缓骞舵寔鏈夈€?
娉ㄦ剰/Notes
- 鏈ā鏉?Windows鈥憃nly锛涗繚鎸佷笌 Editor 鐨?.NET 鐗堟湰涓€鑷达紙`GodotGame.csproj` Sdk=4.5.x锛夈€?- 鑻ユ湭瀹夎鎻掍欢锛岄€傞厤鍣ㄤ細鎶涘嚭 NotSupportedException锛岃繖鏄鏈熺殑鍗犱綅琛屼负銆?

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



