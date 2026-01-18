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
- 口径冻结：`tile_id` 仅要求 map 内唯一；跨地图允许重复。
- 口径冻结：`layout:{x,y}` 必须在 `[0,1]`（归一化坐标、原点左上）；越界视为数据无效，禁止开始（硬失败）。
- 口径冻结：资源路径必须位于 `res://Assets/...` 子树内，扩展名白名单（.png/.webp/.svg）+ 大小上限（1MB）。
- 口径冻结：`action_id` 在同一 tile 内唯一；事件/日志引用使用 `(map_id, tile_id, action_id)` 组合。
- 口径冻结：地图索引与 tile 文本均使用 i18n（只存 key，不存展示文案）。
  - `_index.json`：`name_key` / `description_key` / `preview_image_res_path`
  - `<map_id>.json`：tile `name_key`（hover/选中时展示）、tile action `label_key`（如需）
  - i18n 文件：`res://Data/i18n/zh_cn.json`（缺 key 时允许降级显示 key，但需审计）

## 非目标
- 不定义复杂地图编辑器与热更新。

## 确定性输入
- `res://Data/maps/_index.json`
- `res://Data/maps/<map_id>.json`

## 契约（EventType + 触发点）
- 本任务不新增领域事件；地图数据仅作为 `core.sanguo.game.started` 等事件 payload 中的 `map_id` 与 UI 投影输入。
- 契约 SSoT（代码）：`Game.Core/Contracts/Sanguo/GameEvents.cs`
- 对齐页：`docs/architecture/overlays/PRD-SANGUO-T2/08/08-contracts-taskmap-t50-t65.md`

## 验收条款（ACC）
- ACC:T53.1 `_index.json` 可列出可用地图（map_id/name_key/path/version/recommended_players_min/max/description_key/preview_image_res_path）。
- ACC:T53.2 `<map_id>.json` 中每个 tile 有确定的 `tile_kind` 与 `name_key`；UI 能在 hover/选中时展示 name（缺 key 可降级显示 key 并审计）。

## Test-Refs
- `Game.Core.Tests/Tasks/Task53MapConfigTests.cs`
