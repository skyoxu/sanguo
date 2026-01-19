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
- UI 必须显示 tile 的 `name`（来自 JSON 配置）。

## 非目标
- 不定义复杂地图编辑器与热更新。

## 确定性输入
- `res://Data/maps/_index.json`
- `res://Data/maps/<map_id>.json`

## 验收条款（ACC）
- ACC:T53.1 `_index.json` 可列出可用地图（id/name/path）。
- ACC:T53.2 `<map_id>.json` 中每个 tile 有确定的 type 与 name；UI 能显示 name。

## Test-Refs
- `Game.Core.Tests/Tasks/Task53MapConfigTests.cs`

