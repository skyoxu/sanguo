---
PRD-ID: PRD-SANGUO-T2
Title: 08-T53 地图配置（多文件）与 Tile 语义
Status: Draft
ADR-Refs:
  - ADR-0019
Arch-Refs:
  - CH05
---

# T53：地图配置（多文件）与 Tile 语义

本页为 T53 的功能纵切拆页。配置只读来源与路径约束见 ADR-0019。

## 范围
- 地图列表索引：`res://Data/maps/_index.json`（用于 UI 列表渲染，不扫描目录）。
- 地图定义：`res://Data/maps/<map_id>.json`（`<map_id>` 必须与索引一致）。
- Tile 最小集合：`city` / `facility` / `event` / `empty`。
- 口径冻结：Core 只识别 `tile_kind = city | facility | event | empty`；当 `tile_kind=facility` 时必须给出 `facility_kind`（荒野/商店/战场/监狱/医院/职业所/传送点等）。
- 口径冻结：当前运行时仍按 `tiles[]` 的数组顺序映射 legacy `PositionIndex`；因此 `track.start_tile_id` 必须等于 `tiles[0].tile_id`（避免隐式漂移；全量 V2 运行时接入前不允许其它排列）。
- 口径冻结：`tile_id` 仅要求 map 内唯一；跨地图允许重复。
- 口径冻结：`layout:{x,y}` 必须在 `[0,1]`（归一化坐标、原点左上）；越界视为数据无效，禁止开始（硬失败）。
- 口径冻结：资源路径必须位于 `res://Assets/...` 子树内，扩展名白名单（.png/.webp/.svg）+ 大小上限（1MB）。
- 口径冻结：`action_id` 在同一 tile 内唯一；事件/日志引用使用 `(map_id, tile_id, action_id)` 组合。
- UI 必须显示 tile 的 `name`（来自 JSON 配置）。

## 非目标
- 不定义复杂地图编辑器与热更新。

## 确定性输入
- `res://Data/maps/_index.json`
- `res://Data/maps/<map_id>.json`

## 契约定义

### DTO
- **SanguoMapsCatalog**
  - 用途：新游戏地图列表索引（只读；不扫描目录）
  - 字段：`SchemaVersion`, `Version`, `Maps[]`（`MapId`, `NameKey`, `DescriptionKey`, `Path`, `RecommendedPlayersMin/Max`, `ContentVersion`, `PreviewResPath`）
  - 契约位置：`Game.Core/Contracts/Sanguo/SanguoMapsCatalog.cs`
- **SanguoMapDefinitionV2**
  - 用途：单张地图定义（多文件；只读）
  - 字段：`SchemaVersion`, `Version`, `MapId`, `Track(Length, StartTileId)`, `Tiles[]`
    - Tile 字段：`TileId`, `TileKind`, `NameKey`, `Layout(X,Y)`, `Actions[]({ActionId, IconResPath})`
    - kind=city：额外字段 `RegionId`, `City(BasePrice, BaseToll, AllowedBuildingIds[])`
    - kind=facility：额外字段 `FacilityId`
    - kind=event：额外字段 `EventPoolId`
  - 契约位置：`Game.Core/Contracts/Sanguo/SanguoMapDefinitionV2.cs`
- **SanguoMapDefinitionV2Validator**
  - 用途：地图契约级校验（确定性；不依赖引擎）
  - 契约位置：`Game.Core/Contracts/Sanguo/SanguoMapDefinitionV2Validator.cs`

## 验收条款（ACC）
- ACC:T53.1 `_index.json` 可列出可用地图（id/name/path）。
- ACC:T53.2 `<map_id>.json` 中每个 tile 有确定的 type 与 name；UI 能显示 name。

## Test-Refs
- `Game.Core.Tests/Tasks/Task53MapConfigParsingTests.cs`
- `Game.Core.Tests/Tasks/Task53MapConfigValidationTests.cs`
- `Tests.Godot/tests/Scenes/Sanguo/test_task53_sanguo_map_tile_name_fallback.gd`

