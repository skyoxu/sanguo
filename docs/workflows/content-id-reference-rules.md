# ID 与引用一致性规则（T2 数据门禁）

本规范定义 **ID 唯一性** 与 **跨表引用一致性** 的硬规则。
适用范围：`Data/**` 的最小可玩闭环内容（T50–T65）。

## 总则

- **ID 格式**：`^[a-z0-9_]{1,32}$`，禁止 Windows 保留名。
- **唯一性范围**：每张表内唯一（同表不可重复），跨表允许复用。
- **空值禁止**：所有 `id` 字段与引用字段均不得为空字符串。
- **失败即阻断**：任何 ID/引用错误属于 `data_invalid`，禁止开始。

## 表内唯一性（硬门禁）

| 文件 | 字段 | 规则 |
|---|---|---|
| `Data/maps/_index.json` | `maps[].mapId` | 唯一 |
| `Data/maps/<map_id>.json` | `tiles[].tileId` | map 内唯一 |
| `Data/characters.json` | `characters[].characterId` | 唯一 |
| `Data/random_events.json` | `eventPools[].poolId` | 唯一 |
| `Data/random_events.json` | `events[].eventId` | 唯一 |
| `Data/action_cards.json` | `cards[].cardId` | 唯一 |
| `Data/buildings.json` | `buildings[].buildingId` | 唯一 |
| `Data/relics.json` | `relics[].relicId` | 唯一 |
| `Data/regions.json` | `regions[].regionId` | 唯一 |
| `Data/facilities.json` | `facilities[].facilityId` | 唯一 |
| `Data/facilities.json` | `facilities[].actions[].actionId` | 设施内唯一 |
| `Data/maps/<map_id>.json` | `tiles[].actions[].actionId` | tile 内唯一 |

## 跨表引用一致性（硬门禁）

### 地图索引 → 地图文件
- `maps[].path` 必须存在且被 git 跟踪。
- 地图文件内 `mapId` 必须与索引条目的 `mapId` 一致。

### 地图 tile → 其他表
- `tiles[].regionId` 必须存在于 `regions[].regionId`。
- `tiles[].city.allowedBuildingIds[]` 必须存在于 `buildings[].buildingId`。
- `tiles[].facilityId` 必须存在于 `facilities[].facilityId`。
- `tiles[].eventPoolId` 必须存在于 `eventPools[].poolId`。

### 设施 → 地图 tile（动作一致）
- 对应 `facilityId` 的 `actions[].actionId` 必须覆盖 tile 的 `actions[].actionId`。
- 若设施无 actions，则 tile 不得配置 actions。

### 事件池 → 事件定义
- `eventPools[].eventIds[]` 必须全部存在于 `events[].eventId`。
- `poolId=global` 不允许包含 `startCombat` 事件。

## 说明

- 跨表 ID **不要求** 全局唯一，仅要求在各自表内唯一。
- 任何引用失效或重复都会阻断加载，避免“启动后才暴露”的数据问题。

## 口径引用

- ADR-0004：事件命名与契约口径。
- ADR-0005：质量门禁与 CI 约束。
- ADR-0019：资源与路径安全基线。
