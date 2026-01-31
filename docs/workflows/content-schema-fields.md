# 内容字段清单与范围约束（T2 最小集）

本清单用于统一内容字段的最低要求与取值范围，作为数据门禁与内容制作基线。
适用范围：Data/** 下的最小可玩闭环内容。

## 通用规范

- schemaVersion：整数，固定为 1。
- ersion：整数，必须 >= 1，内容变更必须递增。
- id：^[a-z0-9_]{1,32}$，禁止 Windows 保留名（例如 con）。
- i18n：
ameKey/descriptionKey 必须同时存在于 zh-CN 与 en-US。
- 资源路径：只允许 
es://Assets/，扩展名白名单 .png/.webp/.svg，大小 <=1MB。
- 坐标：layout.x/layout.y 必须在 [0,1]。

## 地图索引（Data/maps/_index.json）

| 字段 | 类型 | 必填 | 约束/说明 |
|---|---|---|---|
| schemaVersion | int | 是 | 固定 1 |
| version | int | 是 | >=1 |
| maps | array | 是 | 非空 |
| maps[].mapId | string | 是 | id 规范 |
| maps[].nameKey | string | 是 | i18n key（双语） |
| maps[].descriptionKey | string | 是 | i18n key（双语） |
| maps[].path | string | 是 | 
es://Data/maps/<file>.json |
| maps[].previewImagePath | string | 是 | 资源路径安全约束 |
| maps[].recommendedPlayersMin | int | 是 | [4,8] |
| maps[].recommendedPlayersMax | int | 是 | [4,8] 且 min<=max |
| maps[].contentVersion | int | 是 | >=1 |

## 地图文件（Data/maps/<map_id>.json）

| 字段 | 类型 | 必填 | 约束/说明 |
|---|---|---|---|
| schemaVersion | int | 是 | 固定 1 |
| version | int | 是 | >=1 |
| mapId | string | 是 | 必须与索引 mapId 一致 |
| track.length | int | 是 | >=1 |
| track.startTileId | string | 是 | 必须存在于 tiles | 
| tiles | array | 是 | 长度必须等于 	rack.length |
| tiles[].tileId | string | 是 | map 内唯一 |
| tiles[].tileKind | string | 是 | city/facility/event/empty |
| tiles[].nameKey | string | 是 | i18n key（双语） |
| tiles[].layout.x | float | 是 | [0,1] |
| tiles[].layout.y | float | 是 | [0,1] |
| tiles[].actions | array | 是 | actionId 在 tile 内唯一 |
| tiles[].actions[].actionId | string | 是 | id 规范 |
| tiles[].actions[].iconResPath | string | 是 | 资源路径安全约束 |

### tileKind=city
- 
egionId：必须存在于 
egions.json。
- city.basePrice：int，>0。
- city.baseToll：int，>=0。
- city.allowedBuildingIds：非空数组，且每项存在于 uildings.json。
- actions 必含 uy_land。

### tileKind=event
- eventPoolId：必须存在于 
andom_events.json 的 eventPools。
- actions 必含 	rigger_event。

### tileKind=facility
- acilityId：必须存在于 acilities.json。
- tile actions 必须匹配 acilities.json 中的 actionId 列表。

## 角色（Data/characters.json）

| 字段 | 类型 | 必填 | 约束/说明 |
|---|---|---|---|
| schemaVersion | int | 是 | 固定 1 |
| version | int | 是 | >=1 |
| characters | array | 是 | 数量 >=8 |
| characters[].characterId | string | 是 | id 规范 |
| characters[].nameKey | string | 是 | i18n key（双语） |
| characters[].descriptionKey | string | 是 | i18n key（双语） |
| characters[].combatRating | int | 是 | [0,100] |
| characters[].portraitPath | string | 是 | 资源路径安全约束 |
| characters[].startingMoneyStepDelta | int | 是 | [-6,6] |
| characters[].economyStepDeltas | object | 是 | 必含 uyPrice/toll/incomeSettlement/buildCost/upgradeCost，每项 int [-6,6] |

## 随机事件（Data/random_events.json）

| 字段 | 类型 | 必填 | 约束/说明 |
|---|---|---|---|
| schemaVersion | int | 是 | 固定 1 |
| version | int | 是 | >=1 |
| eventPools | array | 是 | 非空 |
| eventPools[].poolId | string | 是 | id 规范 |
| eventPools[].eventIds | array | 是 | 必须全部存在于 events |
| events | array | 是 | 数量 >=9 |
| events[].eventId | string | 是 | id 规范 |
| events[].nameKey | string | 是 | i18n key（双语） |
| events[].descriptionKey | string | 是 | i18n key（双语） |
| events[].uniqueOnce | bool | 是 | 固定布尔 |
| events[].cooldownRounds | int | 是 | [0,1000] |
| events[].effectKind | string | 是 | moneyDelta/economyStepDelta/startCombat |

effectKind 补充：
- moneyDelta：moneyDelta int [-10000,10000]。
- economyStepDelta：stepDelta int [-6,6]。
- startCombat：encounterId string，encounterTarget int [0,1000]。
- poolId=global 不允许包含 startCombat。
- 事件数量门禁：moneyDelta>=3、economyStepDelta>=3、startCombat>=2。

## 行动卡（Data/action_cards.json）

| 字段 | 类型 | 必填 | 约束/说明 |
|---|---|---|---|
| schemaVersion | int | 是 | 固定 1 |
| version | int | 是 | >=1 |
| cards | array | 是 | 数量 >=6 |
| cards[].cardId | string | 是 | id 规范 |
| cards[].nameKey | string | 是 | i18n key（双语） |
| cards[].descriptionKey | string | 是 | i18n key（双语） |
| cards[].durationRounds | int | 是 | [1,1000] |
| cards[].effectKind | string | 是 | economyStepDelta/transferOwnership |
| cards[].stepDelta | int | 是 | [-6,6]（transferOwnership 允许 0） |

数量门禁：economyStepDelta>=4，	ransferOwnership>=1。

## 建筑（Data/buildings.json）

| 字段 | 类型 | 必填 | 约束/说明 |
|---|---|---|---|
| schemaVersion | int | 是 | 固定 1 |
| version | int | 是 | >=1 |
| buildings | array | 是 | 数量 >=5 |
| buildings[].buildingId | string | 是 | id 规范 |
| buildings[].nameKey | string | 是 | i18n key（双语） |
| buildings[].descriptionKey | string | 是 | i18n key（双语） |
| buildings[].maxLevel | int | 是 | >=1 |
| buildings[].buildCostBase | int | 是 | >=0 |
| buildings[].upgradeCostBase | int | 是 | >=0 |
| buildings[].settlementIncomeBase | int | 是 | >=0 |
| buildings[].economyStepDeltas | object | 是 | 必含 uyPrice/toll/incomeSettlement/buildCost/upgradeCost，每项 int [-6,6] |

## 宝物（Data/relics.json）

| 字段 | 类型 | 必填 | 约束/说明 |
|---|---|---|---|
| schemaVersion | int | 是 | 固定 1 |
| version | int | 是 | >=1 |
| relics | array | 是 | 数量 >=4 |
| relics[].relicId | string | 是 | id 规范 |
| relics[].nameKey | string | 是 | i18n key（双语） |
| relics[].descriptionKey | string | 是 | i18n key（双语） |
| relics[].effectKind | string | 是 | moneyDelta/economyStepDelta |
| relics[].moneyDelta | int | 条件 | >0（当 effectKind=moneyDelta） |
| relics[].stepDelta | int | 条件 | [-6,6] 且非 0（当 effectKind=economyStepDelta） |

数量门禁：moneyDelta>=2、economyStepDelta>=2。

## 州郡（Data/regions.json）

| 字段 | 类型 | 必填 | 约束/说明 |
|---|---|---|---|
| schemaVersion | int | 是 | 固定 1 |
| version | int | 是 | >=1 |
| regions | array | 是 | 非空 |
| regions[].regionId | string | 是 | id 规范 |
| regions[].nameKey | string | 是 | i18n key（双语） |
| regions[].descriptionKey | string | 是 | i18n key（双语） |
| regions[].effectKind | string | 是 | 固定 economyStepDelta |
| regions[].economyStepDeltas | object | 是 | 必含 uyPrice/toll/incomeSettlement/buildCost/upgradeCost，每项 int [-6,6] |

## 设施（Data/facilities.json）

| 字段 | 类型 | 必填 | 约束/说明 |
|---|---|---|---|
| schemaVersion | int | 是 | 固定 1 |
| version | int | 是 | >=1 |
| facilities | array | 是 | 非空 |
| facilities[].facilityId | string | 是 | id 规范 |
| facilities[].facilityKind | string | 是 | 非空字符串 |
| facilities[].nameKey | string | 是 | i18n key（双语） |
| facilities[].descriptionKey | string | 是 | i18n key（双语） |
| facilities[].actions | array | 是 | 可为空，但若定义必须与 tile actions 一致 |
| facilities[].actions[].actionId | string | 是 | id 规范 |
| facilities[].actions[].iconResPath | string | 是 | 资源路径安全约束 |
| facilities[].actions[].actionKind | string | 条件 | openShop/startCombat/hospital/jail/job/wilderness |
| facilities[].actions[].effectKind | string | 条件 | 	eleport 时需要 params |
| facilities[].actions[].params.targetMode | string | 条件 | 
andom/tileId |
| facilities[].actions[].params.tileId | string | 条件 | targetMode=tileId 时必填 |

## i18n（Data/i18n/zh_cn.json 与 Data/i18n/en_us.json）

| 字段 | 类型 | 必填 | 约束/说明 |
|---|---|---|---|
| schemaVersion | int | 是 | 固定 1 |
| version | int | 是 | >=1 |
| locale | string | 是 | zh-CN 或 en-US |
| strings | object | 是 | key->string，key 必须为字符串 |

## 引用与口径

- ADR-0004：事件命名与契约口径。
- ADR-0005：质量门禁与 CI 约束。
- ADR-0019：资源与路径安全基线。
- docs/workflows/content-pack-manifest.md：内容包规范。

## 内容质量门禁补充（T2）

- eventPools 的 eventIds 必须非空且不重复。
- facility actions 必须满足：teleport 仅用 effectKind=teleport（不得包含 actionKind），其余必须包含 actionKind 且在允许列表内。
- tileKind=empty 必须无 actions；tileKind=city 仅允许 buy_land/build；tileKind=event 仅允许 trigger_event。

## 数值与权重门禁补充（T2）

- economyStepDeltas：每项 int 且必须在 [-6,6]（硬门禁）。
- moneyDelta：int 且必须在 [-10000,10000]（硬门禁）。
- probability/chance/prob：number 且必须在 [0,1]。
- weight：若列表中出现 weight，则该列表每项必须带 weight；
  - 全部为 int 时，范围 [0,100] 且总和必须 = 100。
  - 全部为 float 时，范围 [0,1] 且总和必须 = 1.0。
  - 禁止 int/float 混用。

