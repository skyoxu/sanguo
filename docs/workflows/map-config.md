# 地图配置（Sanguo Map JSON V2）

> 本文说明当前版本地图 JSON 的字段含义、引用路径，以及在不改代码/改代码情况下如何调整地图布局与表现。

## 读取链路（当前默认）

1. `Data/packs/_index.json`
2. `Data/packs/<packId>/pack.json`
3. `Data/packs/<packId>/maps/_index.json`
4. `Data/packs/<packId>/maps/<mapId>.json`

当前默认内容包与地图：
- Pack：`core_t2`
- Map：`map001`
- 入口：`Data/packs/core_t2/maps/map001.json`

> 旧路径 `Data/maps/**` 仅作为回退，不建议继续编辑。

## 文件路径索引（字段值引用来源）

以下路径均来自 `Data/packs/core_t2/pack.json`：
- i18n：`res://Data/packs/core_t2/i18n/zh_cn.json`、`res://Data/packs/core_t2/i18n/en_us.json`
- Regions：`res://Data/packs/core_t2/regions.json`
- Buildings：`res://Data/packs/core_t2/buildings.json`
- Facilities：`res://Data/packs/core_t2/facilities.json`
- Events（随机池）：`res://Data/packs/core_t2/random_events.json`
- Cards：`res://Data/packs/core_t2/action_cards.json`
- Relics：`res://Data/packs/core_t2/relics.json`
- Characters：`res://Data/packs/core_t2/characters.json`

## 地图索引（`maps/_index.json`）字段说明

- `schemaVersion`：索引 schema 版本。
- `version`：索引版本（内容变更建议 bump）。
- `maps[]`：地图条目列表。
  - `mapId`：地图 ID。
  - `nameKey` / `descriptionKey`：i18n key（来自 pack i18n）。
  - `path`：地图 JSON 路径。
  - `previewImagePath`：预览图资源路径。
  - `recommendedPlayersMin/Max`：推荐玩家数量范围。
  - `contentVersion`：对应地图文件的版本号（与地图 JSON 的 `version` 对齐）。

## 地图文件（`maps/<mapId>.json`）字段说明

- `schemaVersion`：地图 schema 版本。
- `version`：地图版本（改动后建议 bump，并同步 `contentVersion`）。
- `mapId`：地图 ID。
- `track`：轨道定义。
  - `length`：轨道长度（格子数量）。
  - `startTileId`：起始格子 ID。
- `tiles[]`：格子定义（每格一条）。
  - `tileId`：格子 ID（唯一）。
  - `tileKind`：格子类型（如 `city` / `empty` / `event` / `facility`）。
  - `nameKey`：格子名称 i18n key。
  - `regionId`：州郡 ID（仅 `city` 类型使用）。
  - `eventPoolId`：事件池 ID（仅 `event` 类型使用）。
  - `facilityId`：设施 ID（仅 `facility` 类型使用）。
  - `city`：城池配置（仅 `city` 类型使用）。
    - `basePrice`：地价基准。
    - `baseToll`：过路费基准。
    - `allowedBuildingIds`：可建建筑 ID 列表。
  - `layout`：布局坐标（归一化）。
    - `x` / `y`：范围 [0,1]，左上为 (0,0)。
  - `actions[]`：可执行动作列表。
    - `actionId`：动作 ID。
    - `iconResPath`：动作图标资源路径。

## 修改指南（面向当前实现）

### 1) 格子坐标、尺寸、间隔

**当前渲染逻辑不使用 `layout.x/y`**，而是由 `SanguoBoardLayout` 自动计算方形/线性布局。

- 修改坐标原点：在 `Game.Godot/Scenes/Sanguo/SanguoBoardView.tscn` 中调整 `Origin`（Inspector）。
- 修改格子间距：调整 `StepPixels`（格子中心间距）。
- 格子尺寸：由 `SanguoBoardTileOverlay` 计算，约为 `StepPixels * 0.35`，且夹在 `[6, 24]`。

如果你希望 **直接使用 JSON 的 `layout.x/y`** 进行布局，需要在 `SanguoBoardLayout.GetBasePositionForIndex` 中改为读取地图坐标并映射到像素坐标（例如使用地图宽高、缩放系数）。

### 2) 直角转弯格子 & 角色按格子移动

- 直角转弯由 `UseSquareLayout = true` 时的自动环绕布局提供（见 `SanguoBoardLayout`）。
- 角色移动走格子序列（非两点直线）：`SanguoTokenAnimator.MoveAlongPath` 会按索引逐格移动。

如果要让 **自定义布局** 也保持直角路径：
- 在地图中添加足够多的“转角格子”；
- 或让 `GetBasePositionForIndex` 返回的坐标本身是直角折线（每一步坐标变化只在 x 或 y 维度）。

### 3) 格子图标与地名

- 地名来自 `tiles[].nameKey`，对应 pack i18n 文件中的条目。
- 动作图标来自 `tiles[].actions[].iconResPath`。

当前格子本身没有图标字段。如需格子图标：
1. 在 `tiles[]` 增加 `iconResPath`。
2. 在 `SanguoBoardTileOverlay.EnsureTiles` 中为每格添加 `Sprite2D/TextureRect` 并加载该资源。

### 4) 鼠标滑过高亮与说明层

建议实现方案：
1. 在 `SanguoBoardView._UnhandledInput` 或 `_Process` 中读取鼠标坐标（`GetViewport().GetMousePosition()`）。
2. 通过 `SanguoBoardLayout.GetBasePositionForIndex` 计算各格中心，找到最近格子并记录 `hoverIndex`。
3. 在 `SanguoBoardTileOverlay` 添加 `SetHoverIndex(int index)`：
   - 将 hover 格子的颜色调亮（或加描边）。
4. 增加一个 `Panel/Label` 作为 tooltip，显示 `nameKey` 翻译 + 简要说明字段。

为了避免频繁刷新，可在 hover 变化时才更新 UI。

## map001 的正确编辑方式

1. 修改 `Data/packs/core_t2/maps/map001.json`。
2. 若内容发生变更：
   - bump `map001.json` 的 `version`。
   - 同步修改 `Data/packs/core_t2/maps/_index.json` 中对应条目的 `contentVersion`。
3. 若新增 i18n key：更新 `Data/packs/core_t2/i18n/zh_cn.json` 与 `en_us.json`。

## 关键文件参考

- 视图与布局：`Game.Godot/Scripts/Sanguo/SanguoBoardView.cs`
- 布局逻辑：`Game.Godot/Scripts/Sanguo/SanguoBoardLayout.cs`
- 格子渲染：`Game.Godot/Scripts/Sanguo/SanguoBoardTileOverlay.cs`
- 地图加载：`Game.Godot/Scripts/Sanguo/SanguoMapConfigLoader.cs`
## 变更提醒：eventPools.nameKey（新增硬门禁）

从当前版本开始，`random_events.json` 的每个 `eventPools[]` 必须包含 `nameKey`，否则内容门禁会失败。

**示例**
```json
{
  "poolId": "default",
  "nameKey": "event_pool.default.name",
  "eventIds": ["event_x", "event_y"]
}
```

**i18n 对应键**
- `event_pool.default.name`
- `event_pool.global.name`

若你维护自定义内容包，请同步补齐：
- `Data/packs/<packId>/random_events.json` 的 `nameKey`
- `Data/packs/<packId>/i18n/zh_cn.json` 与 `en_us.json`