# 地图配置（Sanguo Map JSON）

本项目支持通过 **JSON** 配置棋盘地图（格子数量、格子类型与城市经济参数）。当前实现优先读取 `user://` 的玩家覆盖文件；不存在或非法时回退到 `res://` 的默认配置。

## 读取优先级

1. `user://config/sanguo/map.json`（覆盖文件）
2. `res://Game.Godot/Assets/Config/Sanguo/map-default.json`（默认文件）

> 安全基线：只允许 `res://` 与 `user://`，并记录 `security-audit.jsonl` 便于排障取证。

## JSON 结构（字段说明）

顶层：
- `mapId`：地图编号（字符串，必填）
- `tileCount`：格子总数（整数，必填，>0）
- `tiles`：格子定义数组（必填，长度必须等于 `tileCount`）

每个 `tiles[]`：
- `positionIndex`：格子索引（整数，必填，范围 `0..tileCount-1`，且不可重复）
- `tileType`：格子类型（字符串，必填）：`city` / `pass` / `wild`
- `tileId`：格子ID（字符串，必填，全局唯一）
- `name`：显示名（字符串，必填）
- `stateId`：州/区域编号（字符串，必填；会映射到 Core 的 `City.RegionId`）
- `purchasePrice`：购买价格（数字，必填，>=0；仅 `city` 生效）
- `tollPrice`：过路费（数字，必填，>=0；仅 `city` 生效）
- `actions`：事件占位（字符串数组，可选；当前不驱动玩法，仅用于配置表达）

## 当前玩法影响（重要）

- `city`：会被映射为 `Game.Core.Domain.City`，参与买地/过路费逻辑。
- `pass` / `wild`：目前属于占位类型；Core 层暂不产生额外玩法效果（后续任务再接入“进入战场/随机事件”等）。

## 示例

默认示例文件见：
- `Game.Godot/Assets/Config/Sanguo/map-default.json`

