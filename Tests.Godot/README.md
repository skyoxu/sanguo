# Tests.Godot（测试工程）与 `Game.Godot` 的单一事实源

本仓库是 Windows only 项目。为避免“测试跑的是旧副本/假绿”的风险，测试工程不再维护 `Tests.Godot/Game.Godot/**` 的镜像拷贝。

取而代之，要求在 Windows 上使用 **目录 Junction**（单一事实源）：

- `Tests.Godot/Game.Godot` → `<repo>/Game.Godot`
- `Tests.Godot/Data` → `<repo>/Data`
- `Tests.Godot/Assets` → `<repo>/Assets`

## 一次性准备（本地）

在仓库根目录执行：

`py -3 scripts/python/ensure_tests_project_junction.py --project Tests.Godot --migrate`

该脚本会把已有的非 junction 目录（若存在）迁移为备份目录，并创建 junction。
执行日志会写入 `logs/ci/<YYYY-MM-DD>/ensure-tests-project-junction/`。

## CI / 运行测试

`scripts/python/run_gdunit.py` 会在运行 GdUnit 前强制校验/创建 junction；若失败会直接失败，避免测试跑偏。

## 重要约束

- 不要把 `Tests.Godot/Game.Godot/**` 加入 git（已在 `.gitignore` 中忽略）。
- 不要把 `Tests.Godot/Data/**` 与 `Tests.Godot/Assets/**` 加入 git（已在 `.gitignore` 中忽略）。
- 如果你直接用 Godot 打开 `Tests.Godot` 工程，先运行一次上述脚本，确保 junction 存在。

